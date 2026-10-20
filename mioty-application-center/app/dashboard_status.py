"""Read-only operational dashboard snapshot, without connection credentials."""

import math
import time

from sentinum_cloud import cloud_settings


RADIOS = {
    "mioty": "mioty", "lora": "LoRaWAN", "cellular": "Mobilfunk",
    "oms": "OMS / Wireless M-Bus", "unknown": "Andere",
}
BASESTATION_WINDOW_SECONDS = 300


def _radio(record):
    value = str(record.get("type") or record.get("protocol_type") or "mioty").lower()
    aliases = {"lorawan": "lora", "wmbus": "oms", "mobilfunk": "cellular"}
    value = aliases.get(value, value)
    return value if value in RADIOS else "unknown"


def _recent(record, now, window):
    try:
        last_seen = float(record.get("last_seen", 0))
    except (ValueError, TypeError):
        return False
    return math.isfinite(last_seen) and last_seen > 0 and 0 <= now - last_seen <= window


def _offline(record):
    """Support both string statuses and the existing MQTT status object."""
    status = record.get("status")
    if isinstance(status, dict):
        if status.get("online") is False or status.get("connected") is False:
            return True
        status = status.get("status")
    return status is False or str(status).lower() in ("offline", "inactive", "disconnected")


def dashboard_snapshot(addon, now=None):
    now = time.time() if now is None else now
    sensor_window = getattr(addon, "warning_threshold", 3600)
    if not isinstance(sensor_window, (int, float)) or not math.isfinite(sensor_window) or sensor_window <= 0:
        sensor_window = 3600
    sensors = addon.get_sensor_list()
    basestations = addon.get_basestation_list()
    config = getattr(addon, "config", {})
    cloud_config = cloud_settings(config)
    groups = {
        key: {"key": key, "label": label, "sensors": {"active": 0, "total": 0},
              "basestations": {"active": 0, "total": 0} if key in ("mioty", "lora") else None}
        for key, label in RADIOS.items()
    }
    for record in sensors.values():
        radio = _radio(record)
        counts = groups[radio]["sensors"]
        counts["total"] += 1
        if _recent(record, now, sensor_window) and not _offline(record):
            counts["active"] += 1
    for record in basestations.values():
        radio = _radio(record)
        if radio not in ("mioty", "lora"):
            continue
        counts = groups[radio]["basestations"]
        counts["total"] += 1
        if _recent(record, now, BASESTATION_WINDOW_SECONDS) and not _offline(record):
            counts["active"] += 1
    technologies = [
        group for key, group in groups.items()
        if (
            key in ("mioty", "lora") or group["sensors"]["total"]
            or (key == "cellular" and cloud_config["enabled"])
        )
    ]

    mqtt = getattr(addon, "mqtt_manager", None)
    mqtt_enabled = bool(config.get("mqtt_broker"))
    ha_enabled = bool(config.get("ha_mqtt_broker"))
    mqtt_connected = bool(mqtt and mqtt.connected)
    ha_connected = bool(mqtt and mqtt.ha_connected)
    scaci_enabled = bool(config.get("scaci_enabled"))
    scaci = getattr(addon, "scaci_client", None)
    scaci_connected = bool(scaci and scaci.get_connection_info().get("connected"))

    def connection_state(enabled, connected):
        return "connected" if connected else "disconnected" if enabled else "disabled"

    service_detail = []
    if scaci_enabled or scaci_connected:
        service_detail.append("SCACI: " + ("verbunden" if scaci_connected else "getrennt"))
    if mqtt_enabled or mqtt_connected:
        service_detail.append("MQTT: " + ("verbunden" if mqtt_connected else "getrennt"))
    connections = [
        {"id": "service_center", "label": "Service Center",
         "state": connection_state(scaci_enabled or mqtt_enabled, scaci_connected or mqtt_connected),
         "detail": " · ".join(service_detail) or "Keine Verbindung konfiguriert"},
        {"id": "mioty_mqtt", "label": "mioty-MQTT",
         "state": connection_state(mqtt_enabled, mqtt_connected), "detail": "BSSCI-Sensordaten empfangen"},
        {"id": "homeassistant_mqtt", "label": "Home Assistant MQTT",
         "state": connection_state(ha_enabled, ha_connected), "detail": "Messwerte an Home Assistant weitergeben"},
    ]
    cloud = getattr(addon, "sentinum_cloud", None)
    cloud_status = cloud.status() if cloud else {}
    if not cloud_config["enabled"]:
        cloud_state, cloud_detail = "disabled", "Cloud-Empfang ausgeschaltet"
    else:
        cloud_state = cloud_status.get("state", "unknown")
        if cloud_state == "disabled":
            cloud_state = "unknown"
        if cloud_state not in ("connected", "connecting", "disconnected", "error"):
            cloud_state = "unknown"
        if cloud_status.get("error"):
            cloud_state = "error"
        cloud_detail = "Telemetrie-Abonnement aktiv" if cloud_state == "connected" else "Details unter Einstellungen → Sentinum Cloud"
    connections.append({"id": "sentinum_cloud", "label": "Sentinum Cloud",
                        "state": cloud_state, "detail": cloud_detail})
    return {
        "generated_at": now,
        "sensor_activity_window_seconds": sensor_window,
        "basestation_activity_window_seconds": BASESTATION_WINDOW_SECONDS,
        "sensors": {
            key: sum(group["sensors"][key] for group in technologies)
            for key in ("active", "total")
        },
        "technologies": technologies,
        "connections": connections,
    }
