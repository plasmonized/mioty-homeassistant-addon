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
            # REPARIERT: Absoluter Pfad für Add-on Umgebung
            # Persistente Speicherung in /data für Home Assistant Add-on
            if os.path.exists('/data'):
                settings_path = '/data/settings.json'
            else:
                settings_path = 'settings.json'  # Fallback für Entwicklung
            settings = SettingsManager(settings_path)
            saved_settings = settings.get_all_settings()
            logging.info(f"🔧 SETTINGS PFAD: {settings_path}")
            
            # Kombiniere gespeicherte Einstellungen mit Environment Variables als Fallback
            config = {
                'mqtt_broker': saved_settings.get('mqtt_broker') or os.getenv('MQTT_BROKER', 'core-mosquitto'),
                'mqtt_port': saved_settings.get('mqtt_port') or int(os.getenv('MQTT_PORT', '1883')),
                'mqtt_username': saved_settings.get('mqtt_username') or os.getenv('MQTT_USERNAME', ''),
                'mqtt_password': saved_settings.get('mqtt_password') or os.getenv('MQTT_PASSWORD', ''),
                'ha_mqtt_broker': saved_settings.get('ha_mqtt_broker') or os.getenv('HA_MQTT_BROKER', 'core-mosquitto'),
                'ha_mqtt_port': saved_settings.get('ha_mqtt_port') or int(os.getenv('HA_MQTT_PORT', '1883')),
                'ha_mqtt_username': saved_settings.get('ha_mqtt_username') or os.getenv('HA_MQTT_USERNAME', ''),
                'ha_mqtt_password': saved_settings.get('ha_mqtt_password') or os.getenv('HA_MQTT_PASSWORD', ''),

                'base_topic': saved_settings.get('base_topic') or os.getenv('BASE_TOPIC', 'bssci'),
                'auto_discovery': saved_settings.get('auto_discovery', True) if saved_settings.get('auto_discovery') is not None else (os.getenv('AUTO_DISCOVERY', 'true').lower() == 'true'),
                'web_port': int(os.getenv('WEB_PORT', '5000'))
            }
            return config
        except Exception as e:
            logging.warning(f"Konnte gespeicherte Einstellungen nicht laden: {e}, verwende Environment Variables")
            # Fallback zu Environment Variables
            return {
                'mqtt_broker': os.getenv('MQTT_BROKER', 'your-mqtt-broker.com'),
                'mqtt_port': int(os.getenv('MQTT_PORT', '1883')),
                'mqtt_username': os.getenv('MQTT_USERNAME', 'your-username'),
                'mqtt_password': os.getenv('MQTT_PASSWORD', 'your-password'),
                'ha_mqtt_broker': os.getenv('HA_MQTT_BROKER', 'core-mosquitto'),
                'ha_mqtt_port': int(os.getenv('HA_MQTT_PORT', '1883')),
                'ha_mqtt_username': os.getenv('HA_MQTT_USERNAME', ''),
                'ha_mqtt_password': os.getenv('HA_MQTT_PASSWORD', ''),

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
                    logging.info(f"🔧 Decoder: {decoded_result.get('decoder_name', 'Unknown')}")
                    
                    # Saubere Darstellung der decodierten Daten
                    decoded_data = decoded_result.get('data', {})
                    if decoded_data:
                        logging.info("📊 Dekodierte Daten:")
                        for key, value in decoded_data.items():
                            if isinstance(value, dict):
                                value_str = str(value).replace('"', "'")
                                logging.info(f"   {key}: {value_str}")
                            else:
                                logging.info(f"   {key}: {value}")
                    else:
                        logging.info("📊 Dekodierte Daten: (leer)")
                else:
                    logging.warning(f"❌ Payload für {sensor_eui} nicht dekodiert: {decoded_result.get('reason', 'Unknown')}")
                    logging.info(f"🔍 Raw Payload Hex: {payload_bytes}")
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
        
        # Home Assistant Discovery - Individual Sensor Discovery
        if self.config['auto_discovery'] and self.mqtt_manager and decoded_payload:
            try:
                decoded_data = decoded_payload.get('data', {})
                if decoded_data:
                    # SNR und RSSI aus Metadaten extrahieren
                    snr = data.get('snr')
                    rssi = data.get('rssi')
                    
                    # Separate Discovery Messages für jeden Messwert senden (inklusive SNR/RSSI)
                    device_name = f"Sentinum Febris TH"  # TODO: Aus Metadaten extrahieren
                    self.mqtt_manager.send_individual_sensor_discoveries(sensor_eui, decoded_data, device_name, snr, rssi)
                    
                    # Individual State Updates für alle Sensoren senden
                    self.mqtt_manager.publish_individual_sensor_states(sensor_eui, decoded_data, snr, rssi)
                else:
                    logging.debug(f"Keine dekodierte Daten für Discovery: {sensor_eui}")
            except Exception as e:
                logging.error(f"Fehler bei Individual Discovery für {sensor_eui}: {e}")
        
        # Legacy Discovery System deaktiviert - Individual Discovery wird verwendet  
        # elif self.config['auto_discovery'] and self.mqtt_manager:
        #     self.create_sensor_discovery(sensor_eui, data, decoded_payload or {})
    
    def handle_sensor_config(self, sensor_eui: str, config: Dict[str, Any]):
        """Verarbeite Sensor-Konfigurationsanfragen."""
        logging.info(f"Konfiguration für Sensor {sensor_eui}: {config}")
        
        # Hier würde die Konfiguration an das BSSCI Service Center weitergeleitet
        # Da wir über MQTT kommunizieren, nehmen wir an, dass das bereits geschehen ist
    
    def handle_base_station_data(self, bs_eui: str, data: Dict[str, Any]):
        """Verarbeite Base Station Status-Daten."""
        logging.info(f"🏢 HANDLE_BASE_STATION_DATA AUFGERUFEN für {bs_eui}")
        logging.info(f"Base Station Status empfangen von {bs_eui}")
        
        # Base Station Daten speichern
        self.base_stations[bs_eui] = {
            'last_seen': time.time(),
            'data': data,
            'status': 'online' if data else 'offline'
        }
        
        logging.info(f"🗄️ Base Station {bs_eui} in Dictionary gespeichert. Anzahl Base Stations: {len(self.base_stations)}")
        
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
    
    def _get_device_info_from_decoder(self, sensor_eui: str, device_id: str) -> Dict[str, Any]:
        """Extrahiere Device-Informationen aus zugewiesenem Decoder."""
        
        # Standard Fallback-Werte
        device_info = {
            "identifiers": [device_id],
            "name": f"mioty Sensor {sensor_eui}",
            "model": "mioty IoT Sensor",
            "manufacturer": "Unknown",
            "sw_version": "1.0"
        }
        
        # Prüfe manuelle Metadaten zuerst
        try:
            import json
            metadata_file = '/data/manual_sensor_metadata.json' if os.path.exists('/data') else 'manual_sensor_metadata.json'
            with open(metadata_file, 'r') as f:
                manual_metadata = json.load(f)
                if sensor_eui in manual_metadata:
                    manual_info = manual_metadata[sensor_eui]
                    device_info.update({
                        "name": manual_info.get('name', device_info["name"]),
                        "model": manual_info.get('model', device_info["model"]),
                        "manufacturer": manual_info.get('manufacturer', device_info["manufacturer"])
                    })
                    logging.debug(f"🔧 Manuelle Metadaten für {sensor_eui} geladen: {device_info['manufacturer']} - {device_info['model']}")
                    return device_info
        except FileNotFoundError:
            pass
        
        # Prüfe ob Decoder zugewiesen
        if hasattr(self, 'decoder_manager') and self.decoder_manager:
            try:
                # Hole Decoder-Zuweisungen - sicherstellen, dass es ein Dictionary ist
                assignments = getattr(self.decoder_manager.payload_decoder, 'decoders', {})
                if isinstance(assignments, dict) and sensor_eui in assignments:
                    decoder_assignment = assignments[sensor_eui]
                    
                    # Extrahiere decoder_name aus Assignment (kann String oder Dict sein)
                    if isinstance(decoder_assignment, str):
                        # Legacy Format: direkter String
                        decoder_name = decoder_assignment
                    elif isinstance(decoder_assignment, dict):
                        # Neues Format: Dictionary mit decoder_name
                        decoder_name = decoder_assignment.get('decoder_name')
                        if not decoder_name:
                            logging.warning(f"Decoder-Assignment für {sensor_eui} hat keinen decoder_name: {decoder_assignment}")
                            return device_info
                    else:
                        logging.warning(f"Decoder-Assignment für {sensor_eui} hat unbekanntes Format: {type(decoder_assignment)}")
                        return device_info
                    
                    # Validiere, dass decoder_name ein String ist
                    if not isinstance(decoder_name, str):
                        logging.warning(f"Decoder-Name für {sensor_eui} ist kein String: {type(decoder_name)}")
                        return device_info
                    
                    # Hole Decoder-Datei-Informationen - sicherstellen, dass es ein Dictionary ist
                    decoder_files = getattr(self.decoder_manager.payload_decoder, 'decoder_files', {})
                    if isinstance(decoder_files, dict) and decoder_name in decoder_files:
                        decoder_info = decoder_files[decoder_name]
                        
                        # Validiere decoder_info
                        if not isinstance(decoder_info, dict):
                            logging.warning(f"Decoder Info für {decoder_name} ist kein Dictionary: {type(decoder_info)}")
                            return device_info
                        
                        # Extrahiere Device-Informationen aus Decoder
                        if decoder_info.get('type') == 'iodd':
                            # IODD Decoder - verwende Vendor/Device-Informationen
                            vendor_name = decoder_info.get('vendor_name', 'Unknown')
                            device_name = decoder_info.get('device_name', f'mioty Sensor {sensor_eui}')
                            
                            device_info.update({
                                "name": device_name,
                                "model": device_name,
                                "manufacturer": vendor_name
                            })
                            
                        elif decoder_info.get('type') in ['blueprint', 'javascript']:
                            # Blueprint/JS Decoder - verwende Name/Description
                            decoder_display_name = decoder_info.get('name', f'mioty Sensor {sensor_eui}')
                            
                            device_info.update({
                                "name": decoder_display_name,
                                "model": decoder_display_name,
                                "manufacturer": "Sentinum"
                            })
                            
                        logging.debug(f"🔍 Device Info aus Decoder {decoder_name}: {device_info['manufacturer']} - {device_info['model']}")
                        
            except Exception as e:
                logging.warning(f"Fehler beim Extrahieren der Device-Info für {sensor_eui}: {e}")
        
        return device_info
    
    def _get_basestation_info(self, bs_eui: str, device_id: str) -> Dict[str, Any]:
        """Extrahiere Device-Informationen für Base Station."""
        
        # Standard Fallback-Werte für Base Stations
        device_info = {
            "identifiers": [device_id],
            "name": f"mioty Base Station {bs_eui}",
            "model": "mioty Base Station",
            "manufacturer": "Unknown",
            "sw_version": "1.0"
        }
        
        # Prüfe manuelle Metadaten zuerst
        try:
            import json
            metadata_file = '/data/manual_basestation_metadata.json' if os.path.exists('/data') else 'manual_basestation_metadata.json'
            with open(metadata_file, 'r') as f:
                manual_metadata = json.load(f)
                if bs_eui in manual_metadata:
                    manual_info = manual_metadata[bs_eui]
                    device_info.update({
                        "name": manual_info.get('name', device_info["name"]),
                        "model": manual_info.get('model', device_info["model"]),
                        "manufacturer": manual_info.get('manufacturer', device_info["manufacturer"])
                    })
                    logging.debug(f"🔧 Manuelle BaseStation Metadaten für {bs_eui} geladen: {device_info['manufacturer']} - {device_info['model']}")
                    return device_info
        except FileNotFoundError:
            pass
        
        # Fallback: Versuche bekannte Base Station Hersteller zu erkennen
        if bs_eui.startswith('70b3d5'):
            device_info.update({
                "name": f"Swissphone MBS20 {bs_eui}",
                "model": "MBS20 Base Station",
                "manufacturer": "Swissphone"
            })
        elif bs_eui.startswith('3e5446'):
            device_info.update({
                "name": f"Kerlink Base Station {bs_eui}",
                "model": "Kerlink Wirnet",
                "manufacturer": "Kerlink"
            })
        elif bs_eui.startswith('9c65f9'):
            device_info.update({
                "name": f"Industrial Base Station {bs_eui}",
                "model": "Industrial Gateway",
                "manufacturer": "Generic"
            })
        
        return device_info
    
    def _validate_device_info(self, device_info: Dict[str, Any], allow_fallback: bool = True) -> bool:
        """Prüfe ob Device-Informationen vollständig sind."""
        required_fields = ['manufacturer', 'model', 'name']
        
        for field in required_fields:
            value = device_info.get(field, '')
            if not value:
                logging.debug(f"⚠️ Device-Info unvollständig: {field} ist leer")
                return False
            # Bei allow_fallback sind auch "Unknown" Werte OK
            if not allow_fallback and value == 'Unknown':
                logging.debug(f"⚠️ Device-Info unvollständig: {field} = '{value}'")
                return False
        
        return True
        
    def create_sensor_discovery(self, sensor_eui: str, data: Dict[str, Any], decoded_payload: Dict[str, Any] = None):
        """Erstelle Home Assistant MQTT Discovery für Sensor - Automatische Device-Metadaten aus Decodern."""
        device_id = f"mioty_{sensor_eui}"
        
        # 🔍 Device-Informationen aus zugewiesenem Decoder extrahieren
        device_info = self._get_device_info_from_decoder(sensor_eui, device_id)
        device_name = device_info["name"]
        
        # ❗ Prüfe Device-Informationen (mit Fallback erlaubt)
        if not self._validate_device_info(device_info, allow_fallback=True):
            logging.warning(f"❌ Auto Discovery abgebrochen für {sensor_eui}: Device-Informationen unvollständig")
            logging.info(f"💡 Bitte ergänzen Sie Manufacturer/Model über Decoder-Einstellungen")
            return
        
        # ⚠️ Warnung bei Standard-Werten
        if device_info.get('manufacturer') == 'Unknown':
            logging.info(f"💡 {sensor_eui}: Auto Discovery mit Standard-Werten (Manufacturer: Unknown)")
            logging.info(f"   Tipp: Für bessere HA-Integration Decoder mit Device-Metadaten hinzufügen")
        
        # State Topic für JSON-Daten 
        state_topic = f"homeassistant/sensor/{device_id}/state"
        
        # Individuelle Sensoren erstellen (nach HA Discovery Protokoll)
        sensors = [
            {
                "name": "payload_size",
                "display_name": "Payload Size",
                "device_class": "data_size",
                "unit": "B",
                "icon": "mdi:database",
                "value_template": "{{ value_json.payload_size }}"
            },
            {
                "name": "snr",
                "display_name": "Signal-to-Noise Ratio",
                "device_class": "signal_strength", 
                "unit": "dB",
                "icon": "mdi:signal",
                "value_template": "{{ value_json.snr }}"
            },
            {
                "name": "rssi",
                "display_name": "Signal Strength",
                "device_class": "signal_strength",
                "unit": "dBm",
                "icon": "mdi:wifi-strength-3",
                "value_template": "{{ value_json.rssi }}"
            },
            {
                "name": "message_counter",
                "display_name": "Message Counter",
                "device_class": None,
                "unit": None,
                "icon": "mdi:counter",
                "value_template": "{{ value_json.message_counter }}"
            }
        ]
        
        # Decoded Data Sensor hinzufügen falls Decoder aktiv
        if decoded_payload:
            sensors.append({
                "name": "decoded_data",
                "display_name": "Decoded Data",
                "device_class": None,
                "unit": None,
                "icon": "mdi:code-json",
                "value_template": "{{ value_json.decoded_data | default('N/A') }}"
            })
        
        # Für jeden Sensor individuelle Discovery-Nachricht senden
        for sensor in sensors:
            unique_id = f"{device_id}_{sensor['name']}"
            discovery_topic = f"homeassistant/sensor/{device_id}/{sensor['name']}/config"
            
            config = {
                "name": sensor['display_name'],
                "unique_id": unique_id,
                "state_topic": state_topic,
                "value_template": sensor['value_template'],
                "device": device_info,
                "availability_topic": f"homeassistant/sensor/{device_id}/availability",
                "payload_available": "online",
                "payload_not_available": "offline"
            }
            
            # Optional: Device Class, Unit, Icon
            if sensor['device_class']:
                config['device_class'] = sensor['device_class']
            if sensor['unit']:
                config['unit_of_measurement'] = sensor['unit']
            if sensor['icon']:
                config['icon'] = sensor['icon']
            
            # Discovery senden
            if self.mqtt_manager:
                logging.info(f"🔍 Sensor Discovery: {sensor_eui} - {sensor['display_name']}")
                logging.debug(f"   📤 Topic: {discovery_topic}")
                logging.debug(f"   🏷️ Manufacturer: {device_info['manufacturer']} | Model: {device_info['model']}")
                success = self.mqtt_manager.publish_discovery(discovery_topic, config)
                if success:
                    logging.debug(f"✅ {sensor['display_name']} Discovery erfolgreich")
                else:
                    logging.warning(f"❌ {sensor['display_name']} Discovery fehlgeschlagen")
        
        # Device Availability senden
        if self.mqtt_manager:
            availability_topic = f"homeassistant/sensor/{device_id}/availability"
            if self.mqtt_manager.ha_client:
                self.mqtt_manager.ha_client.publish(availability_topic, "online", retain=True)
        
        # JSON State Data senden (nach HA Discovery Protokoll)
        device_id = f"mioty_{sensor_eui}"
        state_topic = f"homeassistant/sensor/{device_id}/state"
        
        # JSON State für alle Sensoren
        state_data = {
            "payload_size": len(data.get('data', [])),
            "snr": data.get('snr'),
            "rssi": data.get('rssi'),
            "message_counter": data.get('cnt'),
            "sensor_eui": sensor_eui,
            "base_station_eui": data.get('bs_eui', 'Unknown'),
            "receive_time": self.format_timestamp(data.get('rxTime')),
            "signal_quality": self.assess_signal_quality(data.get('snr'), data.get('rssi')),
            "decoded_data": decoded_payload.get('data') if decoded_payload else None,
            "decoder_used": decoded_payload.get('decoder_name') if decoded_payload else None
        }
        
        if self.mqtt_manager:
            logging.info(f"📊 Sensor Update: {sensor_eui} → {len(data.get('data', []))} bytes")
            # JSON State zu HA senden
            import json
            if self.mqtt_manager.ha_client:
                success = self.mqtt_manager.ha_client.publish(state_topic, json.dumps(state_data), retain=False)
                if not success:
                    logging.debug(f"⚠️ Sensor State nicht gesendet (HA MQTT nicht verbunden)")
            else:
                logging.debug(f"⚠️ HA MQTT Client nicht verfügbar")
    
    def create_basestation_discovery(self, bs_eui: str, status: Dict[str, Any]):
        """Erstelle Home Assistant MQTT Discovery für Base Station."""
        device_id = f"bssci_basestation_{bs_eui}"
        
        # 🔍 Device-Informationen für Base Station extrahieren
        device_info = self._get_basestation_info(bs_eui, device_id)
        device_name = device_info["name"]
        
        # ❗ Prüfe Device-Informationen (mit Fallback erlaubt)
        if not self._validate_device_info(device_info, allow_fallback=True):
            logging.warning(f"❌ BaseStation Discovery abgebrochen für {bs_eui}: Device-Informationen unvollständig")
            return
        
        # ⚠️ Warnung bei Standard-Werten
        if device_info.get('manufacturer') == 'Unknown':
            logging.info(f"💡 {bs_eui}: BaseStation Discovery mit Standard-Werten (Manufacturer: Unknown)")
            logging.info(f"   Tipp: Base Station Metadaten über manuellen Eintrag hinzufügen")
        
        unique_id = f"bssci_basestation_{bs_eui}"
        
        discovery_config = {
            "name": device_name,
            "unique_id": unique_id,
            "state_topic": f"homeassistant/sensor/{unique_id}/state",
            "json_attributes_topic": f"homeassistant/sensor/{unique_id}/attributes",
            "icon": "mdi:antenna",
            "device": device_info
        }
        
        discovery_topic = f"homeassistant/sensor/{unique_id}/config"
        if self.mqtt_manager:
            logging.info(f"🏢 BaseStation Discovery: {bs_eui}")
            logging.info(f"   📤 Topic: {discovery_topic}")
            logging.info(f"   🏷️ Device: {device_name}")
            success = self.mqtt_manager.publish_discovery(discovery_topic, discovery_config)
            if success:
                logging.info(f"✅ BaseStation Discovery erfolgreich gesendet")
            else:
                logging.warning(f"❌ BaseStation Discovery fehlgeschlagen (HA MQTT nicht verbunden)")
        
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
            logging.debug(f"📊 BaseStation Status Update: {bs_eui} → {state_value}")
            success = self.mqtt_manager.publish_sensor_state(unique_id, state_value, attributes)
            if not success:
                logging.debug(f"⚠️ BaseStation Status nicht gesendet (HA MQTT nicht verbunden)")
    
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
    
    def reload_settings(self):
        """Lade Einstellungen neu und wende sie auf laufendes System an."""
        logging.info("🔄 Settings werden neu geladen...")
        
        try:
            # Neue Settings laden
            old_config = self.config.copy()
            self.config = self.load_config()
            
            # Prüfen ob MQTT Settings geändert wurden
            mqtt_changed = (
                old_config.get('mqtt_broker') != self.config.get('mqtt_broker') or
                old_config.get('mqtt_port') != self.config.get('mqtt_port') or
                old_config.get('mqtt_username') != self.config.get('mqtt_username') or
                old_config.get('mqtt_password') != self.config.get('mqtt_password') or
                old_config.get('ha_mqtt_broker') != self.config.get('ha_mqtt_broker') or
                old_config.get('ha_mqtt_port') != self.config.get('ha_mqtt_port') or
                old_config.get('ha_mqtt_username') != self.config.get('ha_mqtt_username') or
                old_config.get('ha_mqtt_password') != self.config.get('ha_mqtt_password') or
                old_config.get('base_topic') != self.config.get('base_topic')
            )
            
            if mqtt_changed and self.mqtt_manager:
                logging.info("⚙️  MQTT Settings geändert - Verbindung wird neu aufgebaut...")
                
                # Alte Verbindung trennen
                self.mqtt_manager.disconnect()
                
                # Neue MQTT Manager Instanz erstellen
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
                
                # Callbacks neu setzen
                self.mqtt_manager.set_data_callback(self.handle_sensor_data)
                self.mqtt_manager.set_config_callback(self.handle_sensor_config)
                self.mqtt_manager.set_base_station_callback(self.handle_base_station_data)
                
                # Neue Verbindung aufbauen
                self.mqtt_manager.connect()
                
                logging.info("✅ MQTT Settings erfolgreich aktualisiert!")
            else:
                logging.info("✅ Settings aktualisiert (keine MQTT Änderungen)")
                
        except Exception as e:
            logging.error(f"❌ Fehler beim Neuladen der Settings: {e}")
    
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