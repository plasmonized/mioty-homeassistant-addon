#!/usr/bin/env python3
"""
Demo-Version des mioty Application Center Add-ons
Für Demonstration auf Replit (ohne bashio)
"""

import os
import sys
import logging
import secrets

# Add mioty-application-center app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mioty-application-center', 'app'))

# 🔐 REPLIT DEV SECURITY: Ephemeral master key für demo/development
if not os.getenv('MIOTY_MASTER_KEY') and not os.access('/data', os.W_OK):
    ephemeral_key = secrets.token_urlsafe(64)
    os.environ['MIOTY_MASTER_KEY'] = ephemeral_key
    print(f"⚠️  DEV MODE: Using ephemeral master key (not persistent across restarts)")
    print(f"✅ Production: Requires /data directory or MIOTY_MASTER_KEY environment variable")

# Set demo environment variables
# Update these with your real MQTT broker credentials
os.environ.update({
    'MQTT_BROKER': 'your-mqtt-broker.com',  
    'MQTT_PORT': '1883',
    'MQTT_USERNAME': 'your-username',
    'MQTT_PASSWORD': 'your-password',
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