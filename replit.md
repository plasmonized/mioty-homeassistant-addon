# Overview

The BSSCI mioty Home Assistant Integration is a custom integration that bridges mioty IoT sensors with Home Assistant through MQTT communication. It implements the Base Station Service Center Interface (BSSCI) protocol v1.0.0.0 to enable real-time sensor data collection, base station monitoring, and device management within Home Assistant's ecosystem.

The integration provides automatic sensor discovery, bidirectional communication capabilities, and a German-localized user interface for seamless integration of mioty IoT networks into smart home environments.

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes

**29.08.2025 - BSSCI mioty Home Assistant Integration abgeschlossen:**
- Vollständige Custom Integration für Home Assistant erstellt mit deutscher GUI
- MQTT-Verbindung zu bestehendem BSSCI Service Center implementiert  
- Automatische Sensor-Discovery und dynamische Entity-Management entwickelt
- Services für Sensor-Verwaltung (hinzufügen, konfigurieren, entfernen) über Home Assistant GUI
- Base Station Monitoring mit Echtzeit-Status (CPU, Memory, Uptime, Duty Cycle)
- Signal Quality Assessment und Device Registry Integration
- HACS-kompatible Struktur für einfache Installation und Updates
- Deutsche Lokalisierung aller Benutzeroberflächen-Strings

# System Architecture

## Core Integration Architecture
- **Custom Component Structure**: Follows Home Assistant's standard custom component pattern with separate modules for configuration flow, sensor entities, device tracking, and constants management
- **Platform Support**: Implements both sensor and device_tracker platforms for comprehensive device representation in Home Assistant
- **Service-Based Management**: Provides Home Assistant services for adding, removing, and configuring sensors dynamically through the UI

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