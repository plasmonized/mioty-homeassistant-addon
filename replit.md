# Overview

The BSSCI mioty Home Assistant Integration bridges mioty IoT sensors with Home Assistant via MQTT, implementing the BSSCI protocol v1.0.0.0. Its purpose is to enable real-time sensor data collection, base station monitoring, and device management within the Home Assistant ecosystem. Key capabilities include automatic sensor discovery, bidirectional communication, and a German-localized user interface, aiming for seamless integration of mioty IoT networks into smart home environments.

**Version: 1.0.5.7.2** - NEW FEATURE: Integrated IoddProcessParser for automated IODD interpretation. Added IO-Link Adapter management with IODD assignment per adapter. New Decoder page with 3 sections: Decoder, IO-Link Adapter, IODD Management.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Add-on Architecture
- **Docker Containerization**: Implemented as a Home Assistant Add-on with Docker.
- **Flask Web Application**: Modern web-based GUI with an orange/gray color scheme for all management tasks.
- **Multi-Tab Interface**: Features separate sections for Sensor Management, Decoder Management, and Settings.
- **Persistent Configuration**: Settings are managed with file-based storage and support runtime reconfiguration.

## Payload Decoder System
- **Multi-Format Support**: Handles mioty Blueprint (.json) and Sentinum JavaScript (.js) decoder formats.
- **Dynamic Decoder Engine**: Runtime loading and execution of decoder scripts with fallback mechanisms.
- **Sensor Assignment Management**: Supports individual decoder assignment per sensor EUI with persistent storage.
- **Testing Framework**: Includes built-in decoder testing with hex payload input and JSON result visualization.
- **Upload Management**: Provides web-based file upload with validation and error handling.

## MQTT Communication Layer
- **Protocol Bridge**: Acts as an intermediary between the BSSCI protocol (TLS-secured base station communication) and MQTT messaging.
- **Topic Structure**: Utilizes hierarchical MQTT topics (`ep/+/ul` for sensor data, `bs/+` for base stations, `ep/{}/config` for configuration).
- **Real-time Processing**: Handles live sensor data streams with deduplication and timestamp management.
- **Bidirectional Support**: Enables both uplink data collection and downlink command transmission.

## Entity Management System
- **Dynamic Entity Creation**: Automatically creates Home Assistant entities upon receiving new MQTT messages from unknown sensors.
- **Device Registry Integration**: Registers devices with Home Assistant's device registry for organized management.
- **State Synchronization**: Maintains sensor states and attributes (SNR, RSSI, timestamps) through MQTT message processing.

## Configuration Management
- **Config Flow Implementation**: Provides guided setup through Home Assistant's configuration interface.
- **MQTT Connection Testing**: Validates broker connectivity during initial setup.
- **Options Flow**: Allows runtime reconfiguration of MQTT settings.

## Data Processing Architecture
- **Sensor Data Handling**: Processes raw mioty sensor data, converting it into Home Assistant-compatible sensor readings.
- **Signal Quality Metrics**: Tracks and exposes signal quality indicators (SNR, RSSI) as entity attributes.
- **Base Station Monitoring**: Provides visibility into base station status, including CPU, memory, uptime, and duty cycle.

## Localization Framework
- **German Language Support**: Implements comprehensive German translations for all user-facing strings.
- **Multi-language Ready**: Structured to easily support additional languages.

## UI/UX Decisions
- **Color Scheme**: Consistent orange/gray design across the web interface.
- **Logo**: Custom mioty-themed logo integrated into the UI.
- **Branding**: Includes "Powered by Sentinum" footer and Sentinum logo.

# External Dependencies

## MQTT Infrastructure
- **MQTT Broker**: Requires an external MQTT broker for message routing.
- **paho-mqtt Library**: Python MQTT client library for MQTT communication.

## mioty Network Components
- **BSSCI Service Center**: External service center implementing BSSCI protocol v1.0.0.0.
- **mioty Base Stations**: Physical base stations communicating with IoT sensors.
- **mioty IoT Sensors**: End devices transmitting sensor data via the mioty network.

## Home Assistant Framework
- **Home Assistant Core**: Requires Home Assistant 2023.1.0+ for custom component APIs.
- **Entity Registry**: Utilized for dynamic entity management.
- **Device Registry**: Integrated for proper device representation.
- **Config Entry System**: Leveraged for persistent configuration storage.

## Development and Distribution
- **HACS Compatibility**: Configured for Home Assistant Community Store distribution.
- **Voluptuous Schema Validation**: Used for robust configuration and service parameter validation.