"""Sensor platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from homeassistant.components.sensor import SensorEntityDescription

from .home_climate import ENTITY_DESCRIPTIONS as HOME_CLIMATE_DESCRIPTIONS, JaamHAHomeClimateSensor
from .home_district import ENTITY_DESCRIPTIONS as HOME_DISTRICT_DESCRIPTIONS, JaamHAHomeDistrictSensor
from .home_district_temp import ENTITY_DESCRIPTIONS as HOME_DISTRICT_TEMP_DESCRIPTIONS, JaamHAHomeDistrictTempSensor
from .system_info import ENTITY_DESCRIPTIONS as SYSTEM_INFO_DESCRIPTIONS, JaamHASystemInfoSensor

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


# Combine all entity descriptions from different modules
ENTITY_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    *HOME_DISTRICT_DESCRIPTIONS,
    *HOME_DISTRICT_TEMP_DESCRIPTIONS,
    *SYSTEM_INFO_DESCRIPTIONS,
    *HOME_CLIMATE_DESCRIPTIONS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Add home district sensor
    async_add_entities(
        JaamHAHomeDistrictSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in HOME_DISTRICT_DESCRIPTIONS
    )
    # Add home district temperature sensor
    async_add_entities(
        JaamHAHomeDistrictTempSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in HOME_DISTRICT_TEMP_DESCRIPTIONS
    )

    # Add system info sensors
    async_add_entities(
        JaamHASystemInfoSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in SYSTEM_INFO_DESCRIPTIONS
    )

    # Add home climate sensors only if data is present
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data or {}
    home_climate_entities = []
    for entity_description in HOME_CLIMATE_DESCRIPTIONS:
        if entity_description.key not in data or data[entity_description.key] is None:
            continue
        home_climate_entities.append(
            JaamHAHomeClimateSensor(
                coordinator=coordinator,
                entity_description=entity_description,
            )
        )
    if home_climate_entities:
        async_add_entities(home_climate_entities)
