"""Button platform for xTool Laser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XToolDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class XToolButtonDescription(ButtonEntityDescription):
    """Describe an xTool action button."""

    action: str


BUTTONS: tuple[XToolButtonDescription, ...] = (
    XToolButtonDescription(
        key="pause_job",
        name="Pause job",
        action="pause",
        icon="mdi:pause-circle-outline",
    ),
    XToolButtonDescription(
        key="resume_job",
        name="Resume job",
        action="resume",
        icon="mdi:play-circle-outline",
    ),
    XToolButtonDescription(
        key="stop_job",
        name="Stop job",
        action="stop",
        icon="mdi:stop-circle-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up xTool action buttons."""
    coordinator: XToolDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(XToolButton(coordinator, entry, description) for description in BUTTONS)


class XToolButton(CoordinatorEntity[XToolDataUpdateCoordinator], ButtonEntity):
    """Representation of an xTool control button."""

    entity_description: XToolButtonDescription

    def __init__(
        self,
        coordinator: XToolDataUpdateCoordinator,
        entry: ConfigEntry,
        description: XToolButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_icon = description.icon

    async def async_press(self) -> None:
        """Send action command to device."""
        await self.coordinator.api.async_cnc_action(self.entity_description.action)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> dict[str, Any]:
        """Return shared device info."""
        data = self.coordinator.data or {}
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": data.get("machine_type", "xTool Laser"),
            "manufacturer": "xTool",
            "model": data.get("machine_type", "Unknown"),
            "configuration_url": f"http://{self.coordinator.api.host}:8080",
        }
