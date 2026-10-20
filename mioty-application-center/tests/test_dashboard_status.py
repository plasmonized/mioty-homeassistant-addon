"""Operational dashboard counts and connection states, with no network calls."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from dashboard_status import dashboard_snapshot
from settings_manager import SettingsManager
from web_gui import WebGUI


NOW = 1800000000


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = SettingsManager(str(Path(self.temp.name) / "settings.json"))
        self.sensors = {}
        self.basestations = {}
        self.addon = SimpleNamespace(
            config={}, warning_threshold=3600, mqtt_manager=None, scaci_client=None,
            sentinum_cloud=None, get_sensor_list=lambda: self.sensors.copy(),
            get_basestation_list=lambda: self.basestations.copy(),
        )

    def snapshot(self):
        return dashboard_snapshot(self.addon, now=NOW)

    def test_all_radio_technologies_count_only_recent_active_sensors(self):
        self.sensors.update({
            "M": {"last_seen": NOW - 60},
            "L": {"type": "lorawan", "last_seen": NOW - 10},
            "C": {"type": "cellular", "last_seen": NOW - 100},
            "O": {"type": "oms", "last_seen": NOW - 50},
            "U": {"type": "future_radio", "last_seen": NOW - 100},
            "old": {"last_seen": NOW - 3601, "status": "active"},
            "offline": {"last_seen": NOW - 10, "status": "inactive"},
            "missing": {},
            "future": {"last_seen": NOW + 500},
        })
        result = self.snapshot()
        self.assertEqual(result["sensors"], {"active": 5, "total": 9})
        groups = {group["key"]: group for group in result["technologies"]}
        self.assertEqual(groups["mioty"]["sensors"], {"active": 1, "total": 5})
        self.assertEqual(groups["lora"]["sensors"]["active"], 1)
        self.assertIsNone(groups["cellular"]["basestations"])
        self.assertEqual(result["sensor_activity_window_seconds"], 3600)

    def test_base_stations_require_fresh_telemetry_and_respect_offline_status(self):
        self.basestations.update({
            "M": {"status": "online", "last_seen": NOW - 60},
            "old": {"status": "online", "last_seen": NOW - 301},
            "L": {"type": "lora", "status": {"online": True}, "last_seen": NOW - 30},
            "off": {"type": "lora", "status": {"online": False}, "last_seen": NOW - 5},
            "missing": {"type": "lora", "status": "online"},
        })
        result = self.snapshot()
        groups = {group["key"]: group for group in result["technologies"]}
        self.assertEqual(groups["mioty"]["basestations"], {"active": 1, "total": 2})
        self.assertEqual(groups["lora"]["basestations"], {"active": 1, "total": 3})
        self.assertEqual(result["basestation_activity_window_seconds"], 300)

    def test_overall_counts_ignore_list_filters_and_use_configurable_window(self):
        self.settings.set_setting("show_lora", False)
        self.settings.set_setting("show_oms", False)
        self.addon.warning_threshold = 120
        self.sensors.update({
            "M": {"last_seen": NOW - 121},
            "L": {"type": "lora", "last_seen": NOW - 10},
            "O": {"type": "oms", "last_seen": NOW - 10},
        })
        result = self.snapshot()
        self.assertEqual(result["sensors"], {"active": 2, "total": 3})
        self.assertEqual([group["key"] for group in result["technologies"]], ["mioty", "lora", "oms"])
        self.assertEqual(result["sensor_activity_window_seconds"], 120)

    def test_connection_health_is_separate_and_does_not_expose_credentials(self):
        self.addon.config = {
            "mqtt_broker": "input.invalid", "ha_mqtt_broker": "output.invalid",
            "mqtt_password": "test-password-never-return", "scaci_enabled": True,
            "sentinum_cloud_enabled": True, "sentinum_cloud_password": "test-cloud-password",
        }
        self.addon.mqtt_manager = SimpleNamespace(connected=True, ha_connected=False)
        self.addon.scaci_client = SimpleNamespace(get_connection_info=lambda: {"connected": False})
        self.addon.sentinum_cloud = SimpleNamespace(status=lambda: {"state": "connected", "connected": True})
        result = self.snapshot()
        connections = {item["id"]: item for item in result["connections"]}
        self.assertEqual(connections["service_center"]["state"], "connected")
        self.assertIn("SCACI: getrennt", connections["service_center"]["detail"])
        self.assertEqual(connections["mioty_mqtt"]["state"], "connected")
        self.assertEqual(connections["homeassistant_mqtt"]["state"], "disconnected")
        self.assertEqual(connections["sentinum_cloud"]["state"], "connected")
        output = json.dumps(result)
        for private in ("test-password-never-return", "test-cloud-password", "input.invalid", "output.invalid"):
            self.assertNotIn(private, output)

    def test_disabled_cloud_is_neutral_and_receive_errors_are_visible(self):
        result = self.snapshot()
        self.assertTrue(all(item["state"] == "disabled" for item in result["connections"]))
        self.addon.config["sentinum_cloud_enabled"] = True
        self.addon.sentinum_cloud = SimpleNamespace(status=lambda: {
            "state": "connected", "error": "safe receive error",
        })
        cloud = self.snapshot()["connections"][-1]
        self.assertEqual(cloud["state"], "error")
        self.addon.sentinum_cloud = None
        self.assertEqual(self.snapshot()["connections"][-1]["state"], "unknown")

    def test_scaci_alone_connects_service_center_not_mqtt(self):
        self.addon.config["scaci_enabled"] = True
        self.addon.scaci_client = SimpleNamespace(get_connection_info=lambda: {"connected": True})
        connections = {item["id"]: item for item in self.snapshot()["connections"]}
        self.assertEqual(connections["service_center"]["state"], "connected")
        self.assertEqual(connections["mioty_mqtt"]["state"], "disabled")

    def test_dashboard_endpoint_is_uncached_and_reports_unavailability(self):
        with patch("web_gui.SettingsManager", return_value=self.settings):
            gui = WebGUI(addon_instance=self.addon)
        web = gui.app.test_client()
        response = web.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.get_json()["sensors"]["active"], 0)
        gui.addon = None
        self.assertEqual(web.get("/api/dashboard").status_code, 503)


if __name__ == "__main__":
    unittest.main()
