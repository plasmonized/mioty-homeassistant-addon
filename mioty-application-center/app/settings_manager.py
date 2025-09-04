"""
Settings Manager für BSSCI mioty Add-on
Verwaltet lokale Konfigurationseinstellungen
"""

import json
import logging
import os
from typing import Dict, Any


class SettingsManager:
    """Verwaltet Add-on Einstellungen."""
    
    def __init__(self, config_file: str = None):
        """Initialisiere Settings Manager."""
        if config_file is None:
            # Persistente Speicherung in /data für Home Assistant Add-on
            if os.path.exists('/data'):
                config_file = '/data/settings.json'
            else:
                config_file = 'settings.json'  # Fallback für Entwicklung
        self.config_file = config_file
        self.settings = {}
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
                    'ha_mqtt_password': ''
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
        try:
            # Verzeichnis erstellen falls es nicht existiert (nur wenn Verzeichnis vorhanden)
            if os.path.dirname(self.config_file):
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logging.info("Einstellungen gespeichert")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Einstellungen: {e}")
            return False
    
    def get_setting(self, key: str, default=None):
        """Hole einzelne Einstellung."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Setze einzelne Einstellung."""
        self.settings[key] = value
        return self.save_settings()
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Aktualisiere mehrere Einstellungen."""
        self.settings.update(new_settings)
        return self.save_settings()
    
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