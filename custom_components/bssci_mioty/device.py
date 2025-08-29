"""Device platform for BSSCI mioty integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BSSCI mioty device trackers from a config entry."""
    # Device trackers are created dynamically when MQTT messages arrive
    pass


class BSSCIDeviceTracker(TrackerEntity):
    """Representation of a BSSCI mioty device tracker."""

    def __init__(self, sensor_eui: str, config_entry_id: str):
        """Initialize the device tracker."""
        self._sensor_eui = sensor_eui
        self._config_entry_id = config_entry_id
        self._attr_name = f"mioty Device {sensor_eui}"
        self._attr_unique_id = f"bssci_device_{sensor_eui}"
        self._attr_source_type = SourceType.ROUTER
        self._attr_is_connected = False
        self._last_seen = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"sensor_{self._sensor_eui}")},
            name=f"mioty Sensor {self._sensor_eui}",
            model="mioty IoT Sensor",
            manufacturer="BSSCI",
        )

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected."""
        return self._attr_is_connected

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        return {
            "sensor_eui": self._sensor_eui,
            "last_seen": self._last_seen,
            "source_type": self._attr_source_type.value,
        }

    def update_connection_status(self, connected: bool, last_seen: Optional[str] = None):
        """Update the connection status."""
        self._attr_is_connected = connected
        if last_seen:
            self._last_seen = last_seen
        self.async_write_ha_state()
