"""Offline regression tests: no real MQTT credentials or network connections."""

import base64
import json
import os
import sys
import tempfile
import threading
import unittest
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from sentinum_cloud import (DEFAULTS, PREFIX, SentinumCloudClient, cloud_settings,
                            normalize_message, validate_settings)
from settings_manager import SettingsManager
from main import BSSCIAddon
from decoder_manager import DecoderManager
from payload_decoder import PayloadDecoder
from web_gui import WebGUI


TOPIC = "datahub/example/eos/eos/eos_cellular_012345678901236/up"
EOS = "12100531965F0D48000204B004B0FF3807D00064012D"


def decoder_manager():
    """Actual decoder engine, without unrelated application-key storage setup."""
    engine = PayloadDecoder.__new__(PayloadDecoder)
    blueprint = Path(__file__).resolve().parents[1] / "app/builtin_decoders/sentinum_eos_blueprint.json"
    engine.decoder_files = {
        "sentinum_eos_blueprint": {"type": "blueprint", "name": "Sentinum Eos", "file_path": str(blueprint)}
    }
    engine.decoders = {}
    engine.secure_key_manager = None
    engine.save_decoders = MagicMock()
    manager = DecoderManager.__new__(DecoderManager)
    manager.payload_decoder = engine
    manager.iodd_service = None
    return manager


def addon():
    instance = BSSCIAddon.__new__(BSSCIAddon)
    instance.config = {}
    instance.sentinum_cloud = None
    instance._cloud_lifecycle_lock = threading.Lock()
    instance.sensors = {}
    instance.sensor_last_seen = {}
    instance.sensor_warnings = {}
    instance.live_sensors = OrderedDict()
    instance.live_lock = threading.Lock()
    instance.decoder_manager = decoder_manager()
    instance.mqtt_manager = MagicMock()
    instance.mqtt_manager.publish_discovery.return_value = True
    instance.mqtt_manager.ha_client.publish.return_value = SimpleNamespace(rc=0)
    return instance


class NormalizationTests(unittest.TestCase):
    def test_real_eos_hex_and_time(self):
        identity, data = normalize_message(TOPIC, {
            "deviceId": "eos_cellular_012345678901236", "payload": EOS,
            "timestamp": "2026-10-20T13:00:00+02:00",
        })
        self.assertEqual(identity, "012345678901236")
        self.assertEqual(data["data"], list(bytes.fromhex(EOS)))
        self.assertEqual(data["timestamp_ns"], 1792494000000000000)
        self.assertEqual(data["type"], "cellular")
        self.assertIsNone(data["rssi"])  # Do not fabricate signal measurements

    def test_legacy_bytearray_and_base64(self):
        legacy = TOPIC.replace("datahub/", "devices/")
        for body in (
            {"data": [1, 2, 3]},
            {"payload": base64.b64encode(b"\1\2\3").decode(), "encoding": "base64"},
            {"payload": {"raw": "010203", "encoding": "hex"}},
        ):
            self.assertEqual(normalize_message(legacy, body)[1]["data"], [1, 2, 3])

    def test_decoded_measurements(self):
        result = normalize_message(TOPIC, {"measurements": {
            "temperature": {"value": 22.5, "unit": "°C"}, "alarm": True,
        }})[1]["cloud_decoded"]
        self.assertTrue(result["decoded"])
        self.assertEqual(result["data"]["temperature"], {"value": 22.5, "unit": "°C"})

    def test_bad_messages_do_not_reach_pipeline(self):
        for body in (
            {}, [], {"payload": "GG"}, {"payload": [256]},
            {"payload": "AA", "deviceId": "different"}, {"payload": "AA", "encoding": "unknown"},
            {"payload": "AA", "timestamp": "invalid"},
        ):
            with self.subTest(body=body), self.assertRaises((ValueError, TypeError)):
                normalize_message(TOPIC, body)
        self.assertIsNone(normalize_message(TOPIC.replace("_cellular_", "_mioty_"), {"payload": EOS}))
        with self.assertRaises(ValueError):
            normalize_message(TOPIC.replace("/up", "/reported_shadow"), {"payload": EOS})


class LifecycleTests(unittest.TestCase):
    def test_disabled_creates_no_client_or_network(self):
        with patch("sentinum_cloud.mqtt.Client") as factory:
            client = SentinumCloudClient(DEFAULTS, MagicMock())
            client.start()
            client.stop()
            factory.assert_not_called()
            self.assertEqual(client.status()["state"], "disabled")

    def test_tls_subscribe_errors_and_disable(self):
        config = {**DEFAULTS, "enabled": True, "username": "example", "password": "offline-test"}
        callback = MagicMock()
        with patch("sentinum_cloud.mqtt.Client") as factory:
            mqtt = factory.return_value
            mqtt.subscribe.return_value = (0, 1)
            client = SentinumCloudClient(config, callback)
            client.start()
            mqtt.tls_set.assert_called_once_with()
            mqtt.tls_insecure_set.assert_not_called()
            mqtt.connect_async.assert_called_once_with("broker.sentinum.de", 8883, keepalive=60)
            client._on_connect(mqtt, None, {}, 0)
            mqtt.subscribe.assert_called_once_with("datahub/example/+/+/+/up", qos=1)
            self.assertFalse(client.status()["connected"])
            client._on_subscribe(mqtt, None, 1, [128])
            self.assertEqual(client.status()["state"], "error")
            client._on_subscribe(mqtt, None, 1, [1])
            self.assertTrue(client.status()["connected"])
            client._on_message(mqtt, None, SimpleNamespace(topic=TOPIC, payload=b"not-json"))
            self.assertEqual(client.status()["messages_received"], 0)
            self.assertNotIn("offline-test", str(client.status()))
            client._on_message(mqtt, None, SimpleNamespace(topic=TOPIC, payload=json.dumps({"payload": EOS}).encode()))
            self.assertEqual(client.status()["messages_received"], 1)
            callback.assert_called_once()
            client._on_disconnect(mqtt, None, 1)
            self.assertEqual(client.status()["state"], "connecting")
            client.stop()
            mqtt.disconnect.assert_called_once()
            mqtt.loop_stop.assert_called_once()
            client._on_message(mqtt, None, SimpleNamespace(topic=TOPIC, payload=b"{}"))
            self.assertEqual(callback.call_count, 1)
            self.assertEqual(client.status()["state"], "disabled")

    def test_validation(self):
        for change in ({"enabled": "false"}, {"port": 0}, {"port": "abc"},
                       {"broker": "mqtts://example"}, {"topic": "#"},
                       {"enabled": True}, {"topic": "datahub/+/+/+/+/up"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_settings(change, DEFAULTS)
        current = {**DEFAULTS, "password": "offline-test"}
        self.assertEqual(validate_settings({"password": "***"}, current)["password"], "offline-test")
        self.assertFalse(validate_settings({"enabled": False}, DEFAULTS)["enabled"])


class PipelineAndApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = SettingsManager(str(Path(self.temp.name) / "settings.json"))
        self.addon = addon()
        with patch("web_gui.SettingsManager", return_value=self.settings):
            self.gui = WebGUI(addon_instance=self.addon)
        self.web = self.gui.app.test_client()

    def tearDown(self):
        if self.addon.sentinum_cloud:
            self.addon.sentinum_cloud.stop()
        self.temp.cleanup()

    def test_eos_to_dashboard_live_and_home_assistant(self):
        identity, data = normalize_message(TOPIC, {"payload": EOS})
        self.assertTrue(self.addon._handle_sentinum_cloud_data(identity, data))
        result = self.addon.sensors[identity]
        self.assertEqual(result["type"], "cellular")
        self.assertEqual(result["decoded_data"]["data"]["radar_peaks"]["value"], 2)
        self.assertEqual(result["decoded_data"]["data"]["master"]["value"], 1.2)
        sensors = self.web.get("/api/sensors").get_json()
        self.assertEqual(sensors[0]["type"], "cellular")
        live = self.web.get("/api/livedata").get_json()["sensors"][0]
        self.assertEqual(live["type"], "cellular")
        self.assertTrue(live["messages"][0]["has_decoded"])
        publishes = self.addon.mqtt_manager.ha_client.publish.call_args_list
        self.assertTrue(publishes)
        state = json.loads(publishes[-1].args[1])
        self.assertEqual(state["radar_peaks"]["value"], 2)
        self.assertNotIn("rssi", state)

    def test_manual_assignment_is_preserved(self):
        self.addon.decoder_manager.payload_decoder.decoders["012345678901236"] = {"decoder_name": "custom"}
        with patch.object(self.addon, "handle_sensor_data", return_value=True):
            self.addon._handle_sentinum_cloud_data(*normalize_message(TOPIC, {"payload": EOS}))
        self.assertEqual(self.addon.decoder_manager.get_sensor_assignments()["assignments"]["012345678901236"]["decoder_name"], "custom")

    def test_predecoded_to_pipeline(self):
        identity, data = normalize_message(TOPIC, {"measurements": {"temperature": 25}})
        self.assertTrue(self.addon._handle_sentinum_cloud_data(identity, data))
        self.assertEqual(self.addon.sensors[identity]["decoded_data"]["data"]["temperature"]["value"], 25)
        self.assertEqual(self.addon._get_device_info_from_decoder(identity, "test")["manufacturer"], "Sentinum")
        self.assertTrue(self.addon.mqtt_manager.ha_client.publish.called)

    def test_settings_password_mask_persistence_and_disable(self):
        with patch("sentinum_cloud.mqtt.Client") as factory:
            self.assertEqual(self.web.get("/api/sentinum-cloud").get_json(), DEFAULTS)
            response = self.web.post("/api/sentinum-cloud", json={
                "enabled": True, "username": "example", "password": "offline-test",
            })
            self.assertEqual(response.status_code, 200)
            for path in ("/api/sentinum-cloud", "/api/settings", "/api/sentinum-cloud/status"):
                self.assertNotIn("offline-test", self.web.get(path).get_data(as_text=True))
            self.assertEqual(self.web.get("/api/sentinum-cloud").get_json()["password"], "***")
            self.assertEqual(self.web.post("/api/sentinum-cloud", json={"password": "***"}).status_code, 200)
            loaded = SettingsManager(self.settings.config_file)
            self.assertEqual(cloud_settings(loaded.get_all_settings())["password"], "offline-test")
            self.assertEqual(os.stat(self.settings.config_file).st_mode & 0o777, 0o600)
            self.assertEqual(self.web.post("/api/sentinum-cloud", json={"enabled": False}).status_code, 200)
            self.assertEqual(self.web.get("/api/sentinum-cloud/status").get_json()["state"], "disabled")
            factory.return_value.disconnect.assert_called()
            self.assertEqual(self.web.post("/api/sentinum-cloud", json={"password": ""}).status_code, 200)
            self.assertEqual(self.web.get("/api/sentinum-cloud").get_json()["password"], "")

    def test_validation_does_not_persist_and_failed_save_rolls_back(self):
        for data in (None, [], {"enabled": True}, {"port": -1}, {"topic": "#"}):
            self.assertEqual(self.web.post("/api/sentinum-cloud", json=data).status_code, 400)
        self.assertFalse(self.settings.get_setting(PREFIX + "enabled", False))
        with patch("settings_manager.os.replace", side_effect=OSError("simulated disk error")):
            response = self.web.post("/api/sentinum-cloud", json={"username": "new"})
            self.assertEqual(response.status_code, 500)
        self.assertEqual(self.settings.get_setting(PREFIX + "username", ""), "")

    def test_settings_page_keeps_existing_integrations_and_ingress(self):
        response = self.web.get("/settings", headers={"X-Ingress-Path": "/api/hassio_ingress/test"})
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for token in ("sentinum-cloud-form", "scaciSettingsForm", "haSettingsForm",
                      "/api/hassio_ingress/test"):
            self.assertIn(token, html)


if __name__ == "__main__":
    unittest.main()
