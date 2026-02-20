"""Config flow for xTool Laser integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import XToolApiClient, XToolApiError
from .const import (
    DEFAULT_DISCOVERY_TIMEOUT,
    CONF_SCAN_INTERVAL,
    CONF_USE_WEBSOCKET,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    api = XToolApiClient(hass, data[CONF_HOST])
    if not await api.async_ping():
        raise CannotConnect

    machine_type = await api.async_get_machine_type()
    mac = await api.async_get_mac()
    return {"title": data[CONF_NAME], "machine_type": machine_type, "mac": mac}


class XToolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for xTool Laser."""

    VERSION = 1
    _discovered: dict[str, dict[str, Any]]

    def __init__(self) -> None:
        self._discovered = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show first setup menu."""
        return self.async_show_menu(step_id="user", menu_options=["discover", "manual"])

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle manual host entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except XToolApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["mac"] or user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{user_input[CONF_NAME]} ({info['machine_type']})",
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_NAME: user_input[CONF_NAME],
                    },
                    options={
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                        CONF_USE_WEBSOCKET: True,
                    },
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
            errors=errors,
        )

    async def async_step_discover(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Discover devices and allow selecting one."""
        errors: dict[str, str] = {}

        if not self._discovered:
            api = XToolApiClient(self.hass, "127.0.0.1")
            devices = await api.async_discover_devices(timeout=DEFAULT_DISCOVERY_TIMEOUT)
            self._discovered = {item["host"]: item for item in devices if item.get("host")}

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        hosts = sorted(self._discovered)

        if user_input is not None:
            chosen_host = user_input[CONF_HOST]
            chosen_name = user_input.get(CONF_NAME) or self._discovered[chosen_host].get("name") or DEFAULT_NAME

            try:
                info = await _validate_input(self.hass, {CONF_HOST: chosen_host, CONF_NAME: chosen_name})
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except XToolApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["mac"] or chosen_host)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{chosen_name} ({info['machine_type']})",
                    data={CONF_HOST: chosen_host, CONF_NAME: chosen_name},
                    options={
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                        CONF_USE_WEBSOCKET: True,
                    },
                )

        default_host = hosts[0]
        default_name = self._discovered[default_host].get("name") or DEFAULT_NAME

        return self.async_show_form(
            step_id="discover",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=default_host): vol.In(hosts),
                    vol.Optional(CONF_NAME, default=default_name): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> XToolOptionsFlow:
        """Return options flow."""
        return XToolOptionsFlow(config_entry)


class XToolOptionsFlow(config_entries.OptionsFlow):
    """Options flow for xTool Laser."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                    vol.Required(
                        CONF_USE_WEBSOCKET,
                        default=self._config_entry.options.get(CONF_USE_WEBSOCKET, True),
                    ): bool,
                }
            ),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
