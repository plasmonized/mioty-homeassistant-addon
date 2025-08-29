"""Constants for the BSSCI mioty integration."""

DOMAIN = "bssci_mioty"

# Configuration keys
CONF_MQTT_BROKER = "mqtt_broker"
CONF_MQTT_PORT = "mqtt_port"
CONF_MQTT_USERNAME = "mqtt_username"
CONF_MQTT_PASSWORD = "mqtt_password"
CONF_BASE_TOPIC = "base_topic"

# Default values
DEFAULT_MQTT_PORT = 1883
DEFAULT_BASE_TOPIC = "bssci"

# MQTT Topics
TOPIC_SENSOR_DATA = "ep/+/ul"
TOPIC_BASE_STATION = "bs/+"
TOPIC_SENSOR_CONFIG = "ep/{}/config"

# Services
SERVICE_ADD_SENSOR = "add_sensor"
SERVICE_REMOVE_SENSOR = "remove_sensor"
SERVICE_CONFIGURE_SENSOR = "configure_sensor"

# Attributes
ATTR_SENSOR_EUI = "sensor_eui"
ATTR_NETWORK_KEY = "network_key"
ATTR_SHORT_ADDR = "short_addr"
ATTR_BIDIRECTIONAL = "bidirectional"
ATTR_BS_EUI = "bs_eui"
ATTR_SNR = "snr"
ATTR_RSSI = "rssi"
ATTR_CNT = "cnt"
ATTR_RX_TIME = "rx_time"

# Device classes
DEVICE_CLASS_MIOTY_SENSOR = "mioty_sensor"
DEVICE_CLASS_MIOTY_BASE_STATION = "mioty_base_station"
