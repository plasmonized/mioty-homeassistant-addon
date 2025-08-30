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
    """MQTT Manager für Home Assistant Integration."""
    
    def __init__(self, broker: str, port: int, username: str = "", 
                 password: str = "", base_topic: str = "bssci"):
        """Initialisiere MQTT Manager."""
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.base_topic = base_topic
        
        self.client = None
        self.connected = False
        self.running = False
        
        # Callbacks
        self.data_callback: Optional[Callable] = None
        self.config_callback: Optional[Callable] = None
        self.base_station_callback: Optional[Callable] = None
        
        logging.info(f"MQTT Manager initialisiert für {broker}:{port}")
    
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
        """Verbinde mit MQTT Broker."""
        try:
            self.client = mqtt.Client()
            
            # Authentication
            if self.username:
                self.client.username_pw_set(self.username, self.password)
            
            # Callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Verbinden
            logging.info(f"Verbinde mit MQTT Broker {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, 60)
            
            # Loop starten
            self.client.loop_start()
            self.running = True
            
            # Auf Verbindung warten
            timeout = 10
            while timeout > 0 and not self.connected:
                time.sleep(1)
                timeout -= 1
            
            if not self.connected:
                raise Exception("MQTT Verbindung Timeout")
            
            return True
            
        except Exception as e:
            logging.error(f"MQTT Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        """Trenne MQTT Verbindung."""
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            
        logging.info("MQTT Verbindung getrennt")
    
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
        logging.warning("MQTT Verbindung getrennt")
    
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
                logging.debug(f"Base Station Status: {bs_eui}")
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON Parse Fehler: {e}")
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der BSSCI Nachricht: {e}")
    
    def publish_discovery(self, topic: str, config: Dict[str, Any] | str) -> bool:
        """Sende Home Assistant Discovery Konfiguration."""
        if not self.connected:
            return False
        
        try:
            payload = json.dumps(config) if isinstance(config, dict) else config
            result = self.client.publish(topic, payload, retain=True)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            logging.error(f"Fehler beim Senden der Discovery Konfiguration: {e}")
            return False
    
    def publish_sensor_state(self, unique_id: str, state: Any, attributes: Dict[str, Any]) -> bool:
        """Sende Sensor-Status an Home Assistant."""
        if not self.connected:
            return False
        
        try:
            # State Topic
            state_topic = f"homeassistant/sensor/{unique_id}/state"
            self.client.publish(state_topic, str(state))
            
            # Attributes Topic
            attr_topic = f"homeassistant/sensor/{unique_id}/attributes"
            attr_payload = json.dumps(attributes)
            self.client.publish(attr_topic, attr_payload)
            
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