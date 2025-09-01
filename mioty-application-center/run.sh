#!/usr/bin/with-contenv bashio
# mioty Application Center Add-on Start Script

set -e

# Get configuration
CONFIG_PATH=/data/options.json

MQTT_BROKER=$(bashio::config 'mqtt_broker')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USERNAME=$(bashio::config 'mqtt_username')
MQTT_PASSWORD=$(bashio::config 'mqtt_password')
BASE_TOPIC=$(bashio::config 'base_topic')
AUTO_DISCOVERY=$(bashio::config 'auto_discovery')
LOG_LEVEL=$(bashio::config 'log_level')
WEB_PORT=$(bashio::config 'web_port')

# Export environment variables
export MQTT_BROKER="$MQTT_BROKER"
export MQTT_PORT="$MQTT_PORT"
export MQTT_USERNAME="$MQTT_USERNAME"
export MQTT_PASSWORD="$MQTT_PASSWORD"
export BASE_TOPIC="$BASE_TOPIC"
export AUTO_DISCOVERY="$AUTO_DISCOVERY"
export LOG_LEVEL="$LOG_LEVEL"
export WEB_PORT="$WEB_PORT"

bashio::log.info "Starte mioty Application Center..."
bashio::log.info "MQTT Broker: $MQTT_BROKER:$MQTT_PORT"
bashio::log.info "Base Topic: $BASE_TOPIC"

# Start the application
python3 main.py