"""Sensor platform for xTool Laser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XToolDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class XToolSensorDescription(SensorEntityDescription):
    """Describe an xTool sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[XToolSensorDescription, ...] = (
    XToolSensorDescription(
        key="progress",
        name="Job progress",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("progress"),
    ),
    XToolSensorDescription(
        key="working_seconds",
        name="Working time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: round((data.get("working", 0) or 0) / 1000),
    ),
    XToolSensorDescription(
        key="line",
        name="Current G-code line",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("line"),
    ),
    XToolSensorDescription(
        key="working_state",
        name="Working state",
        value_fn=lambda data: data.get("working_state_label"),
    ),
    XToolSensorDescription(
        key="ws_state",
        name="Machine event",
        value_fn=lambda data: data.get("ws_state"),
    ),
    XToolSensorDescription(
        key="machine_type",
        name="Machine type",
        value_fn=lambda data: data.get("machine_type"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up xTool sensors."""
    coordinator: XToolDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(XToolSensor(coordinator, entry, description) for description in SENSORS)


class XToolSensor(CoordinatorEntity[XToolDataUpdateCoordinator], SensorEntity):
    """Representation of an xTool sensor."""

    entity_description: XToolSensorDescription

    def __init__(
        self,
        coordinator: XToolDataUpdateCoordinator,
        entry: ConfigEntry,
        description: XToolSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> Any:
        """Return sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})

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
