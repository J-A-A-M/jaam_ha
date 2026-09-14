"""Switch platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.jaam_ha.const import PARALLEL_UPDATES as PARALLEL_UPDATES, SUPPORTED_SWITCH_MAPPING
from custom_components.jaam_ha.entity import async_setup_dynamic_entities
from homeassistant.components.switch import SwitchEntityDescription

from .display import ENTITY_DESCRIPTIONS as DISPLAY_DESCRIPTIONS, JaamHADisplaySwitch
from .map import ENTITY_DESCRIPTIONS as MAP_DESCRIPTIONS, JaamHAMapSwitch
from .night_mode import ENTITY_DESCRIPTIONS as NIGHT_MODE_DESCRIPTIONS, JaamHANightModeSwitch

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


# Combine all entity descriptions from different modules
ENTITY_DESCRIPTIONS: tuple[SwitchEntityDescription, ...] = (
    *NIGHT_MODE_DESCRIPTIONS,
    *DISPLAY_DESCRIPTIONS,
    *MAP_DESCRIPTIONS,
)

# Dynamic switch descriptions that should be created/removed based on hardware support
DYNAMIC_SWITCH_DESCRIPTIONS = {
    **{desc.key: (desc, JaamHANightModeSwitch) for desc in NIGHT_MODE_DESCRIPTIONS},
    **{desc.key: (desc, JaamHADisplaySwitch) for desc in DISPLAY_DESCRIPTIONS},
    **{desc.key: (desc, JaamHAMapSwitch) for desc in MAP_DESCRIPTIONS},
}


def _is_switch_supported(switch_key: str, supported_sensors: list[str] | None) -> bool:
    """Check if a switch is supported by the device hardware."""
    # If no supported_sensors list, assume all supported (backward compatibility)
    if supported_sensors is None:
        return True

    # Check if this switch key maps to a supported sensor name
    for sensor_name, mapped_key in SUPPORTED_SWITCH_MAPPING.items():
        if mapped_key == switch_key and sensor_name in supported_sensors:
            return True

    return False


def _should_create_switch(key: str, data: dict[str, Any]) -> bool:
    """A switch is created once it's hardware-supported and has reported a value."""
    return _is_switch_supported(key, data.get("supported_sensors")) and key in data


def _should_remove_switch(key: str, data: dict[str, Any]) -> bool:
    """Remove a switch if hardware support says so; a missing key alone isn't enough.

    Note: this intentionally differs from `_should_create_switch` - once a
    `supported_sensors` list is available, a single update where `key` is
    transiently absent should not remove an already-created switch (it can have a
    None/False value while still supported). Older firmware without a
    `supported_sensors` list falls back to removing on a missing key.
    """
    supported_sensors = data.get("supported_sensors")
    if supported_sensors is not None:
        return not _is_switch_supported(key, supported_sensors)
    return key not in data


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_setup_dynamic_entities(
        hass,
        entry,
        entry.runtime_data.coordinator,
        async_add_entities,
        domain="switch",
        dynamic_descriptions=DYNAMIC_SWITCH_DESCRIPTIONS,
        should_create=_should_create_switch,
        should_remove=_should_remove_switch,
    )
