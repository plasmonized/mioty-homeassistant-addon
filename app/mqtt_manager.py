"""
MQTT Manager für BSSCI mioty Add-on
Verwaltet die MQTT-Kommunikation mit Home Assistant
"""

import json
import logging
import threading
import time
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
        
        logging.info(f"Dual MQTT Manager - mioty: {broker}:{port}, HA: {ha_broker}:{ha_port}")
    
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
            self.client = mqtt.Client(client_id="bssci_mioty_client")
            
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
            self.ha_client = mqtt.Client(client_id="bssci_ha_client")
            
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
            logging.info("MQTT erfolgreich verbunden")
            
            # Topics abonnieren
            self._subscribe_topics()
            
        else:
            logging.error(f"MQTT Verbindung fehlgeschlagen: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT Disconnect Callback."""
        self.connected = False
        logging.warning("mioty MQTT Verbindung getrennt")
    
    def _on_ha_connect(self, client, userdata, flags, rc):
        """Home Assistant MQTT Connect Callback."""
        if rc == 0:
            self.ha_connected = True
            logging.info("Home Assistant MQTT erfolgreich verbunden")
        else:
            logging.error(f"Home Assistant MQTT Verbindung fehlgeschlagen: {rc}")
    
    def _on_ha_disconnect(self, client, userdata, rc):
        """Home Assistant MQTT Disconnect Callback."""
        self.ha_connected = False
        logging.warning("Home Assistant MQTT Verbindung getrennt")
    
    def _on_message(self, client, userdata, msg):
        """MQTT Message Callback."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logging.debug(f"MQTT Nachricht: {topic}")
            
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
            self.client.subscribe(topic)
            logging.info(f"MQTT Topic abonniert: {topic}")
    
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
    
    def is_connected(self) -> bool:
        """Prüfe MQTT Verbindungsstatus."""
        return self.connected