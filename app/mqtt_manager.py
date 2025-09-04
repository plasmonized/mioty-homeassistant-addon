"""
MQTT Manager für BSSCI mioty Add-on
Verwaltet die MQTT-Kommunikation mit Home Assistant
"""

import json
import logging
import threading
import time
import uuid
from typing import Callable, Optional, Dict, Any

import paho.mqtt.client as mqtt


class MQTTManager:
    """Dual MQTT Manager für mioty Daten + Home Assistant Integration."""
    
    def __init__(self, broker: str, port: int, username: str = "", 
                 password: str = "", base_topic: str = "bssci",
                 ha_broker: str = "core-mosquitto", ha_port: int = 1883,
                 ha_username: str = "", ha_password: str = ""):
        """Initialisiere Dual MQTT Manager."""
        # Externes mioty MQTT (für Datenempfang)
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.base_topic = base_topic
        
        # Home Assistant MQTT (für Discovery)
        self.ha_broker = ha_broker
        self.ha_port = ha_port
        self.ha_username = ha_username
        self.ha_password = ha_password
        
        self.client = None  # mioty data client
        self.ha_client = None  # Home Assistant discovery client
        self.connected = False
        self.ha_connected = False
        self.running = False
        
        # Callbacks
        self.data_callback: Optional[Callable] = None
        self.config_callback: Optional[Callable] = None
        self.base_station_callback: Optional[Callable] = None
        
        logging.info(f"🔧 Dual MQTT Manager initialisiert:")
        logging.info(f"   📡 mioty Data Client: {broker}:{port} (User: '{username}')")
        logging.info(f"   🏠 HA Discovery Client: {ha_broker}:{ha_port} (User: '{ha_username}')")
    
    def set_data_callback(self, callback: Callable):
        """Setze Callback für Sensor-Daten."""
        self.data_callback = callback
    
    def set_config_callback(self, callback: Callable):
        """Setze Callback für Sensor-Konfiguration."""
        self.config_callback = callback
    
    def set_base_station_callback(self, callback: Callable):
        """Setze Callback für Base Station Status."""
        self.base_station_callback = callback
    
    def connect(self) -> bool:
        """Verbinde mit beiden MQTT Brokern."""
        success = True
        
        logging.info(f"🔍 DEBUG: Dual MQTT Verbindung wird gestartet:")
        logging.info(f"   📡 BSSCI Broker: {self.broker}:{self.port}")
        logging.info(f"   🏠 HA Broker: {self.ha_broker}:{self.ha_port}")
        
        # 1. Verbinde mit externem mioty Broker (für Datenempfang)
        try:
            # Eindeutige Client-ID generieren um Konflikte zu vermeiden
            unique_id = str(uuid.uuid4())[:8]
            client_id = f"bssci_mioty_{unique_id}"
            self.client = mqtt.Client(client_id=client_id)
            logging.info(f"🔧 MQTT Client ID: {client_id}")
            
            # Authentication
            if self.username:
                self.client.username_pw_set(self.username, self.password)
            
            # Callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Verbinden
            logging.info(f"Verbinde mit mioty MQTT Broker {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            # Auf Verbindung warten
            timeout = 10
            while timeout > 0 and not self.connected:
                time.sleep(1)
                timeout -= 1
            
            if not self.connected:
                logging.error("mioty MQTT Verbindung Timeout")
                success = False
                
        except Exception as e:
            logging.error(f"mioty MQTT Verbindung fehlgeschlagen: {e}")
            success = False
        
        # 2. Verbinde mit Home Assistant MQTT Broker (für Discovery)
        try:
            # Eindeutige Client-ID für HA Client generieren
            ha_unique_id = str(uuid.uuid4())[:8]
            ha_client_id = f"bssci_ha_{ha_unique_id}"
            self.ha_client = mqtt.Client(client_id=ha_client_id)
            logging.info(f"🏠 HA MQTT Client ID: {ha_client_id}")
            
            # Authentication für HA
            if self.ha_username:
                self.ha_client.username_pw_set(self.ha_username, self.ha_password)
            
            # Callbacks
            self.ha_client.on_connect = self._on_ha_connect
            self.ha_client.on_disconnect = self._on_ha_disconnect
            
            # Verbinden
            logging.info(f"Verbinde mit Home Assistant MQTT Broker {self.ha_broker}:{self.ha_port}")
            self.ha_client.connect(self.ha_broker, self.ha_port, 60)
            self.ha_client.loop_start()
            
            # Auf Verbindung warten
            timeout = 10
            while timeout > 0 and not self.ha_connected:
                time.sleep(1)
                timeout -= 1
            
            if not self.ha_connected:
                logging.warning("Home Assistant MQTT Verbindung Timeout - Discovery deaktiviert")
                
        except Exception as e:
            logging.warning(f"Home Assistant MQTT Verbindung fehlgeschlagen: {e} - Discovery deaktiviert")
            logging.info("💡 Tipp: Für Home Assistant Add-ons verwenden Sie 'core-mosquitto' als HA MQTT Broker")
            logging.info(f"🔧 Debug: Versuche Verbindung zu {self.ha_broker}:{self.ha_port} mit User='{self.ha_username}'")
        
        if success:
            self.running = True
            
        return success
    
    def disconnect(self):
        """Trenne beide MQTT Verbindungen."""
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            
        if self.ha_client:
            self.ha_client.loop_stop()
            self.ha_client.disconnect()
            
        logging.info("MQTT Verbindungen getrennt")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT Connect Callback."""
        if rc == 0:
            self.connected = True
            logging.info(f"✅ mioty MQTT Client verbunden: {self.broker}:{self.port}")
            
            # Topics abonnieren
            self._subscribe_topics()
            
        else:
            logging.error(f"❌ mioty MQTT Verbindung fehlgeschlagen: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT Disconnect Callback."""
        self.connected = False
        logging.warning(f"⚠️ mioty MQTT Client getrennt: {self.broker}:{self.port}")
    
    def _on_ha_connect(self, client, userdata, flags, rc):
        """Home Assistant MQTT Connect Callback."""
        if rc == 0:
            self.ha_connected = True
            logging.info("✅ Home Assistant MQTT erfolgreich verbunden - Discovery aktiviert!")
        else:
            error_codes = {
                1: "Falsche Protokoll-Version",
                2: "Ungültige Client-ID", 
                3: "Server nicht verfügbar",
                4: "Ungültige Credentials",
                5: "Nicht autorisiert"
            }
            error_msg = error_codes.get(rc, f"Unbekannter Fehler: {rc}")
            logging.error(f"❌ Home Assistant MQTT Verbindung fehlgeschlagen: {error_msg}")
            logging.error(f"🔧 Broker: {self.ha_broker}:{self.ha_port}, User: '{self.ha_username}'")
    
    def _on_ha_disconnect(self, client, userdata, rc):
        """Home Assistant MQTT Disconnect Callback."""
        self.ha_connected = False
        logging.warning(f"⚠️ Home Assistant MQTT Client getrennt: {self.ha_broker}:{self.ha_port}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT Message Callback."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logging.info(f"📨 MQTT Nachricht empfangen: {topic} (Payload: {len(payload)} bytes)")
            
            # Parse Topic
            topic_parts = topic.split('/')
            
            # BSSCI Topics verarbeiten
            if len(topic_parts) >= 3 and topic_parts[0] == self.base_topic:
                self._handle_bssci_message(topic_parts, payload)
                
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der MQTT Nachricht: {e}")
    
    def _subscribe_topics(self):
        """Abonniere relevante MQTT Topics."""
        topics = [
            f"{self.base_topic}/ep/+/ul",      # Sensor Daten
            f"{self.base_topic}/bs/+",         # Base Station Status
            f"{self.base_topic}/ep/+/config"   # Sensor Konfiguration
        ]
        
        for topic in topics:
            result = self.client.subscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"📋 Topic abonniert: {topic}")
            else:
                logging.error(f"❌ Topic-Abonnement fehlgeschlagen: {topic}")
    
    def _handle_bssci_message(self, topic_parts: list, payload: str):
        """Verarbeite BSSCI MQTT Nachrichten."""
        try:
            data = json.loads(payload)
            
            if len(topic_parts) >= 4 and topic_parts[1] == "ep":
                sensor_eui = topic_parts[2]
                message_type = topic_parts[3]
                
                if message_type == "ul" and self.data_callback:
                    # Sensor-Daten
                    self.data_callback(sensor_eui, data)
                    
                elif message_type == "config" and self.config_callback:
                    # Sensor-Konfiguration
                    self.config_callback(sensor_eui, data)
                    
            elif len(topic_parts) >= 3 and topic_parts[1] == "bs":
                bs_eui = topic_parts[2]
                # Base Station Status
                if self.base_station_callback:
                    self.base_station_callback(bs_eui, data)
                    logging.info(f"Base Station Status empfangen: {bs_eui}")
                else:
                    logging.debug(f"Base Station Status (kein Callback): {bs_eui}")
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON Parse Fehler: {e}")
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der BSSCI Nachricht: {e}")
    
    def publish_discovery(self, topic: str, config: Dict[str, Any] | str) -> bool:
        """Sende Home Assistant Discovery Konfiguration über HA MQTT."""
        if not self.ha_connected or not self.ha_client:
            logging.warning(f"❌ HA MQTT nicht verfügbar - Discovery übersprungen (ha_connected={self.ha_connected}, ha_broker={self.ha_broker}:{self.ha_port})")
            return False
        
        try:
            payload = json.dumps(config) if isinstance(config, dict) else config
            result = self.ha_client.publish(topic, payload, retain=True)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            logging.error(f"Fehler beim Senden der Discovery Konfiguration: {e}")
            return False
    
    def publish_sensor_state(self, unique_id: str, state: Any, attributes: Dict[str, Any]) -> bool:
        """Sende Sensor-Status an Home Assistant über HA MQTT."""
        if not self.ha_connected or not self.ha_client:
            logging.debug("HA MQTT nicht verfügbar - Status übersprungen")
            return False
        
        try:
            # State Topic
            state_topic = f"homeassistant/sensor/{unique_id}/state"
            self.ha_client.publish(state_topic, str(state))
            
            # Attributes Topic
            attr_topic = f"homeassistant/sensor/{unique_id}/attributes"
            attr_payload = json.dumps(attributes)
            self.ha_client.publish(attr_topic, attr_payload)
            
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Senden des Sensor-Status: {e}")
            return False
    
    def publish_config(self, topic: str, config: Dict[str, Any]) -> bool:
        """Sende Sensor-Konfiguration."""
        if not self.connected:
            return False
        
        try:
            payload = json.dumps(config)
            result = self.client.publish(topic, payload)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            logging.error(f"Fehler beim Senden der Konfiguration: {e}")
            return False
    
    def send_individual_sensor_discoveries(self, sensor_eui: str, decoded_data: Dict[str, Any], device_name: str = "mioty Sensor") -> bool:
        """Sende separate Home Assistant Discovery Messages für jeden Messwert."""
        if not self.ha_connected or not self.ha_client:
            logging.debug("HA MQTT nicht verfügbar - Individual Discovery übersprungen")
            return False
        
        # Device Information für alle Sensoren
        device_info = {
            "identifiers": [sensor_eui],
            "name": device_name,
            "manufacturer": "Sentinum",
            "model": "Febris TH",
            "via_device": "bssci_mioty_application_center"
        }
        
        # Sensor Mapping: Messwert → Home Assistant Konfiguration
        sensor_configs = {
            "internal_temperature": {
                "name": "Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "icon": "mdi:thermometer"
            },
            "temperature": {
                "name": "Temperature", 
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "icon": "mdi:thermometer"
            },
            "humidity": {
                "name": "Humidity",
                "device_class": "humidity", 
                "unit_of_measurement": "%",
                "icon": "mdi:water-percent"
            },
            "battery_voltage": {
                "name": "Battery Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "icon": "mdi:battery"
            },
            "dew_point": {
                "name": "Dew Point",
                "device_class": "temperature",
                "unit_of_measurement": "°C", 
                "icon": "mdi:water-thermometer"
            },
            "pressure": {
                "name": "Pressure",
                "device_class": "atmospheric_pressure",
                "unit_of_measurement": "hPa",
                "icon": "mdi:gauge"
            },
            "co2": {
                "name": "CO2",
                "device_class": "carbon_dioxide",
                "unit_of_measurement": "ppm",
                "icon": "mdi:molecule-co2"
            },
            # IO-Link Adapter Measurements
            "vendor_id": {
                "name": "Vendor ID",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:factory"
            },
            "device_id": {
                "name": "Device ID", 
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:chip"
            },
            "adapter_event": {
                "name": "Adapter Event",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:alert-circle"
            },
            "control_byte": {
                "name": "Control Byte",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:tune"
            },
            # Juno TH Sensor Measurements
            "up_cnt": {
                "name": "Uplink Count",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:counter",
                "state_class": "total_increasing"
            },
            "base_id": {
                "name": "Base ID",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:identifier",
                "state_class": None
            },
            "major_version": {
                "name": "Major Version",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:information",
                "state_class": None
            },
            "minor_version": {
                "name": "Minor Version",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:information",
                "state_class": None
            },
            # Generische Sensor Felder
            "sensor_id": {
                "name": "Sensor ID",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:identifier"
            },
            "packet_type": {
                "name": "Packet Type",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:package-variant"
            },
            "value1": {
                "name": "Value 1",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:numeric-1-circle"
            },
            "value2": {
                "name": "Value 2",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:numeric-2-circle"
            },
            "raw_hex": {
                "name": "Raw Data",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:code-braces"
            },
            # Signal Qualität Messwerte
            "signal_strength": {
                "name": "Signal Strength",
                "device_class": "signal_strength",
                "unit_of_measurement": "dBm",
                "icon": "mdi:wifi-strength-3"
            },
            "signal_to_noise_ratio": {
                "name": "Signal to Noise Ratio",
                "device_class": None,
                "unit_of_measurement": "dB",
                "icon": "mdi:wifi-strength-4"
            },
            "message_counter": {
                "name": "Message Counter",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:counter",
                "state_class": "total_increasing"
            }
        }
        
        # State Topic für alle Sensoren (gemeinsam)
        state_topic = f"homeassistant/sensor/{sensor_eui}/state"
        
        success_count = 0
        total_count = 0
        
        # Für jeden dekodierte Wert eine separate Discovery Message senden
        for measurement_key, measurement_data in decoded_data.items():
            if measurement_key in sensor_configs and isinstance(measurement_data, dict) and 'value' in measurement_data:
                config = sensor_configs[measurement_key]
                
                # Discovery Topic für diesen spezifischen Sensor
                discovery_topic = f"homeassistant/sensor/mioty_sensor_{sensor_eui}_{measurement_key}/config"
                
                # Discovery Payload - mioty spezifisches Format
                discovery_payload = {
                    "unique_id": f"mioty_sensor_{sensor_eui}_{measurement_key}",
                    "object_id": f"mioty_sensor_{sensor_eui}_{measurement_key}",
                    "name": f"Sentinum {config['name']}",
                    "state_topic": f"homeassistant/sensor/mioty_sensor_{sensor_eui}_{measurement_key}/state",
                    "value_template": "{{ value }}",
                    "unit_of_meas": config["unit_of_measurement"],
                    "icon": config["icon"],
                    "device": device_info,
                    "platform": "mioty",
                    "availability_topic": f"homeassistant/sensor/mioty_sensor_{sensor_eui}_{measurement_key}/availability",
                    "payload_available": "online",
                    "payload_not_available": "offline"
                }
                
                # Device Class nur hinzufügen wenn definiert
                if config["device_class"]:
                    discovery_payload["device_class"] = config["device_class"]
                
                # State Class hinzufügen (measurement, total, total_increasing oder None)
                if "state_class" in config and config["state_class"]:
                    discovery_payload["state_class"] = config["state_class"]
                elif config["device_class"] in ["temperature", "humidity", "voltage", "pressure", "carbon_dioxide"]:
                    discovery_payload["state_class"] = "measurement"
                
                # Discovery Message senden
                if self.publish_discovery(discovery_topic, discovery_payload):
                    success_count += 1
                    logging.info(f"🔍 Individual Discovery: {sensor_eui} - {config['name']} ({measurement_key})")
                else:
                    logging.warning(f"⚠️ Discovery fehlgeschlagen: {sensor_eui} - {measurement_key}")
                
                total_count += 1
        
        logging.info(f"✅ Individual Discovery abgeschlossen: {success_count}/{total_count} Sensoren für {sensor_eui}")
        return success_count > 0
    
    def publish_individual_sensor_states(self, sensor_eui: str, decoded_data: Dict[str, Any], snr: float = None, rssi: float = None) -> bool:
        """Sende individuelle State Topics für jeden Messwert."""
        if not self.ha_connected or not self.ha_client:
            logging.debug("HA MQTT nicht verfügbar - Individual States übersprungen")
            return False
        
        success_count = 0
        total_count = 0
        
        try:
            # Dekodierte Daten senden
            for measurement_key, measurement_data in decoded_data.items():
                if isinstance(measurement_data, dict) and 'value' in measurement_data:
                    state_topic = f"homeassistant/sensor/mioty_sensor_{sensor_eui}_{measurement_key}/state"
                    availability_topic = f"homeassistant/sensor/mioty_sensor_{sensor_eui}_{measurement_key}/availability"
                    
                    # Availability setzen
                    self.ha_client.publish(availability_topic, "online", retain=True)
                    
                    # State Wert senden
                    value = measurement_data['value']
                    result = self.ha_client.publish(state_topic, str(value), retain=True)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        success_count += 1
                        logging.debug(f"📊 State: mioty_sensor_{sensor_eui}_{measurement_key} → {value}")
                    else:
                        logging.warning(f"⚠️ State fehlgeschlagen: mioty_sensor_{sensor_eui}_{measurement_key}")
                    
                    total_count += 1
            
            # SNR als separaten Sensor senden
            if snr is not None:
                state_topic = f"homeassistant/sensor/mioty_sensor_{sensor_eui}_signal_to_noise_ratio/state"
                availability_topic = f"homeassistant/sensor/mioty_sensor_{sensor_eui}_signal_to_noise_ratio/availability"
                
                self.ha_client.publish(availability_topic, "online", retain=True)
                result = self.ha_client.publish(state_topic, str(round(snr, 2)), retain=True)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    success_count += 1
                    logging.debug(f"📊 SNR: mioty_sensor_{sensor_eui}_signal_to_noise_ratio → {round(snr, 2)}")
                
                total_count += 1
            
            # RSSI als separaten Sensor senden 
            if rssi is not None:
                state_topic = f"homeassistant/sensor/mioty_sensor_{sensor_eui}_signal_strength/state"
                availability_topic = f"homeassistant/sensor/mioty_sensor_{sensor_eui}_signal_strength/availability"
                
                self.ha_client.publish(availability_topic, "online", retain=True)
                result = self.ha_client.publish(state_topic, str(round(rssi, 2)), retain=True)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    success_count += 1
                    logging.debug(f"📊 RSSI: mioty_sensor_{sensor_eui}_signal_strength → {round(rssi, 2)}")
                
                total_count += 1
            
            logging.info(f"📊 Individual States: {sensor_eui} → {success_count}/{total_count} erfolgreich")
            return success_count > 0
                
        except Exception as e:
            logging.error(f"Fehler beim Senden der Individual Sensor States: {e}")
            return False

    def is_connected(self) -> bool:
        """Prüfe MQTT Verbindungsstatus."""
        return self.connected