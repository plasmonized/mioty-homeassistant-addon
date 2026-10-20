"""Read-only Sentinum Datahub MQTT integration for cellular sensors.

Supports Datahub 2.0 and the legacy devices/.../up telemetry mirror.
Never subscribes to shadow/control topics or publishes to the cloud.
"""

import base64
import binascii
import json
import logging
import math
import re
import threading
import time
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


DEFAULTS = {
    "enabled": False,
    "broker": "broker.sentinum.de",
    "port": 8883,
    "username": "",
    "password": "",
    "topic": "",
}
PREFIX = "sentinum_cloud_"


def cloud_settings(settings):
    result = {key: settings.get(PREFIX + key, default) for key, default in DEFAULTS.items()}
    # Sentinum uses one fixed public TLS endpoint, not a user-selected broker.
    result.update(broker=DEFAULTS["broker"], port=DEFAULTS["port"])
    return result


def telemetry_topic(topic):
    """Expand customer prefixes and trailing # to the read-only telemetry filter."""
    if not topic:
        return ""
    if "\0" in topic or len(topic.encode("utf-8")) > 65535:
        raise ValueError("Ungültiges MQTT-Topic.")
    parts = topic.split("/")
    if parts[-1] == "#":
        parts.pop()
    if (not 2 <= len(parts) <= 6 or parts[0] not in ("devices", "datahub")
            or parts[1] in ("", "+", "#")
            or any(not part or "#" in part or ("+" in part and part != "+") for part in parts)):
        raise ValueError("Topic muss zu einem festen Kunden gehören, z. B. devices/<Kunde>/# oder datahub/<Kunde>/+/+/+/up.")
    if len(parts) < 6:
        parts += ["+"] * (5 - len(parts)) + ["up"]
    if parts[-1] != "up":
        raise ValueError("Nur Sensordaten-Topics mit /up werden unterstützt, keine Steuer- oder Konfigurations-Topics.")
    return "/".join(parts)


def validate_settings(data, current):
    """Validate before persistence. The password sentinel means 'unchanged'."""
    if not isinstance(data, dict) or set(data) - set(DEFAULTS):
        raise ValueError("Ungültige Sentinum-Cloud-Einstellungen.")
    result = {**current, **data}
    if not isinstance(result["enabled"], bool):
        raise ValueError("Aktiviert muss ein Wahrheitswert sein.")
    for key in ("broker", "username", "password", "topic"):
        if not isinstance(result[key], str):
            raise ValueError(f"{key} muss Text sein.")
    for key in ("broker", "username", "topic"):
        result[key] = result[key].strip()
    if result["password"] == "***":
        result["password"] = current["password"]
    try:
        if isinstance(result["port"], bool):
            raise ValueError()
        result["port"] = int(str(result["port"]))
        if not 1 <= result["port"] <= 65535:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Port muss zwischen 1 und 65535 liegen.") from None
    if result["broker"] and not re.fullmatch(r"[A-Za-z0-9._:-]+", result["broker"]):
        raise ValueError("Broker als Hostname ohne mqtts:// oder Pfad eingeben.")
    if result["broker"] != DEFAULTS["broker"] or result["port"] != DEFAULTS["port"]:
        raise ValueError("Sentinum Cloud verwendet fest broker.sentinum.de mit TLS-Port 8883.")
    topic = result["topic"]
    if topic:
        result["topic"] = telemetry_topic(topic)
    elif result["enabled"] and any(c in result["username"] for c in "/+#\0"):
        raise ValueError("Für diesen Benutzernamen bitte ein explizites Kunden-Topic eingeben.")
    if result["enabled"] and not all(result[k] for k in ("broker", "username", "password")):
        raise ValueError("Broker, Benutzername und Passwort sind zum Aktivieren erforderlich.")
    return result


def _timestamp_ns(value):
    if value is None:
        return time.time_ns()
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp() * 1e9)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Ungültiger Zeitstempel.")
    scale = 1 if value >= 1e17 else 1e3 if value >= 1e14 else 1e6 if value >= 1e11 else 1e9
    return int(value * scale)


def _payload_bytes(value, encoding):
    if isinstance(value, list):
        if not value or any(type(b) is not int or not 0 <= b <= 255 for b in value):
            raise ValueError("Ungültiges Payload-Bytearray.")
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Payload fehlt oder hat ein unbekanntes Format.")
    if encoding.lower() in ("base64", "b64"):
        try:
            return list(base64.b64decode(value, validate=True))
        except (ValueError, binascii.Error):
            raise ValueError("Ungültiger Base64-Payload.") from None
    if encoding.lower() not in ("hex", "hexadecimal"):
        raise ValueError("Unbekannte Payload-Kodierung.")
    try:
        return list(bytes.fromhex(value.removeprefix("0x")))
    except ValueError:
        raise ValueError("Ungültiger Hex-Payload; Base64 benötigt eine Kodierungsangabe.") from None


def normalize_message(topic, body):
    """Return (stable device identity, pipeline data); reject non-cellular traffic."""
    parts = topic.split("/")
    if len(parts) != 6 or parts[0] not in ("devices", "datahub") or parts[-1] != "up":
        raise ValueError("Kein Sentinum-Telemetrie-Topic.")
    product, device_id = parts[2].lower(), parts[4]
    if not re.fullmatch(r"[a-zA-Z0-9-]+_cellular_[a-zA-Z0-9-]+", device_id, re.I):
        # The same cloud account can contain LoRa/mioty devices. Leave those
        # to their existing transports instead of importing them twice.
        return None
    if not isinstance(body, dict):
        raise ValueError("Cloud-Nachricht muss ein JSON-Objekt sein.")
    reported_id = body.get("deviceId", body.get("device_id", device_id))
    if str(reported_id).lower() != device_id.lower():
        raise ValueError("Geräte-ID stimmt nicht mit dem Topic überein.")
    identity = device_id.rsplit("_", 1)[-1].upper()  # Cellular IMEI, not a synthetic EUI
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    data = {
        "type": "cellular",
        "source": "sentinum_cloud",
        "cloud_device_id": device_id,
        "cloud_product": product,
        "timestamp_ns": _timestamp_ns(body.get("timestamp", body.get("time", metadata.get("timestamp")))),
        "rssi": body.get("rssi", metadata.get("rssi")),
        "snr": body.get("snr", metadata.get("snr")),
    }
    for metric in ("rssi", "snr"):
        value = data[metric]
        data[metric] = float(value) if value is not None else None
        if value is not None and not math.isfinite(data[metric]):
            raise ValueError("Ungültiger Signalwert.")
    encoding = body.get("payloadEncoding", body.get("encoding", "hex"))
    raw = None
    for key in ("payload_hex", "payloadHex", "rawPayload", "payload", "data", "frm_payload"):
        if key in body and body[key] is not None:
            candidate = body[key]
            if isinstance(candidate, dict):
                if "raw" in candidate or "hex" in candidate:
                    encoding = candidate.get("encoding", encoding)
                    raw = candidate.get("raw", candidate.get("hex"))
                    break
                continue
            raw = candidate
            if key == "frm_payload":
                encoding = "base64"
            break
    if raw is not None:
        if not isinstance(encoding, str):
            raise ValueError("Ungültige Payload-Kodierung.")
        data["data"] = _payload_bytes(raw, encoding)
        if not data["data"]:
            raise ValueError("Leerer Payload.")
    else:
        # Datahub may already provide decoded measurements instead of raw bytes.
        values = body.get("measurements", body.get("decoded", body.get("data")))
        if not isinstance(values, dict) or not values:
            raise ValueError("Keine Rohdaten oder dekodierten Messwerte in der Cloud-Nachricht.")
        normalized = {}
        for key, value in values.items():
            if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", key):
                raise ValueError("Ungültiger Messwertname.")
            if isinstance(value, dict) and "value" in value:
                unit, value = value.get("unit", ""), value["value"]
            else:
                unit = ""
            if isinstance(value, (str, int, float, bool)) and value is not None:
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("Ungültiger Messwert.")
                normalized[key] = {"value": value, "unit": str(unit)}
        if not normalized:
            raise ValueError("Keine unterstützten Cloud-Messwerte.")
        data["cloud_decoded"] = {
            "decoded": True, "decoder_name": "Sentinum Cloud", "data": normalized,
        }
    return identity, data


class SentinumCloudClient:
    """Independent TLS client. Disabled means no client, sockets or worker loop."""

    def __init__(self, settings, on_data):
        self.settings = dict(settings)
        self.on_data = on_data
        self.client = None
        self._lock = threading.RLock()
        self._active = False
        self._status = {
            "enabled": False, "connected": False, "state": "disabled",
            "error": None, "messages_received": 0, "last_message": None,
        }

    def status(self):
        with self._lock:
            return dict(self._status)

    def start(self):
        if not self.settings["enabled"]:
            return
        self._active = True
        self._status.update(enabled=True, state="connecting")
        try:
            self.settings = validate_settings(self.settings, self.settings)
            # VERSION1 callbacks support both paho 1.x and 2.x already used here.
            self.client = mqtt.Client(client_id="sentinum-ha-" + uuid.uuid4().hex[:16])
            self.client.username_pw_set(self.settings["username"], self.settings["password"])
            self.client.tls_set()  # System CA, certificate and hostname verification enabled
            self.client.reconnect_delay_set(min_delay=2, max_delay=120)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_connect_fail = self._on_connect_fail
            self.client.on_subscribe = self._on_subscribe
            self.client.on_message = self._on_message
            self.client.connect_async(self.settings["broker"], self.settings["port"], keepalive=60)
            self.client.loop_start()
        except Exception:
            self._status.update(state="error", error="Cloud-Verbindung konnte nicht gestartet werden.")
            logging.error("Sentinum Cloud: Verbindung konnte nicht gestartet werden.")

    def stop(self):
        # Gate in-flight deliveries before stopping; loop_stop waits for callback completion.
        with self._lock:
            self._active = False
            self._status.update(enabled=False, connected=False, state="disabled", error=None)
        if self.client:
            self.client.disconnect()
            self.client.loop_stop()
            self.client = None

    def _on_connect(self, client, userdata, flags, rc):
        with self._lock:
            if not self._active:
                return
            if rc != 0:
                self._status.update(connected=False, state="error",
                                    error=f"MQTT-Anmeldung abgelehnt (Code {rc}).")
                return
            topic = self.settings["topic"] or f'datahub/{self.settings["username"]}/+/+/+/up'
            result, _ = client.subscribe(topic, qos=1)
            if result != mqtt.MQTT_ERR_SUCCESS:
                self._status.update(state="error", error="MQTT-Abonnement fehlgeschlagen.")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        with self._lock:
            if not self._active:
                return
            denied = not granted_qos or any(q >= 128 for q in granted_qos)
            self._status.update(
                connected=not denied, state="error" if denied else "connected",
                error="Topic-Zugriff verweigert. Kunden-Topic prüfen." if denied else None,
            )

    def _on_connect_fail(self, client, userdata):
        with self._lock:
            if self._active:
                self._status.update(connected=False, state="error",
                                    error="Broker nicht erreichbar oder TLS-Prüfung fehlgeschlagen. Erneuter Versuch folgt.")

    def _on_disconnect(self, client, userdata, rc):
        with self._lock:
            if self._active:
                self._status.update(connected=False, state="connecting",
                                    error="Verbindung unterbrochen. Erneuter Versuch folgt.")

    def _on_message(self, client, userdata, msg):
        with self._lock:
            if not self._active:
                return
            try:
                if len(msg.payload) > 262144:
                    raise ValueError("Cloud-Nachricht zu groß.")
                normalized = normalize_message(msg.topic, json.loads(msg.payload))
                if normalized is None:
                    return
                if self.on_data(*normalized) is False:
                    raise ValueError("Sensordaten konnten nicht verarbeitet werden.")
                self._status["messages_received"] += 1
                self._status["last_message"] = datetime.now(timezone.utc).isoformat()
                self._status["error"] = None
            except Exception:
                # Never log the message, username, credentials or broker exceptions.
                self._status["error"] = "Cloud-Nachricht nicht verarbeitet: Geräte-ID, Payload-Format oder Decoder prüfen."
                logging.warning("Sentinum Cloud: Telemetrie konnte nicht verarbeitet werden.")
