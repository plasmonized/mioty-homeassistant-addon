# mioty Application Center für Homeassistant

Ein vollständiges Home Assistant Add-on für die Verwaltung von mioty IoT Sensoren über das BSSCI (Base Station Service Center Interface) Protokoll.

## Features

- **Web-GUI**: Moderne Benutzeroberfläche mit orange/grauem Design
- **Automatisiertes Payload Decoder System**: 
  - Unterstützung für mioty Blueprint (.json) und Sentinum JavaScript (.js) Decoder
  - Upload-Funktionalität und Live-Testing
  - Sensor-Decoder Zuordnungsverwaltung
- **MQTT Integration**: Vollständige MQTT Broker Konfiguration
- **Deutsche Lokalisierung**: Komplett deutsche Benutzeroberfläche
- **Sensor Management**: Einfache Verwaltung von mioty Sensoren
- **Base Station Monitoring**: Überwachung von Basisstationen

## Installation

1. Fügen Sie dieses Repository zu Home Assistant hinzu
2. Installieren Sie das "mioty Application Center" Add-on  
3. Konfigurieren Sie Ihren MQTT Broker
4. Starten Sie das Add-on
5. Öffnen Sie die Web-GUI über "OPEN WEB UI"

## Konfiguration

Das Add-on kann über die Home Assistant Konfiguration oder direkt über die Web-GUI konfiguriert werden.

## Web-GUI

Die Web-GUI bietet drei Hauptbereiche:
- **Sensoren**: Sensor-Management und -Übersicht
- **Decoder**: Upload und Verwaltung von Payload-Decodern
- **Einstellungen**: MQTT und Systemkonfiguration