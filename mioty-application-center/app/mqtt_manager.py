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
        
        # Reconnect / Backoff Status
        self._reconnect_lock = threading.Lock()
        self._mioty_backoff = 5      # Sekunden bis zum nächsten Reconnect-Versuch
        self._ha_backoff = 5
        self._mioty_backoff_max = 300  # maximal 5 Minuten zwischen Versuchen
        self._ha_backoff_max = 300
        self._mioty_next_attempt = 0.0
        self._ha_next_attempt = 0.0
        
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
    
    def _normalize_sensor_eui(self, sensor_eui: str) -> str:
        """Normalisiere Sensor EUI: Wandle Buchstaben in Großbuchstaben um, lasse Zahlen unverändert."""
        if not sensor_eui:
            return sensor_eui
        
        # Konvertiere nur Buchstaben zu Großbuchstaben, Zahlen bleiben unverändert
        normalized = ""
        for char in sensor_eui:
            if char.isalpha():
                normalized += char.upper()
            else:
                normalized += char
        
        return normalized
    
    def connect(self) -> bool:
        """Verbinde mit beiden MQTT Brokern."""
        # Manager gilt ab dem ersten Verbindungsversuch als "aktiv", damit
        # check_and_reconnect() auch dann greift, wenn der initiale Connect
        # fehlschlägt (statt dauerhaft getrennt zu bleiben).
        self.running = True
        
        success = self._connect_mioty_client()
        self._connect_ha_client()
        
        return success
    
    def _connect_mioty_client(self) -> bool:
        """Baue die Verbindung zum externen mioty MQTT Broker auf (für Datenempfang)."""
        try:
            # Falls bereits ein alter Client existiert, sauber aufräumen
            if self.client:
                try:
                    self.client.loop_stop()
                except Exception:
                    pass
            
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
                return False
            
            return True
                
        except Exception as e:
            logging.error(f"mioty MQTT Verbindung fehlgeschlagen: {e}")
            return False
    
    def _connect_ha_client(self) -> bool:
        """Baue die Verbindung zum Home Assistant MQTT Broker auf (für Discovery)."""
        try:
            # Falls bereits ein alter Client existiert, sauber aufräumen
            if self.ha_client:
                try:
                    self.ha_client.loop_stop()
                except Exception:
                    pass
            
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
                return False
            
            return True
                
        except Exception as e:
            logging.warning(f"Home Assistant MQTT Verbindung fehlgeschlagen: {e} - Discovery deaktiviert")
            logging.info("💡 Tipp: Für Home Assistant Add-ons verwenden Sie 'core-mosquitto' als HA MQTT Broker")
            logging.info(f"🔧 Debug: Versuche Verbindung zu {self.ha_broker}:{self.ha_port} mit User='{self.ha_username}'")
            return False
    
    def check_and_reconnect(self):
        """Prüfe den Verbindungsstatus beider Broker und versuche bei Bedarf mit Backoff eine
        Wiederverbindung. Wird periodisch aus dem Haupt-Loop aufgerufen."""
        if not self.running:
            return
        
        if not self._reconnect_lock.acquire(blocking=False):
            # Es läuft bereits ein Reconnect-Versuch, nichts zu tun
            return
        
        try:
            now = time.time()
            
            if not self.connected and now >= self._mioty_next_attempt:
                logging.warning(
                    f"🔁 mioty MQTT nicht verbunden - versuche Wiederverbindung "
                    f"(nächster Versuch in max. {self._mioty_backoff}s Backoff)..."
                )
                if self._connect_mioty_client():
                    logging.info("✅ mioty MQTT Wiederverbindung erfolgreich!")
                    self._mioty_backoff = 5
                    self._mioty_next_attempt = 0.0
                else:
                    logging.error(
                        f"❌ mioty MQTT Wiederverbindung fehlgeschlagen - "
                        f"nächster Versuch in {self._mioty_backoff}s"
                    )
                    self._mioty_next_attempt = now + self._mioty_backoff
                    self._mioty_backoff = min(self._mioty_backoff * 2, self._mioty_backoff_max)
            
            if not self.ha_connected and now >= self._ha_next_attempt:
                logging.warning(
                    f"🔁 Home Assistant MQTT nicht verbunden - versuche Wiederverbindung "
                    f"(nächster Versuch in max. {self._ha_backoff}s Backoff)..."
                )
                if self._connect_ha_client():
                    logging.info("✅ Home Assistant MQTT Wiederverbindung erfolgreich!")
                    self._ha_backoff = 5
                    self._ha_next_attempt = 0.0
                else:
                    logging.error(
                        f"❌ Home Assistant MQTT Wiederverbindung fehlgeschlagen - "
                        f"nächster Versuch in {self._ha_backoff}s"
                    )
                    self._ha_next_attempt = now + self._ha_backoff
                    self._ha_backoff = min(self._ha_backoff * 2, self._ha_backoff_max)
        finally:
            self._reconnect_lock.release()
    
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
            
            # BSSCI Topics mit BASE_TOPIC verarbeiten
            if len(topic_parts) >= 3 and topic_parts[0] == self.base_topic:
                self._handle_bssci_message(topic_parts, payload)
            
            # Remote EP Commands (bssci/ep/{EUI}/cmd) verarbeiten
            elif len(topic_parts) >= 4 and topic_parts[0] == "bssci" and topic_parts[1] == "ep" and topic_parts[3] == "cmd":
                self._handle_remote_ep_command(topic_parts, payload)
                
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der MQTT Nachricht: {e}")
    
    def _subscribe_topics(self):
        """Abonniere relevante MQTT Topics."""
        topics = [
            f"{self.base_topic}/ep/+/ul",       # Sensor Daten (Uplink)
            f"{self.base_topic}/bs/+",          # Base Station Status
            f"{self.base_topic}/ep/+/register", # 🎯 Legacy Sensor Registration (RECOMMENDED)
            f"{self.base_topic}/ep/+/config",   # Alternative Sensor Konfiguration
            f"{self.base_topic}/ep/+/cmd",      # 🎯 Unified Sensor Commands (attach, detach, status)
            f"{self.base_topic}/ep/+/dl",       # Downlink Messages
            f"{self.base_topic}/ep/+/response", # Command Responses
            f"{self.base_topic}/ep/+/status",   # Status Updates
            f"{self.base_topic}/ep/+/warning",  # Warning Notifications
            f"{self.base_topic}/ep/+/error",    # Error Notifications
        ]
        
        for topic in topics:
            result = self.client.subscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"📋 ✅ Topic abonniert: {topic}")
            else:
                logging.error(f"❌ Topic-Abonnement fehlgeschlagen: {topic}")
        
        # Extra Logging für Sensor Uplink Monitoring
        logging.info(f"🎯 WICHTIG: Warte auf Sensor Uplink Daten auf Topic: {self.base_topic}/ep/+/ul")
        logging.info(f"📊 Falls SNR/RSSI fehlen, kommen keine Sensor-Daten an!")
    
    def _handle_bssci_message(self, topic_parts: list, payload: str):
        """Verarbeite BSSCI MQTT Nachrichten."""
        try:
            data = json.loads(payload)
            
            if len(topic_parts) >= 4 and topic_parts[1] == "ep":
                sensor_eui = topic_parts[2]
                message_type = topic_parts[3]
                
                if message_type == "ul" and self.data_callback:
                    # Sensor-Daten (Uplink)
                    logging.info(f"📡 Sensor Uplink empfangen: {sensor_eui}")
                    logging.info(f"   📊 RSSI: {data.get('rssi', 'N/A')} dBm, SNR: {data.get('snr', 'N/A')} dB")
                    self.data_callback(sensor_eui, data)
                
                elif message_type == "register":
                    # Legacy Sensor Registration (RECOMMENDED)
                    logging.info(f"🎯 Legacy Sensor Registration: {sensor_eui}")
                    self._handle_sensor_registration(sensor_eui, data)
                    
                elif message_type == "config" and self.config_callback:
                    # Sensor-Konfiguration
                    logging.info(f"⚙️ Sensor Config: {sensor_eui}")
                    self.config_callback(sensor_eui, data)
                
                elif message_type == "cmd":
                    # Standard Commands
                    self._handle_sensor_command(sensor_eui, data)
                
                elif message_type == "dl":
                    # Downlink Messages
                    self._handle_downlink_message(sensor_eui, data)
                
                elif message_type == "response":
                    # Command Responses
                    self._handle_command_response(sensor_eui, data)
                
                elif message_type == "status":
                    # Status Updates
                    self._handle_status_update(sensor_eui, data)
                
                elif message_type == "warning":
                    # Warning Notifications
                    self._handle_warning_notification(sensor_eui, data)
                
                elif message_type == "error":
                    # Error Notifications
                    self._handle_error_notification(sensor_eui, data)
                    
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
            logging.debug("HA MQTT nicht verfügbar - Discovery übersprungen")
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
    
    def publish_config(self, topic: str, config: Dict[str, Any], confirm: bool = True) -> bool:
        """Sende Sensor-Konfiguration (QoS 1).
        
        confirm=True: wartet auf Broker-Bestätigung (PUBACK). Darf NICHT aus
        MQTT-Callbacks (on_message) aufgerufen werden, da wait_for_publish
        sonst die Netzwerk-Schleife blockiert - dort confirm=False verwenden.
        """
        if not self.connected:
            logging.error(f"❌ MQTT nicht verbunden ({self.broker}:{self.port}) - Publish auf '{topic}' übersprungen")
            return False
        
        try:
            payload = json.dumps(config)
            result = self.client.publish(topic, payload, qos=1)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error(f"❌ MQTT Publish fehlgeschlagen (rc={result.rc}) für '{topic}' auf {self.broker}:{self.port}")
                return False
            
            if confirm:
                # Auf PUBACK vom Broker warten (max. 5 Sekunden)
                result.wait_for_publish(timeout=5.0)
                if not result.is_published():
                    logging.error(f"❌ Keine Broker-Bestätigung (PUBACK) für '{topic}' auf {self.broker}:{self.port} - Nachricht evtl. verloren!")
                    return False
                logging.info(f"✅ MQTT Publish bestätigt: '{topic}' auf {self.broker}:{self.port}")
            
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Senden der Konfiguration an '{topic}': {e}")
            return False
    
    def send_sensor_command(self, sensor_eui: str, command: str) -> bool:
        """Sende Command an Sensor über {base_topic}/ep/{EUI}/cmd Topic."""
        if not self.connected:
            logging.error(f"MQTT nicht verbunden - Command {command} für {sensor_eui} übersprungen")
            return False
        
        try:
            # Service Center Command Topic mit Base Topic
            cmd_topic = f"{self.base_topic}/ep/{sensor_eui}/cmd"
            
            result = self.client.publish(cmd_topic, command, retain=False)
            success = result.rc == mqtt.MQTT_ERR_SUCCESS
            
            if success:
                logging.info(f"📡 Sensor Command gesendet: {sensor_eui} → {cmd_topic} ('{command}')")
            else:
                logging.error(f"❌ Sensor Command fehlgeschlagen für {sensor_eui}: {command}")
                
            return success
            
        except Exception as e:
            logging.error(f"Fehler beim Senden des Sensor Commands für {sensor_eui}: {e}")
            return False
    
    def publish_sensor_status(self, sensor_eui: str, status_data: Dict[str, Any]) -> bool:
        """Sende Sensor Status Update."""
        if not self.connected:
            logging.error(f"MQTT nicht verbunden - Status für {sensor_eui} übersprungen")
            return False
        
        try:
            status_topic = f"{self.base_topic}/ep/{sensor_eui}/status"
            payload = json.dumps(status_data)
            
            result = self.client.publish(status_topic, payload, retain=True)
            success = result.rc == mqtt.MQTT_ERR_SUCCESS
            
            if success:
                logging.info(f"📊 Sensor Status gesendet: {sensor_eui} → {status_topic}")
            else:
                logging.error(f"❌ Sensor Status fehlgeschlagen für {sensor_eui}")
                
            return success
            
        except Exception as e:
            logging.error(f"Fehler beim Senden des Sensor Status für {sensor_eui}: {e}")
            return False
    
    def send_individual_sensor_discoveries(self, sensor_eui: str, decoded_data: Dict[str, Any], device_name: str = "mioty Sensor", snr: float = None, rssi: float = None) -> bool:
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
            "co2_ppm": {
                "name": "CO2",
                "device_class": "carbon_dioxide",
                "unit_of_measurement": "ppm",
                "icon": "mdi:molecule-co2"
            },
            "co2": {
                "name": "CO2",
                "device_class": "carbon_dioxide",
                "unit_of_measurement": "ppm",
                "icon": "mdi:molecule-co2"
            },
            "alarm": {
                "name": "Alarm Status",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:alert-circle"
            },
            "up_cnt": {
                "name": "Upload Counter",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:counter"
            },
            "base_id": {
                "name": "Base ID",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:identifier"
            },
            "major_version": {
                "name": "Major Version",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:numeric"
            },
            "minor_version": {
                "name": "Minor Version",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:numeric"
            },
            "product_version": {
                "name": "Product Version",
                "device_class": None,
                "unit_of_measurement": "",
                "icon": "mdi:numeric"
            }
        }
        
        success_count = 0
        total_count = 0
        
        try:
            # Discovery für dekodierte Messwerte
            if decoded_data:
                for measurement_key, measurement_value in decoded_data.items():
                    if measurement_key in sensor_configs:
                        config_topic = f"homeassistant/sensor/mioty_{sensor_eui}/{measurement_key}/config"
                        state_topic = f"homeassistant/sensor/mioty_{sensor_eui}/{measurement_key}/state"
                        availability_topic = f"homeassistant/sensor/mioty_{sensor_eui}/{measurement_key}/availability"
                        
                        sensor_config = sensor_configs[measurement_key]
                        discovery_payload = {
                            "name": f"{device_name} {sensor_config['name']}",
                            "unique_id": f"mioty_{sensor_eui}_{measurement_key}",
                            "state_topic": state_topic,
                            "availability_topic": availability_topic,
                            "device": device_info,
                            "icon": sensor_config["icon"]
                        }
                        
                        if sensor_config["device_class"]:
                            discovery_payload["device_class"] = sensor_config["device_class"]
                        if sensor_config["unit_of_measurement"]:
                            discovery_payload["unit_of_measurement"] = sensor_config["unit_of_measurement"]
                        
                        result = self.ha_client.publish(config_topic, json.dumps(discovery_payload), retain=True)
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            success_count += 1
                            logging.info(f"🔧 Korrekte Discovery: {sensor_eui} - {sensor_config['name']} → {config_topic}")
                        total_count += 1
            
            # Immer SNR Discovery erstellen
            config_topic = f"homeassistant/sensor/mioty_{sensor_eui}/snr/config"
            state_topic = f"homeassistant/sensor/mioty_{sensor_eui}/snr/state"
            availability_topic = f"homeassistant/sensor/mioty_{sensor_eui}/snr/availability"
            
            discovery_payload = {
                "name": f"{device_name} SNR",
                "unique_id": f"mioty_{sensor_eui}_snr",
                "state_topic": state_topic,
                "availability_topic": availability_topic,
                "device": device_info,
                "device_class": "signal_strength",
                "unit_of_measurement": "dB",
                "icon": "mdi:signal"
            }
            
            result = self.ha_client.publish(config_topic, json.dumps(discovery_payload), retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                success_count += 1
                logging.info(f"🔧 Korrekte Discovery: {sensor_eui} - SNR → {config_topic}")
            total_count += 1
            
            # Immer RSSI Discovery erstellen
            config_topic = f"homeassistant/sensor/mioty_{sensor_eui}/rssi/config"
            state_topic = f"homeassistant/sensor/mioty_{sensor_eui}/rssi/state"
            availability_topic = f"homeassistant/sensor/mioty_{sensor_eui}/rssi/availability"
            
            discovery_payload = {
                "name": f"{device_name} RSSI",
                "unique_id": f"mioty_{sensor_eui}_rssi",
                "state_topic": state_topic,
                "availability_topic": availability_topic,
                "device": device_info,
                "device_class": "signal_strength",
                "unit_of_measurement": "dBm",
                "icon": "mdi:wifi"
            }
            
            result = self.ha_client.publish(config_topic, json.dumps(discovery_payload), retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                success_count += 1
                logging.info(f"🔧 Korrekte Discovery: {sensor_eui} - RSSI → {config_topic}")
            total_count += 1
            
            # EUI Discovery erstellen
            config_topic = f"homeassistant/sensor/mioty_{sensor_eui}/eui/config"
            state_topic = f"homeassistant/sensor/mioty_{sensor_eui}/eui/state"
            availability_topic = f"homeassistant/sensor/mioty_{sensor_eui}/eui/availability"
            
            discovery_payload = {
                "name": f"{device_name} EUI (Serial Number)",
                "unique_id": f"mioty_{sensor_eui}_eui",
                "state_topic": state_topic,
                "availability_topic": availability_topic,
                "device": device_info,
                "icon": "mdi:identifier"
            }
            
            result = self.ha_client.publish(config_topic, json.dumps(discovery_payload), retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                success_count += 1
                logging.info(f"🔧 Korrekte Discovery: {sensor_eui} - EUI (Serial Number) → {config_topic}")
            total_count += 1
                
        except Exception as e:
            logging.error(f"Fehler beim Individual Discovery für {sensor_eui}: {e}")
            return False
                
        logging.info(f"✅ Korrekte Discovery abgeschlossen: {success_count}/{total_count} Messwerte für {sensor_eui}")
        return success_count > 0
    
    
    def _handle_remote_ep_command(self, topic_parts: list, payload: str):
        """Verarbeite Remote EP Commands (bssci/ep/{EUI}/cmd)."""
        try:
            if len(topic_parts) >= 3:
                sensor_eui = topic_parts[2]
                command = payload.strip()
                
                logging.info(f"🔧 Remote EP Command empfangen: {sensor_eui} → '{command}'")
                
                # Command-spezifische Verarbeitung
                if command == "attach":
                    logging.info(f"📡 Remote Attach Command für {sensor_eui}")
                elif command == "detach":
                    logging.info(f"📤 Remote Detach Command für {sensor_eui}")
                elif command == "status":
                    logging.info(f"📊 Remote Status Request für {sensor_eui}")
                
                # Command Response senden (gemäß Service Center Doku: EP/{EUI}/response)
                response_data = {
                    "command": command,
                    "status": "received",
                    "timestamp": self._get_timestamp()
                }
                
                response_topic = f"{self.base_topic}/ep/{sensor_eui}/response"
                self.publish_config(response_topic, response_data, confirm=False)
                
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten des Remote EP Commands: {e}")
    
    def _handle_sensor_command(self, sensor_eui: str, data: Dict[str, Any]):
        """Verarbeite Standard Sensor Commands."""
        try:
            command = data.get("command", "")
            logging.info(f"⚡ Standard Sensor Command: {sensor_eui} → '{command}'")
            
            # Command-spezifische Verarbeitung
            if command == "attach":
                logging.info(f"📡 Standard Attach Command für {sensor_eui}")
            elif command == "detach":
                logging.info(f"📤 Standard Detach Command für {sensor_eui}")
            elif command == "status":
                logging.info(f"📊 Standard Status Request für {sensor_eui}")
            
            # Response senden
            response_data = {
                "command": command,
                "status": "processed",
                "sensor_eui": sensor_eui,
                "timestamp": self._get_timestamp()
            }
            
            response_topic = f"{self.base_topic}/ep/{sensor_eui}/response"
            self.publish_config(response_topic, response_data, confirm=False)
            
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten des Sensor Commands: {e}")
    
    def _handle_sensor_registration(self, sensor_eui: str, data: Dict[str, Any]):
        """Verarbeite Legacy Sensor Registration (RECOMMENDED METHOD)."""
        try:
            nw_key = data.get("nwKey", "")
            short_addr = data.get("shortAddr", "")
            bidirectional = data.get("bidi", False)
            
            logging.info(f"🎯 Legacy Registration Details:")
            logging.info(f"   📍 Sensor EUI: {sensor_eui}")
            logging.info(f"   🔑 Network Key: {nw_key}")
            logging.info(f"   📨 Short Address: {short_addr}")
            logging.info(f"   ↔️ Bidirectional: {bidirectional}")
            
            # Registration Response senden
            response_data = {
                "registration": "received",
                "sensor_eui": sensor_eui,
                "status": "processing",
                "timestamp": self._get_timestamp()
            }
            
            response_topic = f"{self.base_topic}/ep/{sensor_eui}/response"
            self.publish_config(response_topic, response_data, confirm=False)
            
            logging.info(f"✅ Legacy Registration Response gesendet für {sensor_eui}")
            
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der Legacy Registration: {e}")
    
    def _handle_downlink_message(self, sensor_eui: str, data: Dict[str, Any]):
        """Verarbeite Downlink Messages."""
        try:
            logging.info(f"📥 Downlink Message empfangen: {sensor_eui}")
            logging.debug(f"Downlink Data: {data}")
            
            # Downlink-Verarbeitung hier implementieren
            # z.B. an Service Center weiterleiten
            
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der Downlink Message: {e}")
    
    def _handle_command_response(self, sensor_eui: str, data: Dict[str, Any]):
        """Verarbeite Command Responses."""
        try:
            command = data.get("command", "unknown")
            status = data.get("status", "unknown")
            
            logging.info(f"📝 Command Response: {sensor_eui} → {command}: {status}")
            
            # Response-Verarbeitung hier implementieren
            
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der Command Response: {e}")
    
    def _handle_status_update(self, sensor_eui: str, data: Dict[str, Any]):
        """Verarbeite Status Updates."""
        try:
            action = data.get("action", "unknown")
            logging.info(f"📊 Status Update: {sensor_eui} → {action}")
            
            if action == "auto_detached":
                reason = data.get("reason", "unknown")
                inactive_hours = data.get("inactive_hours", 0)
                logging.warning(f"⚠️ Sensor auto-detached: {sensor_eui} ({reason}, {inactive_hours}h inactive)")
            
            # Status-Update-Verarbeitung hier implementieren
            
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten des Status Updates: {e}")
    
    def _handle_warning_notification(self, sensor_eui: str, data: Dict[str, Any]):
        """Verarbeite Warning Notifications."""
        try:
            action = data.get("action", "unknown")
            logging.warning(f"⚠️ Warning: {sensor_eui} → {action}")
            
            if action == "inactivity_warning":
                inactive_hours = data.get("inactive_hours", 0)
                hours_until_detach = data.get("hours_until_detach", 0)
                logging.warning(f"⏰ Inactivity Warning: {sensor_eui} ({inactive_hours}h inactive, {hours_until_detach}h until detach)")
            
            # Warning-Verarbeitung hier implementieren
            
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der Warning Notification: {e}")
    
    def _handle_error_notification(self, sensor_eui: str, data: Dict[str, Any]):
        """Verarbeite Error Notifications."""
        try:
            error_type = data.get("error_type", "unknown")
            error_message = data.get("message", "")
            
            logging.error(f"❌ Error Notification: {sensor_eui} → {error_type}: {error_message}")
            
            # Error-Verarbeitung hier implementieren
            
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der Error Notification: {e}")
    
    def _get_timestamp(self) -> float:
        """Gibt aktuellen Timestamp zurück."""
        import time
        return time.time()  # Erfolgreich "deaktiviert"
        
        # ❌ KOMPLETT DEAKTIVIERT - ALLE ALTER CODE ENTFERNT
        # Individual Discovery System wurde durch einheitliche Topic-Struktur ersetzt
    
    def publish_sensor_state_json(self, sensor_eui: str, decoded_data: Dict[str, Any]) -> bool:
        """Sende Sensor-Status als JSON für alle individuellen Sensoren."""
        if not self.ha_connected or not self.ha_client:
            logging.debug("HA MQTT nicht verfügbar - JSON State übersprungen")
            return False
        
        try:
            # Normalisiere Sensor EUI für MQTT Topics
            sensor_eui = self._normalize_sensor_eui(sensor_eui)
            
            # State Topic
            state_topic = f"homeassistant/sensor/{sensor_eui}/state"
            
            # JSON Payload mit nur den Werten (ohne Metadaten)
            state_payload = {}
            for key, data in decoded_data.items():
                if isinstance(data, dict) and 'value' in data:
                    state_payload[key] = data['value']
                    
            # Availability setzen
            availability_topic = f"homeassistant/sensor/{sensor_eui}/availability"
            self.ha_client.publish(availability_topic, "online", retain=True)
            
            # State senden
            result = self.ha_client.publish(state_topic, json.dumps(state_payload), retain=True)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"📊 JSON State Update: {sensor_eui} → {len(state_payload)} Werte")
                return True
            else:
                logging.warning(f"⚠️ JSON State Update fehlgeschlagen: {sensor_eui}")
                return False
                
        except Exception as e:
            logging.error(f"Fehler beim Senden des JSON Sensor-Status: {e}")
            return False

    def is_connected(self) -> bool:
        """Prüfe MQTT Verbindungsstatus."""
        return self.connected