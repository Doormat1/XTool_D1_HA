"""xTool Laser integration setup."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .api import XToolApiClient
from .const import (
    ATTR_ENTRY_ID,
    CONF_SCAN_INTERVAL,
    CONF_USE_WEBSOCKET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_PAUSE_JOB,
    SERVICE_RESUME_JOB,
    SERVICE_STOP_JOB,
)
from .coordinator import XToolDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up xTool Laser from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    use_websocket = entry.options.get(CONF_USE_WEBSOCKET, True)

    api = XToolApiClient(hass, entry.data["host"])
    coordinator = XToolDataUpdateCoordinator(
        hass,
        api=api,
        entry_id=entry.entry_id,
        scan_interval=scan_interval,
        use_websocket=use_websocket,
    )

    hass.data[DOMAIN][entry.entry_id] = {"api": api, "coordinator": coordinator}
    _async_register_services(hass)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await coordinator.async_start()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: XToolDataUpdateCoordinator = data["coordinator"]

    await coordinator.async_stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            _async_unregister_services(hass)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register xTool services once per domain."""
    schema = vol.Schema({vol.Optional(ATTR_ENTRY_ID): str})

    async def handle_pause(call: ServiceCall) -> None:
        await _async_handle_job_service(hass, call, "pause")

    async def handle_resume(call: ServiceCall) -> None:
        await _async_handle_job_service(hass, call, "resume")

    async def handle_stop(call: ServiceCall) -> None:
        await _async_handle_job_service(hass, call, "stop")

    if not hass.services.has_service(DOMAIN, SERVICE_PAUSE_JOB):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PAUSE_JOB,
            handle_pause,
            schema=schema,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RESUME_JOB):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESUME_JOB,
            handle_resume,
            schema=schema,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_STOP_JOB):
        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_JOB,
            handle_stop,
            schema=schema,
        )


def _async_unregister_services(hass: HomeAssistant) -> None:
    """Remove registered xTool services."""
    for service in (SERVICE_PAUSE_JOB, SERVICE_RESUME_JOB, SERVICE_STOP_JOB):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)


async def _async_handle_job_service(hass: HomeAssistant, call: ServiceCall, action: str) -> None:
    """Handle pause/resume/stop service calls."""
    entry_id = call.data.get(ATTR_ENTRY_ID)
    entries = _get_target_entries(hass, entry_id)

    for target_entry_id in entries:
        item = hass.data[DOMAIN][target_entry_id]
        api: XToolApiClient = item["api"]
        coordinator: XToolDataUpdateCoordinator = item["coordinator"]
        await api.async_cnc_action(action)
        await coordinator.async_request_refresh()


def _get_target_entries(hass: HomeAssistant, entry_id: str | None) -> list[str]:
    """Return targeted entry IDs for service calls."""
    if DOMAIN not in hass.data or not hass.data[DOMAIN]:
        raise HomeAssistantError("No xTool integrations are loaded")

    if entry_id:
        if entry_id not in hass.data[DOMAIN]:
            raise HomeAssistantError(f"Unknown xTool entry_id: {entry_id}")
        return [entry_id]

    return list(hass.data[DOMAIN].keys())
