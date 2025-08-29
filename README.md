# BSSCI mioty Integration für Home Assistant

Eine Home Assistant Custom Integration zur nahtlosen Integration Ihres bestehenden BSSCI Service Centers mit MQTT-basierter Sensor-Verwaltung.

## Überblick

Diese Integration ermöglicht es Ihnen, mioty IoT-Sensoren über das BSSCI (Base Station Service Center Interface) Protokoll in Home Assistant zu integrieren. Die Integration kommuniziert über MQTT mit Ihrem bestehenden BSSCI Service Center und bietet:

- **Automatische Sensor-Erkennung** basierend auf MQTT-Nachrichten
- **Einfache GUI** für Sensor-Management in Home Assistant
- **Echtzeit-Datenübertragung** von mioty Sensoren
- **Base Station Monitoring** für Netzwerk-Überwachung
- **Deutsche Lokalisierung** der Benutzeroberfläche

## Features

### 🚀 Hauptfunktionen
- MQTT-Verbindung zu Ihrem BSSCI Service Center
- Automatische Erstellung von Sensor-Entitäten
- Sensor-Konfiguration über Home Assistant Services
- Base Station Status-Monitoring
- Signal-Quality Attribute (SNR, RSSI)
- Bidirektionale Sensor-Kommunikation

### 📊 Überwachte Daten
- Sensor-Daten mit Timestamp und Signal-Qualität
- Base Station CPU/Memory/Uptime
- Nachrichten-Zähler und Duty Cycle
- Verbindungsstatus und Fehlerbehandlung

### 🔧 Management-Features
- Sensor hinzufügen/entfernen über GUI
- Netzwerk-Schlüssel und Adressen konfigurieren
- Bidirektionale Kommunikation aktivieren
- Automatisches Device Discovery

## Installation

### Über HACS (empfohlen)

1. Öffnen Sie HACS in Home Assistant
2. Gehen Sie zu "Integrationen"
3. Klicken Sie auf das Menü (⋮) und wählen Sie "Custom Repositories"
4. Fügen Sie diese Repository-URL hinzu: `https://github.com/ihr-repo/bssci-mioty-ha`
5. Wählen Sie "Integration" als Kategorie
6. Klicken Sie auf "Hinzufügen"
7. Suchen Sie nach "BSSCI mioty" und installieren Sie es
8. Starten Sie Home Assistant neu

### Manuelle Installation

1. Laden Sie die neueste Version von den [Releases](https://github.com/ihr-repo/bssci-mioty-ha/releases) herunter
2. Extrahieren Sie das Archiv in das `custom_components` Verzeichnis Ihrer Home Assistant Installation
3. Starten Sie Home Assistant neu

## Konfiguration

### 1. Integration hinzufügen

1. Gehen Sie zu "Einstellungen" → "Geräte & Dienste"
2. Klicken Sie auf "Integration hinzufügen"
3. Suchen Sie nach "BSSCI mioty"
4. Folgen Sie dem Konfigurationsassistenten

### 2. MQTT-Einstellungen

Konfigurieren Sie die Verbindung zu Ihrem BSSCI Service Center:

- **MQTT Broker**: IP-Adresse Ihres MQTT-Brokers
- **Port**: Standard ist 1883 (oder 8883 für TLS)
- **Benutzername/Passwort**: Ihre MQTT-Zugangsdaten
- **Basis-Topic**: Standard ist "bssci"

## Verwendung

### Sensoren verwalten

#### Neuen Sensor hinzufügen

Verwenden Sie den Service `bssci_mioty.add_sensor`:

```yaml
service: bssci_mioty.add_sensor
data:
  sensor_eui: "fca84a0300001234"
  network_key: "0011223344556677889AABBCCDDEEFF00"
  short_addr: "1234"
  bidirectional: false
