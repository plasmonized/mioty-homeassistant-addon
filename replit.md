# Overview

The BSSCI mioty Home Assistant Integration is a custom integration that bridges mioty IoT sensors with Home Assistant through MQTT communication. It implements the Base Station Service Center Interface (BSSCI) protocol v1.0.0.0 to enable real-time sensor data collection, base station monitoring, and device management within Home Assistant's ecosystem.

The integration provides automatic sensor discovery, bidirectional communication capabilities, and a German-localized user interface for seamless integration of mioty IoT networks into smart home environments.

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes

**03.09.2025 - Replit iframe Cache-Busting & HA MQTT Integration (Version 1.0.4.6):**
- **REPLIT IFRAME CACHE-BUSTING:** Aggressive Cache-Busting mit Timestamps für iframe-Umgebung implementiert
- **HOME ASSISTANT MQTT INTEGRATION:** Vollständige HA MQTT Verbindung konfiguriert (Base Station Discovery funktioniert)
- **JAVASCRIPT CACHE-OVERRIDE:** Automatisches Cache-Busting für alle API-Calls in iframe-Umgebungen
- **HTTP HEADERS ERWEITERT:** X-Frame-Options, Vary, ETag Headers für bessere Cache-Kontrolle
- **EXTERNE ABHÄNGIGKEIT DOKUMENTIERT:** containerized-mioty-Service-Center Referenz in README hinzugefügt

**02.09.2025 - Browser-Cache Problem behoben (Version 1.0.4.5):**
- **KRITISCHES CACHE-PROBLEM BEHOBEN:** Anti-Cache Headers implementiert (Cache-Control: no-cache, no-store, must-revalidate)
- Browser-Cache-Problem gelöst, das altes Dashboard nach Add-on Updates anzeigte
- Automatische Cache-Verhinderung für alle GUI-Seiten (/, /settings, /decoders)
- Pragma und Expires Headers für vollständige Browser-Kompatibilität
- Cache-Control Logging für besseres Debugging hinzugefügt

**02.09.2025 - Erweiterte HTTP-Debugging Implementierung (Version 1.0.4.4):**
- Vollständige HTTP-Request-Protokollierung mit allen Headers und Parametern
- Home Assistant Ingress-Erkennung und automatische Umgebungsdetektion
- Detaillierte Response-Debugging mit Status-Codes und Headers
- Spezielle Ingress-Debugging für alle Hauptseiten (Index, Settings, Decoders)
- HTTP-Fehler-Handler mit umfassendem Logging für Troubleshooting
- Warnsystem für externe/Development-Umgebung vs. Home Assistant Ingress

**01.09.2025 - Konfiguration bereinigt:**
- Unnötige bssci_service_url Konfiguration entfernt (wird nicht verwendet - alles läuft über MQTT)
- Dokumentation in README-Dateien aktualisiert 
- Add-on-Konfiguration vereinfacht (config.yaml, run.sh bereinigt)

**30.08.2025 - Konfiguration und Logo Updates:**
- Fixed configuration dashboard to display actual runtime MQTT settings instead of defaults
- Added live connection status API endpoint (/api/status) with auto-refresh
- Resolved Home Assistant ingress compatibility with proper BASE_URL handling
- **Added custom mioty-themed logo** - Professional IoT logo with orange/gray design showing radio waves, sensor networks, and MQTT connectivity

**29.08.2025 - mioty Application Center für Homeassistant mit Payload Decoder System abgeschlossen:**
- Vollständige Custom Integration zu Home Assistant Add-on konvertiert
- Docker-containerisierte Lösung mit Flask Web-GUI im orange/grauen Design
- MQTT Broker Konfiguration direkt über Web-Interface mit Credentials-Support
- **Automatisiertes Payload Decoder System implementiert:**
  - Unterstützung für mioty Blueprint Decoder (.json Format)
  - Unterstützung für Sentinum JavaScript Decoder (.js Format)  
  - Upload-Funktionalität für Decoder-Dateien über Web-GUI
  - Sensor-Decoder Zuordnungsverwaltung
  - Live-Testing von Decodern mit Test-Payloads
  - Automatische Payload-Dekodierung im MQTT Flow integriert
  - Beispiel-Decoder für Demo-Zwecke vorinstalliert
- Komplette Umbenennung zu "mioty Application Center für Homeassistant"
- Web-GUI erweitert mit Decoder-Management Tab und vollständiger CRUD-Funktionalität

# System Architecture

## Add-on Architecture
- **Docker Containerization**: Complete Home Assistant Add-on with Dockerfile and configuration files
- **Flask Web Application**: Modern web-based GUI with orange/gray color scheme for all management tasks
- **Multi-Tab Interface**: Separate sections for Sensor Management, Decoder Management, and Settings
- **Persistent Configuration**: Settings management with file-based storage and runtime reconfiguration

## Payload Decoder System  
- **Multi-Format Support**: Handles both mioty Blueprint (.json) and Sentinum JavaScript (.js) decoder formats
- **Dynamic Decoder Engine**: Runtime loading and execution of decoder scripts with fallback mechanisms
- **Sensor Assignment Management**: Individual decoder assignment per sensor EUI with persistent storage
- **Testing Framework**: Built-in decoder testing with hex payload input and JSON result visualization
- **Upload Management**: Web-based file upload with validation and error handling

## MQTT Communication Layer
- **Protocol Bridge**: Acts as an intermediary between BSSCI protocol (TLS-secured base station communication) and MQTT messaging
- **Topic Structure**: Uses hierarchical MQTT topics (`ep/+/ul` for sensor data, `bs/+` for base stations, `ep/{}/config` for configuration)
- **Real-time Processing**: Handles live sensor data streams with deduplication and timestamp management
- **Bidirectional Support**: Enables both uplink data collection and downlink command transmission

## Entity Management System
- **Dynamic Entity Creation**: Automatically creates Home Assistant entities when new MQTT messages arrive from previously unknown sensors
- **Device Registry Integration**: Properly registers devices with Home Assistant's device registry for organized management
- **State Synchronization**: Maintains sensor states and attributes (SNR, RSSI, timestamps) through MQTT message processing

## Configuration Management
- **Config Flow Implementation**: Provides guided setup through Home Assistant's configuration interface
- **MQTT Connection Testing**: Validates broker connectivity during initial setup
- **Options Flow**: Allows runtime reconfiguration of MQTT settings without reinstalling the integration

## Data Processing Architecture
- **Sensor Data Handling**: Processes raw mioty sensor data and converts it into Home Assistant-compatible sensor readings
- **Signal Quality Metrics**: Tracks and exposes signal quality indicators (SNR, RSSI) as entity attributes
- **Base Station Monitoring**: Provides visibility into base station status, including CPU, memory, uptime, and duty cycle information

## Localization Framework
- **German Language Support**: Implements comprehensive German translations for all user-facing strings
- **Multi-language Ready**: Structured to easily support additional languages through the translations system

# External Dependencies

## MQTT Infrastructure
- **MQTT Broker**: Requires external MQTT broker for message routing between the BSSCI service center and Home Assistant
- **paho-mqtt Library**: Python MQTT client library (v1.6.0+) for handling MQTT communication protocols

## mioty Network Components
- **BSSCI Service Center**: External service center implementing BSSCI protocol v1.0.0.0 for base station communication
- **mioty Base Stations**: Physical base stations that communicate with IoT sensors and relay data to the service center
- **mioty IoT Sensors**: End devices that transmit sensor data through the mioty network protocol

## Home Assistant Framework
- **Home Assistant Core**: Requires Home Assistant 2023.1.0+ for modern custom component APIs
- **Entity Registry**: Utilizes Home Assistant's entity registry for dynamic entity management
- **Device Registry**: Integrates with device registry for proper device representation and organization
- **Config Entry System**: Leverages Home Assistant's configuration entry system for persistent configuration storage

## Development and Distribution
- **HACS Compatibility**: Configured for Home Assistant Community Store distribution with proper metadata
- **Voluptuous Schema Validation**: Uses voluptuous for robust configuration and service parameter validation