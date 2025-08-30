#!/usr/bin/env python3
"""
Demo-Version des mioty Application Center Add-ons
Für Demonstration auf Replit (ohne bashio)
"""

import os
import sys
import logging

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set demo environment variables
# Update these with your real MQTT broker credentials
os.environ.update({
    'MQTT_BROKER': os.getenv('MQTT_BROKER_HOST', 'localhost'),  
    'MQTT_PORT': os.getenv('MQTT_BROKER_PORT', '1883'),
    'MQTT_USERNAME': os.getenv('MQTT_USERNAME', ''),
    'MQTT_PASSWORD': os.getenv('MQTT_PASSWORD', ''),
    'BSSCI_SERVICE_URL': os.getenv('BSSCI_SERVICE_URL', 'localhost:16018'),
    'BASE_TOPIC': 'bssci',
    'AUTO_DISCOVERY': 'true',
    'LOG_LEVEL': 'info',
    'WEB_PORT': '5000'
})

# Import and start the main application
try:
    from main import BSSCIAddon
    
    print("🚀 mioty Application Center Demo")
    print("=" * 50)
    print("Starte mioty Application Center für Homeassistant...")
    print("Web-GUI wird auf Port 5000 gestartet")
    print("=" * 50)
    
    addon = BSSCIAddon()
    addon.start()
    
except KeyboardInterrupt:
    print("\nDemo beendet durch Benutzer")
except Exception as e:
    print(f"Fehler beim Starten des Add-ons: {e}")
    logging.exception("Detailed error:")
    sys.exit(1)