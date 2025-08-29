"""The BSSCI mioty integration."""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .const import (
    DOMAIN,
    CONF_MQTT_BROKER,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    CONF_MQTT_PASSWORD,
    CONF_BASE_TOPIC,
    TOPIC_SENSOR_DATA,
    TOPIC_BASE_STATION,
    TOPIC_SENSOR_CONFIG,
    SERVICE_ADD_SENSOR,
    SERVICE_REMOVE_SENSOR,
    SERVICE_CONFIGURE_SENSOR,
    ATTR_SENSOR_EUI,
    ATTR_NETWORK_KEY,
    ATTR_SHORT_ADDR,
    ATTR_BIDIRECTIONAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]

# Service schemas
ADD_SENSOR_SCHEMA = vol.Schema({
    vol.Required(ATTR_SENSOR_EUI): cv.string,
    vol.Required(ATTR_NETWORK_KEY): cv.string,
    vol.Required(ATTR_SHORT_ADDR): cv.string,
    vol.Optional(ATTR_BIDIRECTIONAL, default=False): cv.boolean,
})

CONFIGURE_SENSOR_SCHEMA = vol.Schema({
    vol.Required(ATTR_SENSOR_EUI): cv.string,
    vol.Required(ATTR_NETWORK_KEY): cv.string,
    vol.Required(ATTR_SHORT_ADDR): cv.string,
    vol.Optional(ATTR_BIDIRECTIONAL, default=False): cv.boolean,
})

REMOVE_SENSOR_SCHEMA = vol.Schema({
    vol.Required(ATTR_SENSOR_EUI): cv.string,
})


class BSSCIMQTTClient:
    """MQTT client for BSSCI communication."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize the MQTT client."""
        self.hass = hass
        self.config = config
        self.client = None
        self.connected = False
        self.sensors = {}
        self.base_stations = {}

    async def async_connect(self):
        """Connect to MQTT broker."""
        try:
            self.client = mqtt.Client()
            
            if self.config.get(CONF_MQTT_USERNAME):
                self.client.username_pw_set(
                    self.config[CONF_MQTT_USERNAME],
                    self.config.get(CONF_MQTT_PASSWORD, "")
                )

            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            await self.hass.async_add_executor_job(
                self.client.connect,
                self.config[CONF_MQTT_BROKER],
                self.config[CONF_MQTT_PORT],
                60
            )

            # Start the MQTT loop in a separate thread
            self.client.loop_start()
            
        except Exception as e:
            _LOGGER.error("Failed to connect to MQTT broker: %s", e)
            raise

    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            self.connected = True
            _LOGGER.info("Connected to MQTT broker")
            
            # Subscribe to sensor data
            topic = f"{self.config[CONF_BASE_TOPIC]}/{TOPIC_SENSOR_DATA}"
            client.subscribe(topic)
            _LOGGER.debug("Subscribed to %s", topic)
            
            # Subscribe to base station status
            topic = f"{self.config[CONF_BASE_TOPIC]}/{TOPIC_BASE_STATION}"
            client.subscribe(topic)
            _LOGGER.debug("Subscribed to %s", topic)
            
        else:
            _LOGGER.error("Failed to connect to MQTT broker with code %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        self.connected = False
        _LOGGER.warning("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            topic_parts = msg.topic.split('/')
            base_topic_parts = self.config[CONF_BASE_TOPIC].split('/')
            
            # Remove base topic parts
            topic_parts = topic_parts[len(base_topic_parts):]
            
            if len(topic_parts) >= 3 and topic_parts[0] == "ep" and topic_parts[2] == "ul":
                # Sensor data message
                sensor_eui = topic_parts[1]
                data = json.loads(msg.payload.decode())
                self._handle_sensor_data(sensor_eui, data)
                
            elif len(topic_parts) >= 2 and topic_parts[0] == "bs":
                # Base station status
                bs_eui = topic_parts[1]
                data = json.loads(msg.payload.decode())
                self._handle_base_station_status(bs_eui, data)
                
        except Exception as e:
            _LOGGER.error("Error processing MQTT message: %s", e)

    def _handle_sensor_data(self, sensor_eui: str, data: Dict[str, Any]):
        """Handle sensor data message."""
        self.hass.async_create_task(
            self._async_update_sensor(sensor_eui, data)
        )

    def _handle_base_station_status(self, bs_eui: str, data: Dict[str, Any]):
        """Handle base station status message."""
        self.hass.async_create_task(
            self._async_update_base_station(bs_eui, data)
        )

    async def _async_update_sensor(self, sensor_eui: str, data: Dict[str, Any]):
        """Update sensor entity with new data."""
        entity_id = f"sensor.bssci_sensor_{sensor_eui.lower()}"
        
        # Create sensor entity if it doesn't exist
        if sensor_eui not in self.sensors:
            await self._async_create_sensor_entity(sensor_eui)
        
        # Update sensor state
        self.hass.states.async_set(
            entity_id,
            len(data.get("data", [])),  # Use data length as state
            {
                "bs_eui": data.get("bs_eui"),
                "snr": data.get("snr"),
                "rssi": data.get("rssi"),
                "cnt": data.get("cnt"),
                "rx_time": data.get("rxTime"),
                "raw_data": data.get("data", []),
                "friendly_name": f"mioty Sensor {sensor_eui}",
                "device_class": "data_size",
                "unit_of_measurement": "bytes",
            }
        )

    async def _async_update_base_station(self, bs_eui: str, data: Dict[str, Any]):
        """Update base station entity with new status."""
        entity_id = f"sensor.bssci_basestation_{bs_eui.lower()}"
        
        # Create base station entity if it doesn't exist
        if bs_eui not in self.base_stations:
            await self._async_create_base_station_entity(bs_eui)
        
        # Determine status based on code
        status = "online" if data.get("code", 1) == 0 else "error"
        
        # Update base station state
        self.hass.states.async_set(
            entity_id,
            status,
            {
                "code": data.get("code"),
                "mem_load": data.get("memLoad"),
                "cpu_load": data.get("cpuLoad"),
                "duty_cycle": data.get("dutyCycle"),
                "time": data.get("time"),
                "uptime": data.get("uptime"),
                "friendly_name": f"mioty Base Station {bs_eui}",
                "device_class": "connectivity",
            }
        )

    async def _async_create_sensor_entity(self, sensor_eui: str):
        """Create a new sensor entity."""
        self.sensors[sensor_eui] = True
        
        # Register device
        device_registry = async_get_device_registry(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self.hass.data[DOMAIN]["config_entry_id"],
            identifiers={(DOMAIN, f"sensor_{sensor_eui}")},
            name=f"mioty Sensor {sensor_eui}",
            model="mioty IoT Sensor",
            manufacturer="BSSCI",
        )

    async def _async_create_base_station_entity(self, bs_eui: str):
        """Create a new base station entity."""
        self.base_stations[bs_eui] = True
        
        # Register device
        device_registry = async_get_device_registry(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self.hass.data[DOMAIN]["config_entry_id"],
            identifiers={(DOMAIN, f"basestation_{bs_eui}")},
            name=f"mioty Base Station {bs_eui}",
            model="MBS20 Base Station",
            manufacturer="Swissphone",
        )

    async def async_configure_sensor(self, sensor_eui: str, network_key: str, 
                                   short_addr: str, bidirectional: bool = False):
        """Configure a sensor via MQTT."""
        if not self.connected:
            raise Exception("MQTT client not connected")

        config = {
            "nwKey": network_key,
            "shortAddr": short_addr,
            "bidi": bidirectional
        }

        topic = f"{self.config[CONF_BASE_TOPIC]}/{TOPIC_SENSOR_CONFIG.format(sensor_eui)}"
        
        await self.hass.async_add_executor_job(
            self.client.publish,
            topic,
            json.dumps(config)
        )
        
        _LOGGER.info("Sensor configuration sent for %s", sensor_eui)

    async def async_disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            await self.hass.async_add_executor_job(self.client.disconnect)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the BSSCI mioty component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BSSCI mioty from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Store config entry ID for device registration
    hass.data[DOMAIN]["config_entry_id"] = entry.entry_id
    
    # Create MQTT client
    mqtt_client = BSSCIMQTTClient(hass, entry.data)
    hass.data[DOMAIN]["mqtt_client"] = mqtt_client
    
    # Connect to MQTT
    await mqtt_client.async_connect()
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    async def async_add_sensor(call: ServiceCall):
        """Add and configure a new sensor."""
        sensor_eui = call.data[ATTR_SENSOR_EUI]
        network_key = call.data[ATTR_NETWORK_KEY]
        short_addr = call.data[ATTR_SHORT_ADDR]
        bidirectional = call.data.get(ATTR_BIDIRECTIONAL, False)
        
        try:
            await mqtt_client.async_configure_sensor(
                sensor_eui, network_key, short_addr, bidirectional
            )
        except Exception as e:
            _LOGGER.error("Failed to add sensor %s: %s", sensor_eui, e)
            raise

    async def async_configure_sensor(call: ServiceCall):
        """Configure an existing sensor."""
        sensor_eui = call.data[ATTR_SENSOR_EUI]
        network_key = call.data[ATTR_NETWORK_KEY]
        short_addr = call.data[ATTR_SHORT_ADDR]
        bidirectional = call.data.get(ATTR_BIDIRECTIONAL, False)
        
        try:
            await mqtt_client.async_configure_sensor(
                sensor_eui, network_key, short_addr, bidirectional
            )
        except Exception as e:
            _LOGGER.error("Failed to configure sensor %s: %s", sensor_eui, e)
            raise

    async def async_remove_sensor(call: ServiceCall):
        """Remove a sensor."""
        sensor_eui = call.data[ATTR_SENSOR_EUI]
        entity_id = f"sensor.bssci_sensor_{sensor_eui.lower()}"
        
        # Remove entity
        entity_registry = async_get_entity_registry(hass)
        if entity := entity_registry.async_get(entity_id):
            entity_registry.async_remove(entity_id)
        
        # Remove from tracking
        if sensor_eui in mqtt_client.sensors:
            del mqtt_client.sensors[sensor_eui]
        
        _LOGGER.info("Removed sensor %s", sensor_eui)

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_SENSOR, async_add_sensor, schema=ADD_SENSOR_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CONFIGURE_SENSOR, async_configure_sensor, schema=CONFIGURE_SENSOR_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_SENSOR, async_remove_sensor, schema=REMOVE_SENSOR_SCHEMA
    )
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Disconnect MQTT client
        mqtt_client = hass.data[DOMAIN]["mqtt_client"]
        await mqtt_client.async_disconnect()
        
        # Remove services
        hass.services.async_remove(DOMAIN, SERVICE_ADD_SENSOR)
        hass.services.async_remove(DOMAIN, SERVICE_CONFIGURE_SENSOR)
        hass.services.async_remove(DOMAIN, SERVICE_REMOVE_SENSOR)
        
        hass.data[DOMAIN].pop("mqtt_client")
        
    return unload_ok
