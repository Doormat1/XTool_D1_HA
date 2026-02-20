"""Binary sensor platform for xTool Laser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XToolDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class XToolBinarySensorDescription(BinarySensorEntityDescription):
    """Describe an xTool binary sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


BINARY_SENSORS: tuple[XToolBinarySensorDescription, ...] = (
    XToolBinarySensorDescription(
        key="sd_card_inserted",
        name="SD card inserted",
        value_fn=lambda data: bool((data.get("peripheral_status") or {}).get("sdCard", 0)),
    ),
    XToolBinarySensorDescription(
        key="limit_stop_enabled",
        name="Limit stop enabled",
        value_fn=lambda data: bool((data.get("peripheral_status") or {}).get("limitStopFlag", 0)),
    ),
    XToolBinarySensorDescription(
        key="tilt_stop_enabled",
        name="Tilt stop enabled",
        value_fn=lambda data: bool((data.get("peripheral_status") or {}).get("tiltStopFlag", 0)),
    ),
    XToolBinarySensorDescription(
        key="moving_stop_enabled",
        name="Moving stop enabled",
        value_fn=lambda data: bool((data.get("peripheral_status") or {}).get("movingStopFlag", 0)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up xTool binary sensors."""
    coordinator: XToolDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(XToolBinarySensor(coordinator, entry, description) for description in BINARY_SENSORS)


class XToolBinarySensor(CoordinatorEntity[XToolDataUpdateCoordinator], BinarySensorEntity):
    """Representation of an xTool binary sensor."""

    entity_description: XToolBinarySensorDescription

    def __init__(
        self,
        coordinator: XToolDataUpdateCoordinator,
        entry: ConfigEntry,
        description: XToolBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def is_on(self) -> bool:
        """Return binary state."""
        return bool(self.entity_description.value_fn(self.coordinator.data or {}))

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
