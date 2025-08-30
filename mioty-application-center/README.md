# BSSCI mioty Home Assistant Add-on

Ein vollständiges Home Assistant Add-on für die Verwaltung von mioty IoT Sensoren über das BSSCI (Base Station Service Center Interface) Protokoll.

## 🚀 Features

- **MQTT Integration**: Nahtlose Verbindung zu Ihrem BSSCI Service Center
- **Automatische Discovery**: Sensoren werden automatisch in Home Assistant erkannt
- **Web-GUI**: Einfache Sensor-Verwaltung über moderne Weboberfläche
- **Deutsche Lokalisierung**: Vollständig deutsche Benutzeroberfläche
- **Base Station Monitoring**: Überwachung von CPU, Memory und Uptime
- **Signal Quality Assessment**: SNR/RSSI Bewertung der Verbindungsqualität

## 📦 Installation

### Über Add-on Store

1. Fügen Sie dieses Repository zu Ihrem Home Assistant hinzu:
   - Gehen Sie zu **Supervisor** → **Add-on Store** → **⋮** → **Repositories**
   - Fügen Sie die URL hinzu: `https://github.com/your-repo/bssci-mioty-addon`

2. Installieren Sie das "BSSCI mioty Sensor Manager" Add-on

3. Konfigurieren Sie das Add-on (siehe Konfiguration unten)

4. Starten Sie das Add-on

### Manuelle Installation

1. Kopieren Sie diesen Ordner nach `/addons/bssci_mioty/` in Ihrem Home Assistant
2. Gehen Sie zu **Supervisor** → **Add-on Store** → **⋮** → **Repositories aktualisieren**
3. Das Add-on sollte nun unter "Lokale Add-ons" erscheinen

## ⚙️ Konfiguration

```yaml
mqtt_broker: "core-mosquitto"      # MQTT Broker (meist core-mosquitto)
mqtt_port: 1883                   # MQTT Port
mqtt_username: ""                 # MQTT Benutzername (optional)
mqtt_password: ""                 # MQTT Passwort (optional)
bssci_service_url: "localhost:16018"  # Ihr BSSCI Service Center
base_topic: "bssci"               # MQTT Basis-Topic
auto_discovery: true              # Home Assistant Auto-Discovery
log_level: "info"                 # Log-Level (debug/info/warning/error)
```

## 🔧 Verwendung

### 1. Add-on starten

Nach der Konfiguration starten Sie das Add-on. Es verbindet sich automatisch mit:
- Ihrem MQTT Broker
- Ihrem BSSCI Service Center
- Home Assistant's Discovery System

### 2. Web-GUI verwenden

- Klicken Sie auf "OPEN WEB UI" im Add-on
- Oder besuchen Sie `http://homeassistant:8080`

### 3. Sensoren hinzufügen

In der Web-GUI können Sie neue Sensoren registrieren:

1. **Sensor EUI**: 16-stellige Hex-Kennung (z.B. `fca84a0300001234`)
2. **Netzwerk-Schlüssel**: 32-stelliger Hex-Schlüssel für Authentifizierung  
3. **Kurze Adresse**: 4-stellige Hex-Adresse für Kommunikation
4. **Bidirektional**: Aktiviert Downlink-Nachrichten (optional)

### 4. Automatische Erkennung

Sobald Sensoren Daten senden, werden sie automatisch in Home Assistant erstellt:
- `sensor.bssci_sensor_[eui]` - Sensor-Daten Entity
- Vollständige Attribute mit SNR, RSSI, Signalqualität
- Device Registry Integration

## 📊 MQTT Topics

Das Add-on verwendet folgende MQTT Topic-Struktur:

```
bssci/ep/[sensor_eui]/ul       # Eingehende Sensor-Daten
bssci/ep/[sensor_eui]/config   # Sensor-Konfiguration  
bssci/bs/[basestation_eui]     # Base Station Status
```

## 🏠 Home Assistant Integration

### Automatisch erstellte Entities:

- **Sensor Entities**: `sensor.bssci_sensor_[eui]`
  - State: Anzahl empfangener Bytes
  - Attribute: SNR, RSSI, Timestamp, Base Station, etc.

- **Base Station Entities**: `sensor.bssci_basestation_[eui]`
  - State: online/offline
  - Attribute: CPU, Memory, Uptime, Duty Cycle

### Device Registry:
Alle Sensoren werden sauber im Home Assistant Device Registry organisiert.

## 📝 Logging

Das Add-on schreibt ausführliche Logs. Log-Level können angepasst werden:

- `debug`: Sehr detaillierte Informationen
- `info`: Normale Betriebsmeldungen (Standard)
- `warning`: Nur Warnungen und Fehler
- `error`: Nur Fehler

## 🔍 Troubleshooting

### MQTT Verbindung

```bash
# Add-on Logs überprüfen
ha addons logs bssci_mioty

# MQTT Broker Status
ha addons logs core_mosquitto
```

### BSSCI Service Center

- Überprüfen Sie die `bssci_service_url` in der Konfiguration
- Stellen Sie sicher, dass das Service Center läuft
- Prüfen Sie Firewall-Regeln für Port 16018

### Home Assistant Discovery

- `auto_discovery: true` muss aktiviert sein
- MQTT Integration muss in Home Assistant konfiguriert sein
- Überprüfen Sie die MQTT Discovery Topics

## 🤝 Support

Bei Problemen:

1. Überprüfen Sie die Add-on Logs
2. Validieren Sie die MQTT/BSSCI Konfiguration
3. Erstellen Sie ein Issue im Repository mit:
   - Add-on Logs
   - Konfiguration (ohne Passwörter)
   - Home Assistant Version
   - Fehlerbeschreibung

## 📄 Lizenz

MIT License - siehe LICENSE Datei für Details.