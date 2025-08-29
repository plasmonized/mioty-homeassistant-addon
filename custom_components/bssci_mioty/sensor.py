"""Sensor platform for BSSCI mioty integration."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BSSCI mioty sensors from a config entry."""
    # Sensors are created dynamically when MQTT messages arrive
    # This function is required but sensors are added via the MQTT client
    pass


class BSSCISensorEntity(SensorEntity):
    """Representation of a BSSCI mioty sensor."""

    def __init__(self, sensor_eui: str, config_entry_id: str):
        """Initialize the sensor."""
        self._sensor_eui = sensor_eui
        self._config_entry_id = config_entry_id
        self._attr_name = f"mioty Sensor {sensor_eui}"
        self._attr_unique_id = f"bssci_sensor_{sensor_eui}"
        self._attr_device_class = "data_size"
        self._attr_unit_of_measurement = "bytes"
        self._attr_state = None
        self._attr_extra_state_attributes = {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"sensor_{self._sensor_eui}")},
            name=f"mioty Sensor {self._sensor_eui}",
            model="mioty IoT Sensor",
            manufacturer="BSSCI",
            via_device=(DOMAIN, "bssci_service_center"),
        )

    @callback
    def async_update_data(self, data: Dict[str, Any]) -> None:
        """Update sensor with new data."""
        self._attr_state = len(data.get("data", []))
        
        # Parse timestamp
        rx_time = data.get("rxTime")
        if rx_time:
            try:
                # Convert nanoseconds to seconds
                timestamp = datetime.fromtimestamp(rx_time / 1_000_000_000)
                rx_time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OverflowError):
                rx_time_str = "Invalid timestamp"
        else:
            rx_time_str = "Unknown"

        self._attr_extra_state_attributes = {
            "sensor_eui": self._sensor_eui,
            "base_station_eui": data.get("bs_eui", "Unknown"),
            "snr": data.get("snr"),
            "rssi": data.get("rssi"),
            "message_counter": data.get("cnt"),
            "receive_time": rx_time_str,
            "raw_data": data.get("data", []),
            "signal_quality": self._get_signal_quality(data.get("snr"), data.get("rssi")),
        }
        
        self.async_write_ha_state()

    def _get_signal_quality(self, snr: Optional[float], rssi: Optional[float]) -> str:
        """Assess signal quality from SNR and RSSI values."""
        if snr is None or rssi is None:
            return "unknown"
        
        if snr > 10 and rssi > -80:
            return "excellent"
        elif snr > 5 and rssi > -90:
            return "good"
        elif snr > 0 and rssi > -100:
            return "fair"
        else:
            return "poor"


class BSSCIBaseStationEntity(SensorEntity):
    """Representation of a BSSCI base station."""

    def __init__(self, bs_eui: str, config_entry_id: str):
        """Initialize the base station sensor."""
        self._bs_eui = bs_eui
        self._config_entry_id = config_entry_id
        self._attr_name = f"mioty Base Station {bs_eui}"
        self._attr_unique_id = f"bssci_basestation_{bs_eui}"
        self._attr_device_class = "connectivity"
        self._attr_state = None
        self._attr_extra_state_attributes = {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"basestation_{self._bs_eui}")},
            name=f"mioty Base Station {self._bs_eui}",
            model="MBS20 Base Station",
            manufacturer="Swissphone",
            via_device=(DOMAIN, "bssci_service_center"),
        )

    @property
    def icon(self) -> str:
        """Return the icon for the base station."""
        if self._attr_state == "online":
            return "mdi:antenna"
        else:
            return "mdi:antenna-off"

    @callback
    def async_update_status(self, data: Dict[str, Any]) -> None:
        """Update base station with new status."""
        code = data.get("code", 1)
        self._attr_state = "online" if code == 0 else "error"
        
        # Parse timestamp
        time_value = data.get("time")
        if time_value:
            try:
                # Convert nanoseconds to seconds
                timestamp = datetime.fromtimestamp(time_value / 1_000_000_000)
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OverflowError):
                time_str = "Invalid timestamp"
        else:
            time_str = "Unknown"

        # Convert uptime to human readable format
        uptime = data.get("uptime", 0)
        uptime_str = self._format_uptime(uptime)

        self._attr_extra_state_attributes = {
            "base_station_eui": self._bs_eui,
            "status_code": code,
            "memory_load": f"{data.get('memLoad', 0) * 100:.1f}%",
            "cpu_load": f"{data.get('cpuLoad', 0) * 100:.1f}%",
            "duty_cycle": f"{data.get('dutyCycle', 0) * 100:.1f}%",
            "last_seen": time_str,
            "uptime": uptime_str,
            "uptime_seconds": uptime,
        }
        
        self.async_write_ha_state()

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in human readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m {seconds % 60}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
