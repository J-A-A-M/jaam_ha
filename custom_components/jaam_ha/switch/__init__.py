"""Switch platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.jaam_ha.const import LOGGER, PARALLEL_UPDATES as PARALLEL_UPDATES, SUPPORTED_SWITCH_MAPPING
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.helpers import entity_registry as er

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


def _remove_unsupported_switches(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    data: dict[str, Any],
) -> None:
    """Remove switches from registry that are no longer supported by hardware."""
    supported_sensors = data.get("supported_sensors")
    entity_registry = er.async_get(hass)
    chip_id = data.get("chip_id") or entry.entry_id

    # Determine which switches to remove
    switches_to_remove: set[str] = set()

    if supported_sensors is not None:
        # Use explicit supported_sensors list from device
        for key in DYNAMIC_SWITCH_DESCRIPTIONS:
            if not _is_switch_supported(key, supported_sensors):
                switches_to_remove.add(key)
    else:
        # Fallback: Remove switches where field is not present in data (not supported)
        # Note: Switch can have None/False value if supported but disabled
        for key in DYNAMIC_SWITCH_DESCRIPTIONS:
            if key not in data:
                switches_to_remove.add(key)

    if not switches_to_remove:
        return

    removed_count = 0
    for key in switches_to_remove:
        # Try both possible unique_id formats
        unique_id_with_chip = f"jaam_{chip_id}_{key}"
        unique_id_fallback = f"{entry.entry_id}_{key}"

        entity_id = entity_registry.async_get_entity_id("switch", "jaam_ha", unique_id_with_chip)
        if not entity_id:
            entity_id = entity_registry.async_get_entity_id("switch", "jaam_ha", unique_id_fallback)

        if entity_id:
            LOGGER.info("Removing switch %s - not supported by device hardware", entity_id)
            entity_registry.async_remove(entity_id)
            removed_count += 1

    if removed_count > 0:
        LOGGER.info("Removed %d unsupported switch(es) from device", removed_count)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator = entry.runtime_data.coordinator

    # Track which dynamic switches have been created (by entity_description.key)
    created_switches: set[str] = set()

    # Add initial dynamic switches if supported by hardware
    data = coordinator.data or {}
    supported_sensors = data.get("supported_sensors")
    initial_entities = []

    for key, (entity_description, entity_class) in DYNAMIC_SWITCH_DESCRIPTIONS.items():
        if _is_switch_supported(key, supported_sensors) and key in data:
            initial_entities.append(entity_class(coordinator=coordinator, entity_description=entity_description))
            created_switches.add(key)

    if initial_entities:
        async_add_entities(initial_entities)

    # Remove switches that are no longer supported by hardware
    _remove_unsupported_switches(hass, entry, data)

    # Listener to dynamically add/remove switches based on hardware support
    def _check_and_add_switches() -> None:
        """Check coordinator data and add new switches if available and supported, remove unsupported."""
        data = coordinator.data or {}
        supported_sensors = data.get("supported_sensors")
        new_entities = []

        # Add new switches if supported
        for key, (entity_description, entity_class) in DYNAMIC_SWITCH_DESCRIPTIONS.items():
            if key in created_switches:
                continue

            if _is_switch_supported(key, supported_sensors) and key in data:
                new_entities.append(entity_class(coordinator=coordinator, entity_description=entity_description))
                created_switches.add(key)
                LOGGER.info("Dynamically adding new switch: %s with value %s", key, data[key])

        if new_entities:
            async_add_entities(new_entities)

        # Remove switches that became unsupported
        entity_registry = er.async_get(hass)
        chip_id = data.get("chip_id") or entry.entry_id

        for key in list(created_switches):  # Use list() to avoid RuntimeError during iteration
            should_remove = False

            if supported_sensors is not None:
                # Use explicit supported_sensors list
                if not _is_switch_supported(key, supported_sensors):
                    should_remove = True
            elif key not in data:
                # Fallback: Remove if field is not present in data (not supported)
                should_remove = True

            if should_remove:
                # Try both possible unique_id formats
                unique_id_with_chip = f"jaam_{chip_id}_{key}"
                unique_id_fallback = f"{entry.entry_id}_{key}"

                entity_id = entity_registry.async_get_entity_id("switch", "jaam_ha", unique_id_with_chip)
                if not entity_id:
                    entity_id = entity_registry.async_get_entity_id("switch", "jaam_ha", unique_id_fallback)

                if entity_id:
                    LOGGER.info("Dynamically removing switch %s - no longer supported", entity_id)
                    entity_registry.async_remove(entity_id)
                    created_switches.discard(key)

    # Register listener to be called on every coordinator update
    entry.async_on_unload(coordinator.async_add_listener(_check_and_add_switches))
