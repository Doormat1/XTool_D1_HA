"""Data update coordinator for xTool Laser."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import XToolApiClient, XToolApiError
from .const import ATTR_WS_STATE, DOMAIN

WORKING_STATE_MAP = {
    "0": "idle",
    "1": "running_api",
    "2": "running_button",
}

LOGGER = logging.getLogger(__name__)


class XToolDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate xTool data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: XToolApiClient,
        entry_id: str,
        scan_interval: int,
        use_websocket: bool,
    ) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{entry_id}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.entry_id = entry_id
        self.use_websocket = use_websocket

    async def async_start(self) -> None:
        """Start background listeners."""
        if self.use_websocket:
            await self.api.async_start_ws(self._async_handle_ws_message)

    async def async_stop(self) -> None:
        """Stop background listeners."""
        await self.api.async_stop_ws()

    async def _async_update_data(self) -> dict:
        """Fetch latest data from device."""
        try:
            data = await self.api.async_get_snapshot()
        except XToolApiError as err:
            raise UpdateFailed(str(err)) from err

        data["working_state_label"] = WORKING_STATE_MAP.get(data.get("working_state", "0"), "unknown")
        if self.data and ATTR_WS_STATE in self.data:
            data[ATTR_WS_STATE] = self.data[ATTR_WS_STATE]

        return data

    async def _async_handle_ws_message(self, message: str) -> None:
        """Merge incoming WebSocket state into coordinator data."""
        current = dict(self.data or {})
        current[ATTR_WS_STATE] = message
        self.async_set_updated_data(current)
