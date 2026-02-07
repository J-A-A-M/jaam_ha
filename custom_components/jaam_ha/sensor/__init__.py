"""Sensor platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from homeassistant.components.sensor import SensorEntityDescription

from .home_danger import ENTITY_DESCRIPTIONS as HOME_DANGER_DESCRIPTIONS, JaamHAHomeDangerSensor
from .home_district import ENTITY_DESCRIPTIONS as HOME_DISTRICT_DESCRIPTIONS, JaamHAHomeDistrictSensor
from .system_info import ENTITY_DESCRIPTIONS as SYSTEM_INFO_DESCRIPTIONS, JaamHASystemInfoSensor

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Combine all entity descriptions from different modules
ENTITY_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    *HOME_DANGER_DESCRIPTIONS,
    *HOME_DISTRICT_DESCRIPTIONS,
    *SYSTEM_INFO_DESCRIPTIONS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Add home danger sensor
    async_add_entities(
        JaamHAHomeDangerSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in HOME_DANGER_DESCRIPTIONS
    )
    # Add home district sensor
    async_add_entities(
        JaamHAHomeDistrictSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in HOME_DISTRICT_DESCRIPTIONS
    )
    # Add system info sensors
    async_add_entities(
        JaamHASystemInfoSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in SYSTEM_INFO_DESCRIPTIONS
    )
