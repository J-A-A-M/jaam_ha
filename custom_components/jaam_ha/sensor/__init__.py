"""Sensor platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.jaam_ha.const import LOGGER, PARALLEL_UPDATES as PARALLEL_UPDATES
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers import entity_registry as er

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

# Dynamic sensor descriptions that should be created/removed based on hardware support
DYNAMIC_SENSOR_DESCRIPTIONS = {
    **{desc.key: (desc, JaamHAHomeClimateSensor) for desc in HOME_CLIMATE_DESCRIPTIONS},
    **{desc.key: (desc, JaamHALightLevelSensor) for desc in LIGHT_LEVEL_DESCRIPTIONS},
}

# Mapping from supported_sensors names to sensor keys
SUPPORTED_SENSOR_MAPPING = {
    "temperature": "climate_temp",
    "humidity": "climate_humidity",
    "pressure": "climate_pressure",
    "light": "light_level",
}


def _is_sensor_supported(sensor_key: str, supported_sensors: list[str] | None) -> bool:
    """Check if a sensor is supported by the device hardware."""
    # If no supported_sensors list, assume all supported (backward compatibility)
    if supported_sensors is None:
        return True

    # Check if this sensor key maps to a supported sensor name
    for sensor_name, mapped_key in SUPPORTED_SENSOR_MAPPING.items():
        if mapped_key == sensor_key and sensor_name in supported_sensors:
            return True

    return False


def _remove_unsupported_sensors(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    data: dict[str, Any],
) -> None:
    """Remove sensors from registry that are no longer supported by hardware."""
    supported_sensors = data.get("supported_sensors")
    entity_registry = er.async_get(hass)
    chip_id = data.get("chip_id") or entry.entry_id

    # Determine which sensors to remove
    sensors_to_remove: set[str] = set()

    if supported_sensors is not None:
        # Use explicit supported_sensors list from device
        for key in DYNAMIC_SENSOR_DESCRIPTIONS:
            if not _is_sensor_supported(key, supported_sensors):
                sensors_to_remove.add(key)
    else:
        # Fallback: Remove sensors where field is not present in data (not supported)
        # Note: Sensor can have None value if supported but not configured
        for key in DYNAMIC_SENSOR_DESCRIPTIONS:
            if key not in data:
                sensors_to_remove.add(key)

    if not sensors_to_remove:
        return

    removed_count = 0
    for key in sensors_to_remove:
        # Try both possible unique_id formats
        unique_id_with_chip = f"jaam_{chip_id}_{key}"
        unique_id_fallback = f"{entry.entry_id}_{key}"

        entity_id = entity_registry.async_get_entity_id("sensor", "jaam_ha", unique_id_with_chip)
        if not entity_id:
            entity_id = entity_registry.async_get_entity_id("sensor", "jaam_ha", unique_id_fallback)

        if entity_id:
            LOGGER.info("Removing sensor %s - not supported by device hardware", entity_id)
            entity_registry.async_remove(entity_id)
            removed_count += 1

    if removed_count > 0:
        LOGGER.info("Removed %d unsupported sensor(s) from device", removed_count)


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

    # Add initial dynamic sensors if supported by hardware
    data = coordinator.data or {}
    supported_sensors = data.get("supported_sensors")
    initial_entities = []

    for key, (entity_description, entity_class) in DYNAMIC_SENSOR_DESCRIPTIONS.items():
        if _is_sensor_supported(key, supported_sensors) and key in data and data[key] is not None:
            initial_entities.append(entity_class(coordinator=coordinator, entity_description=entity_description))
            created_sensors.add(key)

    if initial_entities:
        async_add_entities(initial_entities)

    # Remove sensors that are no longer supported by hardware
    _remove_unsupported_sensors(hass, entry, data)

    # Listener to dynamically add/remove sensors based on hardware support
    def _check_and_add_sensors() -> None:
        """Check coordinator data and add new sensors if available and supported, remove unsupported."""
        data = coordinator.data or {}
        supported_sensors = data.get("supported_sensors")
        new_entities = []

        # Add new sensors if supported
        for key, (entity_description, entity_class) in DYNAMIC_SENSOR_DESCRIPTIONS.items():
            if key in created_sensors:
                continue

            if _is_sensor_supported(key, supported_sensors) and key in data and data[key] is not None:
                new_entities.append(entity_class(coordinator=coordinator, entity_description=entity_description))
                created_sensors.add(key)
                LOGGER.info("Dynamically adding new sensor: %s with value %s", key, data[key])

        if new_entities:
            async_add_entities(new_entities)

        # Remove sensors that became unsupported or have None values
        entity_registry = er.async_get(hass)
        chip_id = data.get("chip_id") or entry.entry_id

        for key in list(created_sensors):  # Use list() to avoid RuntimeError during iteration
            should_remove = False

            if supported_sensors is not None:
                # Use explicit supported_sensors list
                if not _is_sensor_supported(key, supported_sensors):
                    should_remove = True
            elif key not in data:
                # Fallback: Remove if field is not present in data (not supported)
                should_remove = True

            if should_remove:
                # Try both possible unique_id formats
                unique_id_with_chip = f"jaam_{chip_id}_{key}"
                unique_id_fallback = f"{entry.entry_id}_{key}"

                entity_id = entity_registry.async_get_entity_id("sensor", "jaam_ha", unique_id_with_chip)
                if not entity_id:
                    entity_id = entity_registry.async_get_entity_id("sensor", "jaam_ha", unique_id_fallback)

                if entity_id:
                    LOGGER.info("Dynamically removing sensor %s - no longer supported", entity_id)
                    entity_registry.async_remove(entity_id)
                    created_sensors.discard(key)

    # Register listener to be called on every coordinator update
    entry.async_on_unload(coordinator.async_add_listener(_check_and_add_sensors))
