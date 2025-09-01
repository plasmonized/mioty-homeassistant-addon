#!/usr/bin/env python3
"""
BSSCI mioty Home Assistant Add-on
Hauptanwendung für die Verwaltung von mioty Sensoren
"""

import os
import sys
import json
import time
import logging
import threading
from typing import Dict, Any

# Import modules
from mqtt_manager import MQTTManager
from bssci_client import BSSCIClient
from web_gui import WebGUI
from decoder_manager import DecoderManager
from settings_manager import SettingsManager

class BSSCIAddon:
    """Hauptklasse für das BSSCI mioty Add-on."""
    
    def __init__(self):
        """Initialisiere das Add-on."""
        self.setup_logging()
        self.config = self.load_config()
        
        # Komponenten
        self.mqtt_manager = None
        self.bssci_client = None
        self.web_gui = None
        self.decoder_manager = None
        
        # Status
        self.running = False
        self.sensors = {}
        self.base_stations = {}
        
        logging.info("BSSCI mioty Add-on initialisiert")
    
    def setup_logging(self):
        """Konfiguriere Logging."""
        log_level = os.getenv('LOG_LEVEL', 'info').upper()
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        
        # Reduziere MQTT Client Logs
        logging.getLogger('paho').setLevel(logging.WARNING)
    
    def load_config(self) -> Dict[str, Any]:
        """Lade Konfiguration aus gespeicherten Einstellungen oder Environment Variables."""
        # Versuche zuerst gespeicherte Einstellungen zu laden
        try:
            settings = SettingsManager()
            saved_settings = settings.get_all_settings()
            
            # Kombiniere gespeicherte Einstellungen mit Environment Variables als Fallback
            config = {
                'mqtt_broker': saved_settings.get('mqtt_broker') or os.getenv('MQTT_BROKER', 'akahlig.selfhost.co'),
                'mqtt_port': saved_settings.get('mqtt_port') or int(os.getenv('MQTT_PORT', '1887')),
                'mqtt_username': saved_settings.get('mqtt_username') or os.getenv('MQTT_USERNAME', 'Hasso'),
                'mqtt_password': saved_settings.get('mqtt_password') or os.getenv('MQTT_PASSWORD', 'test=1234'),
                'ha_mqtt_broker': saved_settings.get('ha_mqtt_broker') or os.getenv('HA_MQTT_BROKER', 'core-mosquitto'),
                'ha_mqtt_port': saved_settings.get('ha_mqtt_port') or int(os.getenv('HA_MQTT_PORT', '1883')),
                'ha_mqtt_username': saved_settings.get('ha_mqtt_username') or os.getenv('HA_MQTT_USERNAME', ''),
                'ha_mqtt_password': saved_settings.get('ha_mqtt_password') or os.getenv('HA_MQTT_PASSWORD', ''),
                'bssci_service_url': os.getenv('BSSCI_SERVICE_URL', 'localhost:16018'),
                'base_topic': saved_settings.get('base_topic') or os.getenv('BASE_TOPIC', 'bssci'),
                'auto_discovery': saved_settings.get('auto_discovery', True) if saved_settings.get('auto_discovery') is not None else (os.getenv('AUTO_DISCOVERY', 'true').lower() == 'true'),
                'web_port': int(os.getenv('WEB_PORT', '5000'))
            }
            return config
        except Exception as e:
            logging.warning(f"Konnte gespeicherte Einstellungen nicht laden: {e}, verwende Environment Variables")
            # Fallback zu Environment Variables
            return {
                'mqtt_broker': os.getenv('MQTT_BROKER', 'akahlig.selfhost.co'),
                'mqtt_port': int(os.getenv('MQTT_PORT', '1887')),
                'mqtt_username': os.getenv('MQTT_USERNAME', 'Hasso'),
                'mqtt_password': os.getenv('MQTT_PASSWORD', 'test=1234'),
                'ha_mqtt_broker': os.getenv('HA_MQTT_BROKER', 'core-mosquitto'),
                'ha_mqtt_port': int(os.getenv('HA_MQTT_PORT', '1883')),
                'ha_mqtt_username': os.getenv('HA_MQTT_USERNAME', ''),
                'ha_mqtt_password': os.getenv('HA_MQTT_PASSWORD', ''),
                'bssci_service_url': os.getenv('BSSCI_SERVICE_URL', 'localhost:16018'),
                'base_topic': os.getenv('BASE_TOPIC', 'bssci'),
                'auto_discovery': os.getenv('AUTO_DISCOVERY', 'true').lower() == 'true',
                'web_port': int(os.getenv('WEB_PORT', '5000'))
            }
    
    def start(self):
        """Starte das Add-on."""
        logging.info("Starte BSSCI mioty Add-on...")
        
        try:
            # Dual MQTT Manager starten (extern für mioty + HA für Discovery)
            self.mqtt_manager = MQTTManager(
                # Externe mioty MQTT Verbindung
                broker=self.config['mqtt_broker'],
                port=self.config['mqtt_port'],
                username=self.config['mqtt_username'],
                password=self.config['mqtt_password'],
                base_topic=self.config['base_topic'],
                # Home Assistant MQTT Verbindung
                ha_broker=self.config['ha_mqtt_broker'],
                ha_port=self.config['ha_mqtt_port'],
                ha_username=self.config['ha_mqtt_username'],
                ha_password=self.config['ha_mqtt_password']
            )
            self.mqtt_manager.set_data_callback(self.handle_sensor_data)
            self.mqtt_manager.set_config_callback(self.handle_sensor_config)
            self.mqtt_manager.set_base_station_callback(self.handle_base_station_data)
            
            # BSSCI Client starten (optional, falls direkter Zugriff gewünscht)
            # self.bssci_client = BSSCIClient(self.config['bssci_service_url'])
            
            # Decoder Manager starten (verwende lokales Verzeichnis in Demo-Umgebung)
            decoder_dir = "decoders" if os.path.exists("demo_run.py") else "/data/decoders"
            self.decoder_manager = DecoderManager(decoder_dir)
            
            # Web GUI starten
            self.web_gui = WebGUI(
                port=self.config['web_port'],
                addon_instance=self
            )
            
            # MQTT verbinden
            self.mqtt_manager.connect()
            
            # Web GUI in separatem Thread starten
            web_thread = threading.Thread(target=self.web_gui.run, daemon=True)
            web_thread.start()
            
            # Haupt-Loop
            self.running = True
            logging.info("Add-on erfolgreich gestartet")
            
            while self.running:
                try:
                    # Status-Updates verarbeiten
                    self.process_status_updates()
                    time.sleep(1)
                    
                except KeyboardInterrupt:
                    logging.info("Shutdown angefordert")
                    break
                except Exception as e:
                    logging.error(f"Fehler in Haupt-Loop: {e}")
                    time.sleep(5)
        
        except Exception as e:
            logging.error(f"Fehler beim Starten: {e}")
            sys.exit(1)
        
        finally:
            self.shutdown()
    
    def handle_sensor_data(self, sensor_eui: str, data: Dict[str, Any]):
        """Verarbeite eingehende Sensor-Daten."""
        raw_payload = data.get('data', 'N/A')
        logging.info(f"Sensor-Daten empfangen von {sensor_eui}")
        logging.info(f"Raw Payload: {raw_payload}")
        
        # Payload dekodieren falls Decoder zugewiesen ist
        decoded_payload = None
        if self.decoder_manager and 'data' in data:
            try:
                payload_bytes = data['data']
                metadata = {
                    'snr': data.get('snr'),
                    'rssi': data.get('rssi'),
                    'timestamp': data.get('rxTime'),
                    'base_station': data.get('bs_eui')
                }
                logging.info(f"Metadata: SNR={metadata.get('snr')}, RSSI={metadata.get('rssi')}, Base Station={metadata.get('base_station')}")
                
                decoded_result = self.decoder_manager.decode_sensor_payload(
                    sensor_eui, payload_bytes, metadata
                )
                if decoded_result.get('decoded'):
                    decoded_payload = decoded_result
                    logging.info(f"✅ Payload für {sensor_eui} erfolgreich dekodiert")
                    logging.info(f"🔍 Dekodierte Daten: {json.dumps(decoded_result.get('data', {}), indent=2)}")
                else:
                    logging.warning(f"❌ Payload für {sensor_eui} nicht dekodiert: {decoded_result.get('reason', 'Unknown')}")
                    logging.info(f"Raw Payload Hex: {payload_bytes}")
            except Exception as e:
                logging.error(f"Fehler beim Dekodieren von Sensor {sensor_eui}: {e}")
                logging.info(f"Problematischer Raw Payload: {raw_payload}")
        
        # Sensor-Daten speichern
        self.sensors[sensor_eui] = {
            'last_seen': time.time(),
            'data': data,
            'decoded_payload': decoded_payload,
            'signal_quality': self.assess_signal_quality(
                data.get('snr', 0), 
                data.get('rssi', -100)
            )
        }
        
        # Home Assistant Discovery
        if self.config['auto_discovery'] and self.mqtt_manager:
            self.create_sensor_discovery(sensor_eui, data, decoded_payload)
    
    def handle_sensor_config(self, sensor_eui: str, config: Dict[str, Any]):
        """Verarbeite Sensor-Konfigurationsanfragen."""
        logging.info(f"Konfiguration für Sensor {sensor_eui}: {config}")
        
        # Hier würde die Konfiguration an das BSSCI Service Center weitergeleitet
        # Da wir über MQTT kommunizieren, nehmen wir an, dass das bereits geschehen ist
    
    def handle_base_station_data(self, bs_eui: str, data: Dict[str, Any]):
        """Verarbeite Base Station Status-Daten."""
        logging.info(f"Base Station Status empfangen von {bs_eui}")
        
        # Base Station Daten speichern
        self.base_stations[bs_eui] = {
            'last_seen': time.time(),
            'data': data,
            'status': 'online' if data else 'offline'
        }
        
        # Home Assistant Discovery für Base Station
        if self.config['auto_discovery']:
            try:
                self.create_basestation_discovery(bs_eui, data)
            except AttributeError:
                logging.debug(f"Base Station Discovery für {bs_eui} übersprungen")
    
    def handle_base_station_status(self, bs_eui: str, status: Dict[str, Any]):
        """Verarbeite Base Station Status."""
        logging.debug(f"Base Station Status: {bs_eui}")
        
        self.base_stations[bs_eui] = {
            'last_seen': time.time(),
            'status': status
        }
        
        # Home Assistant Discovery für Base Station
        if self.config['auto_discovery']:
            self.create_basestation_discovery(bs_eui, status)
    
    def create_sensor_discovery(self, sensor_eui: str, data: Dict[str, Any], decoded_payload: Dict[str, Any] = None):
        """Erstelle Home Assistant MQTT Discovery für Sensor."""
        device_name = f"mioty Sensor {sensor_eui}"
        unique_id = f"bssci_sensor_{sensor_eui}"
        
        # Discovery Konfiguration
        discovery_config = {
            "name": device_name,
            "unique_id": unique_id,
            "state_topic": f"homeassistant/sensor/{unique_id}/state",
            "json_attributes_topic": f"homeassistant/sensor/{unique_id}/attributes",
            "device_class": "data_size",
            "unit_of_measurement": "bytes",
            "icon": "mdi:access-point",
            "device": {
                "identifiers": [f"bssci_sensor_{sensor_eui}"],
                "name": device_name,
                "model": "mioty IoT Sensor",
                "manufacturer": "BSSCI"
            }
        }
        
        # Discovery Nachricht senden
        discovery_topic = f"homeassistant/sensor/{unique_id}/config"
        if self.mqtt_manager:
            self.mqtt_manager.publish_discovery(discovery_topic, discovery_config)
        
        # Status und Attribute senden
        state_value = len(data.get('data', []))
        attributes = {
            "sensor_eui": sensor_eui,
            "base_station_eui": data.get('bs_eui', 'Unknown'),
            "snr": data.get('snr'),
            "rssi": data.get('rssi'),
            "message_counter": data.get('cnt'),
            "receive_time": self.format_timestamp(data.get('rxTime')),
            "signal_quality": self.assess_signal_quality(data.get('snr'), data.get('rssi')),
            "raw_data": data.get('data', [])[:10],  # Nur erste 10 Bytes zeigen
            "decoded_data": decoded_payload.get('data') if decoded_payload else None,
            "decoder_used": decoded_payload.get('decoder_name') if decoded_payload else None
        }
        
        if self.mqtt_manager:
            self.mqtt_manager.publish_sensor_state(unique_id, state_value, attributes)
    
    def create_basestation_discovery(self, bs_eui: str, status: Dict[str, Any]):
        """Erstelle Home Assistant MQTT Discovery für Base Station."""
        device_name = f"mioty Base Station {bs_eui}"
        unique_id = f"bssci_basestation_{bs_eui}"
        
        discovery_config = {
            "name": device_name,
            "unique_id": unique_id,
            "state_topic": f"homeassistant/sensor/{unique_id}/state",
            "json_attributes_topic": f"homeassistant/sensor/{unique_id}/attributes",
            "device_class": "connectivity",
            "icon": "mdi:antenna",
            "device": {
                "identifiers": [f"bssci_basestation_{bs_eui}"],
                "name": device_name,
                "model": "MBS20 Base Station",
                "manufacturer": "Swissphone"
            }
        }
        
        discovery_topic = f"homeassistant/sensor/{unique_id}/config"
        if self.mqtt_manager:
            self.mqtt_manager.publish_discovery(discovery_topic, discovery_config)
        
        # Status
        state_value = "online" if status.get('code', 1) == 0 else "offline"
        attributes = {
            "base_station_eui": bs_eui,
            "status_code": status.get('code'),
            "memory_load": f"{status.get('memLoad', 0) * 100:.1f}%",
            "cpu_load": f"{status.get('cpuLoad', 0) * 100:.1f}%",
            "duty_cycle": f"{status.get('dutyCycle', 0) * 100:.1f}%",
            "uptime": self.format_uptime(status.get('uptime', 0)),
            "last_seen": self.format_timestamp(status.get('time'))
        }
        
        if self.mqtt_manager:
            self.mqtt_manager.publish_sensor_state(unique_id, state_value, attributes)
    
    def assess_signal_quality(self, snr, rssi) -> str:
        """Bewerte Signalqualität."""
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
    
    def format_timestamp(self, timestamp_ns) -> str:
        """Formatiere Timestamp."""
        if not timestamp_ns:
            return "Unknown"
        
        try:
            from datetime import datetime
            timestamp_s = timestamp_ns / 1_000_000_000
            dt = datetime.fromtimestamp(timestamp_s)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "Invalid"
    
    def format_uptime(self, seconds: int) -> str:
        """Formatiere Uptime."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
    
    def process_status_updates(self):
        """Verarbeite regelmäßige Status-Updates."""
        # Hier könnte regelmäßige Überwachung implementiert werden
        pass
    
    def add_sensor(self, sensor_eui: str, network_key: str, short_addr: str, bidirectional: bool = False) -> bool:
        """Füge einen neuen Sensor hinzu."""
        config = {
            "nwKey": network_key,
            "shortAddr": short_addr,
            "bidi": bidirectional
        }
        
        # Konfiguration über MQTT senden
        topic = f"{self.config['base_topic']}/ep/{sensor_eui}/config"
        if self.mqtt_manager:
            return self.mqtt_manager.publish_config(topic, config)
        return False
    
    def remove_sensor(self, sensor_eui: str) -> bool:
        """Entferne einen Sensor."""
        if sensor_eui in self.sensors:
            # Sensor aus lokaler Liste entfernen
            del self.sensors[sensor_eui]
            
            # Discovery-Konfiguration löschen
            unique_id = f"bssci_sensor_{sensor_eui}"
            discovery_topic = f"homeassistant/sensor/{unique_id}/config"
            if self.mqtt_manager:
                self.mqtt_manager.publish_discovery(discovery_topic, "")
            
            return True
        return False
    
    def get_sensor_list(self) -> Dict[str, Any]:
        """Gibt Liste aller Sensoren zurück."""
        return self.sensors.copy()
    
    def get_basestation_list(self) -> Dict[str, Any]:
        """Gibt Liste aller Base Stations zurück."""
        return self.base_stations.copy()
    
    def shutdown(self):
        """Beende das Add-on sauber."""
        logging.info("Beende BSSCI mioty Add-on...")
        
        self.running = False
        
        if self.mqtt_manager:
            self.mqtt_manager.disconnect()
        
        if self.web_gui:
            self.web_gui.shutdown()
        
        logging.info("Add-on beendet")


if __name__ == "__main__":
    addon = BSSCIAddon()
    addon.start()