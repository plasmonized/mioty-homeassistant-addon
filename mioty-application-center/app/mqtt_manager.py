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
                    # Sensor-Daten (Uplink)
                    logging.info(f"📡 Sensor Uplink: {sensor_eui}")
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
    
    def send_individual_sensor_discoveries(self, sensor_eui: str, decoded_data: Dict[str, Any], device_name: str = "mioty Sensor") -> bool:
        """DEAKTIVIERT: Individual Discovery System (40+ Topics pro Sensor) - ersetzt durch einheitliche Topic-Struktur."""
        logging.debug(f"Individual Discovery System deaktiviert für {sensor_eui} - einheitliche Struktur verwendet")
        return True
    
    
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
                self.publish_config(response_topic, response_data)
                
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
            self.publish_config(response_topic, response_data)
            
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
            self.publish_config(response_topic, response_data)
            
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