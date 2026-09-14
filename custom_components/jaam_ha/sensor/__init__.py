"""Sensor platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.jaam_ha.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.jaam_ha.entity import async_setup_dynamic_entities
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


def _should_create_sensor(key: str, data: dict[str, Any]) -> bool:
    """A sensor is created once it's hardware-supported and has reported a real value."""
    return _is_sensor_supported(key, data.get("supported_sensors")) and key in data and data[key] is not None


def _should_remove_sensor(key: str, data: dict[str, Any]) -> bool:
    """Remove a sensor if hardware support says so; a missing/None value alone isn't enough.

    Note: this intentionally differs from `_should_create_sensor` - once a
    `supported_sensors` list is available, a single update where `key` is
    transiently missing or None should not remove an already-created sensor. Older
    firmware without a `supported_sensors` list falls back to removing on a missing key.
    """
    supported_sensors = data.get("supported_sensors")
    if supported_sensors is not None:
        return not _is_sensor_supported(key, supported_sensors)
    return key not in data


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator

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

    async_setup_dynamic_entities(
        hass,
        entry,
        coordinator,
        async_add_entities,
        domain="sensor",
        dynamic_descriptions=DYNAMIC_SENSOR_DESCRIPTIONS,
        should_create=_should_create_sensor,
        should_remove=_should_remove_sensor,
    )
