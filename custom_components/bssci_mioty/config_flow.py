"""Config flow for BSSCI mioty integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_MQTT_BROKER,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    CONF_MQTT_PASSWORD,
    CONF_BASE_TOPIC,
    DEFAULT_MQTT_PORT,
    DEFAULT_BASE_TOPIC,
)

_LOGGER = logging.getLogger(__name__)


class BSSCIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BSSCI mioty."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Test the connection
                await self._test_connection(user_input)
                
                # Create entry
                return self.async_create_entry(
                    title=f"BSSCI mioty ({user_input[CONF_MQTT_BROKER]})",
                    data=user_input,
                )
            except Exception as e:
                _LOGGER.error("Failed to connect to MQTT broker: %s", e)
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required(CONF_MQTT_BROKER): cv.string,
            vol.Required(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): cv.port,
            vol.Optional(CONF_MQTT_USERNAME): cv.string,
            vol.Optional(CONF_MQTT_PASSWORD): cv.string,
            vol.Required(CONF_BASE_TOPIC, default=DEFAULT_BASE_TOPIC): cv.string,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _test_connection(self, config: Dict[str, Any]) -> None:
        """Test the MQTT connection."""
        import paho.mqtt.client as mqtt
        
        client = mqtt.Client()
        
        if config.get(CONF_MQTT_USERNAME):
            client.username_pw_set(
                config[CONF_MQTT_USERNAME],
                config.get(CONF_MQTT_PASSWORD, "")
            )

        # Test connection
        try:
            await self.hass.async_add_executor_job(
                client.connect,
                config[CONF_MQTT_BROKER],
                config[CONF_MQTT_PORT],
                10
            )
            await self.hass.async_add_executor_job(client.disconnect)
        except Exception as e:
            _LOGGER.error("Connection test failed: %s", e)
            raise

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return BSSCIOptionsFlowHandler(config_entry)


class BSSCIOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for BSSCI mioty."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required(
                CONF_MQTT_BROKER,
                default=self.config_entry.data.get(CONF_MQTT_BROKER, "")
            ): cv.string,
            vol.Required(
                CONF_MQTT_PORT,
                default=self.config_entry.data.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT)
            ): cv.port,
            vol.Optional(
                CONF_MQTT_USERNAME,
                default=self.config_entry.data.get(CONF_MQTT_USERNAME, "")
            ): cv.string,
            vol.Optional(
                CONF_MQTT_PASSWORD,
                default=self.config_entry.data.get(CONF_MQTT_PASSWORD, "")
            ): cv.string,
            vol.Required(
                CONF_BASE_TOPIC,
                default=self.config_entry.data.get(CONF_BASE_TOPIC, DEFAULT_BASE_TOPIC)
            ): cv.string,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
