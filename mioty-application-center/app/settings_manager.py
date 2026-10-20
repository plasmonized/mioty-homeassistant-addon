"""
Settings Manager für BSSCI mioty Add-on
Verwaltet lokale Konfigurationseinstellungen
"""

import json
import logging
import os
import tempfile
import threading
from typing import Dict, Any, Optional


class SettingsManager:
    """Verwaltet Add-on Einstellungen."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialisiere Settings Manager."""
        if config_file is None:
            # Persistente Speicherung in /data für Home Assistant Add-on
            if os.path.exists('/data'):
                config_file = '/data/settings.json'
            else:
                config_file = 'settings.json'  # Fallback für Entwicklung
        self.config_file = config_file
        self.settings = {}
        self._lock = threading.RLock()
        self.load_settings()
    
    def load_settings(self):
        """Lade Einstellungen aus Datei."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.settings = json.load(f)
                logging.info("Einstellungen geladen")
            else:
                # Standard-Einstellungen
                self.settings = {
                    'mqtt_broker': 'core-mosquitto',
                    'mqtt_port': 1883,
                    'mqtt_username': '',
                    'mqtt_password': '',
                    'base_topic': 'bssci',
                    'auto_discovery': True,
                    'ha_mqtt_broker': 'core-mosquitto',
                    'ha_mqtt_port': 1883,
                    'ha_mqtt_username': '',
                    'ha_mqtt_password': '',
                    'show_lora': True,
                    'show_oms': True
                }
                self.save_settings()
                logging.info("Standard-Einstellungen erstellt")
        except Exception as e:
            logging.error(f"Fehler beim Laden der Einstellungen: {e}")
            # Fallback zu Standard-Einstellungen
            self.settings = {
                'mqtt_broker': 'core-mosquitto',
                'mqtt_port': 1883,
                'mqtt_username': '',
                'mqtt_password': '',
                'base_topic': 'bssci',
                'auto_discovery': True,
                'ha_mqtt_broker': 'core-mosquitto',
                'ha_mqtt_port': 1883,
                'ha_mqtt_username': '',
                'ha_mqtt_password': ''
            }
    
    def save_settings(self):
        """Speichere Einstellungen in Datei."""
        temporary_path = None
        try:
            # Verzeichnis erstellen falls es nicht existiert (nur wenn Verzeichnis vorhanden)
            if os.path.dirname(self.config_file):
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Credentials belong only to the add-on user. Atomic replacement
            # prevents a failed save from truncating all integration settings.
            with self._lock:
                directory = os.path.dirname(os.path.abspath(self.config_file))
                fd, temporary_path = tempfile.mkstemp(prefix='.settings-', suffix='.tmp', dir=directory)
                with os.fdopen(fd, 'w') as f:
                    json.dump(self.settings, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary_path, self.config_file)
            logging.info("Einstellungen gespeichert")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Einstellungen: {e}")
            return False
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
    
    def get_setting(self, key: str, default=None):
        """Hole einzelne Einstellung."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Setze einzelne Einstellung."""
        return self.update_settings({key: value})
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Aktualisiere mehrere Einstellungen."""
        with self._lock:
            previous = self.settings.copy()
            self.settings.update(new_settings)
            if self.save_settings():
                return True
            self.settings = previous
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Hole alle Einstellungen."""
        return self.settings.copy()
    
    def reset_to_defaults(self):
        """Setze auf Standard-Einstellungen zurück."""
        self.settings = {
            'mqtt_broker': 'core-mosquitto',
            'mqtt_port': 1883,
            'mqtt_username': '',
            'mqtt_password': '',
            'base_topic': 'bssci',
            'auto_discovery': True
        }
        return self.save_settings()