"""Sensor platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import LOGGER, PARALLEL_UPDATES as PARALLEL_UPDATES
from homeassistant.components.sensor import SensorEntityDescription

from .home_climate import ENTITY_DESCRIPTIONS as HOME_CLIMATE_DESCRIPTIONS, JaamHAHomeClimateSensor
from .home_district import ENTITY_DESCRIPTIONS as HOME_DISTRICT_DESCRIPTIONS, JaamHAHomeDistrictSensor
from .home_district_temp import ENTITY_DESCRIPTIONS as HOME_DISTRICT_TEMP_DESCRIPTIONS, JaamHAHomeDistrictTempSensor
from .light_level import ENTITY_DESCRIPTIONS as LIGHT_LEVEL_DESCRIPTIONS, JaamHALightLevelSensor
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
    *LIGHT_LEVEL_DESCRIPTIONS,
)

# Dynamic sensor descriptions that should be created/removed based on data availability
DYNAMIC_SENSOR_DESCRIPTIONS = {
    **{desc.key: (desc, JaamHAHomeClimateSensor) for desc in HOME_CLIMATE_DESCRIPTIONS},
    **{desc.key: (desc, JaamHALightLevelSensor) for desc in LIGHT_LEVEL_DESCRIPTIONS},
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator

    # Track which dynamic sensors have been created (by entity_description.key)
    created_sensors: set[str] = set()

    # Add always-available sensors (home district, system info)
    async_add_entities(
        JaamHAHomeDistrictSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in HOME_DISTRICT_DESCRIPTIONS
    )
    async_add_entities(
        JaamHAHomeDistrictTempSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in HOME_DISTRICT_TEMP_DESCRIPTIONS
    )
    async_add_entities(
        JaamHASystemInfoSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in SYSTEM_INFO_DESCRIPTIONS
    )

    # Add initial dynamic sensors if data is already present
    data = coordinator.data or {}
    initial_entities = []
    for key, (entity_description, entity_class) in DYNAMIC_SENSOR_DESCRIPTIONS.items():
        if key in data and data[key] is not None:
            initial_entities.append(entity_class(coordinator=coordinator, entity_description=entity_description))
            created_sensors.add(key)
            LOGGER.debug("Creating initial dynamic sensor: %s", key)

    if initial_entities:
        async_add_entities(initial_entities)

    # Listener to dynamically add sensors when new data appears
    def _check_and_add_sensors() -> None:
        """Check coordinator data and add new sensors if available."""
        data = coordinator.data or {}
        new_entities = []

        for key, (entity_description, entity_class) in DYNAMIC_SENSOR_DESCRIPTIONS.items():
            # Check if sensor should be created
            if key not in created_sensors and key in data and data[key] is not None:
                new_entities.append(entity_class(coordinator=coordinator, entity_description=entity_description))
                created_sensors.add(key)
                LOGGER.info("Dynamically adding new sensor: %s with value %s", key, data[key])

        if new_entities:
            async_add_entities(new_entities)

    # Register listener to be called on every coordinator update
    entry.async_on_unload(coordinator.async_add_listener(_check_and_add_sensors))
