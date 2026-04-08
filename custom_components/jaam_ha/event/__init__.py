"""Event platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.jaam_ha.const import LOGGER, PARALLEL_UPDATES as PARALLEL_UPDATES
from homeassistant.components.event import EventEntityDescription
from homeassistant.helpers import entity_registry as er

from .button_events import ENTITY_DESCRIPTIONS as BUTTON_EVENTS_DESCRIPTIONS, JaamHAButtonEventsEntity

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


# Combine all entity descriptions from different modules
ENTITY_DESCRIPTIONS: tuple[EventEntityDescription, ...] = (*BUTTON_EVENTS_DESCRIPTIONS,)

# Dynamic event entity descriptions (created/removed based on supported_sensors)
DYNAMIC_EVENT_DESCRIPTIONS = {
    **{desc.key: (desc, JaamHAButtonEventsEntity) for desc in BUTTON_EVENTS_DESCRIPTIONS},
}


def _is_event_supported(event_key: str, supported_sensors: list[str] | None) -> bool:
    """
    Check if an event entity is supported by the device hardware.

    Args:
        event_key: The entity description key (e.g., "button_events")
        supported_sensors: List of supported sensors from device

    Returns:
        True if supported, False otherwise
    """
    # If no supported_sensors list, assume not supported (default: no events)
    if supported_sensors is None:
        return False

    # Check if button_events is in supported_sensors
    if event_key == "button_events" and "button_events" in supported_sensors:
        return True

    return False


def _remove_unsupported_events(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    data: dict[str, Any],
) -> None:
    """Remove event entities from registry that are no longer supported by hardware."""
    supported_sensors = data.get("supported_sensors")
    entity_registry = er.async_get(hass)
    chip_id = data.get("chip_id") or entry.entry_id

    # Determine which events to remove
    events_to_remove: set[str] = set()

    for key in DYNAMIC_EVENT_DESCRIPTIONS:
        if not _is_event_supported(key, supported_sensors):
            events_to_remove.add(key)

    if not events_to_remove:
        return

    removed_count = 0
    for key in events_to_remove:
        # Try both possible unique_id formats
        unique_id_with_chip = f"jaam_{chip_id}_{key}"
        unique_id_fallback = f"{entry.entry_id}_{key}"

        entity_id = entity_registry.async_get_entity_id("event", "jaam_ha", unique_id_with_chip)
        if not entity_id:
            entity_id = entity_registry.async_get_entity_id("event", "jaam_ha", unique_id_fallback)

        if entity_id:
            LOGGER.info("Removing event entity %s - not supported by device hardware", entity_id)
            entity_registry.async_remove(entity_id)
            removed_count += 1

    if removed_count > 0:
        LOGGER.info("Removed %d unsupported event entit(y/ies) from device", removed_count)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the event platform."""
    coordinator = entry.runtime_data.coordinator

    # Track which dynamic events have been created (by entity_description.key)
    created_events: set[str] = set()

    # Add initial dynamic events if supported by hardware
    data = coordinator.data or {}
    supported_sensors = data.get("supported_sensors")
    initial_entities = []

    for key, (entity_description, entity_class) in DYNAMIC_EVENT_DESCRIPTIONS.items():
        if _is_event_supported(key, supported_sensors):
            initial_entities.append(entity_class(coordinator=coordinator, entity_description=entity_description))
            created_events.add(key)
            LOGGER.info("Adding event entity: %s (button events supported)", key)

    if initial_entities:
        async_add_entities(initial_entities)

    # Remove event entities that are no longer supported by hardware
    _remove_unsupported_events(hass, entry, data)

    # Listener to dynamically add/remove events based on hardware support
    def _check_and_add_events() -> None:
        """Check coordinator data and add new events if supported, remove unsupported."""
        data = coordinator.data or {}
        supported_sensors = data.get("supported_sensors")
        new_entities = []

        # Add new events if supported
        for key, (entity_description, entity_class) in DYNAMIC_EVENT_DESCRIPTIONS.items():
            if key in created_events:
                continue

            if _is_event_supported(key, supported_sensors):
                new_entities.append(entity_class(coordinator=coordinator, entity_description=entity_description))
                created_events.add(key)
                LOGGER.info("Dynamically adding new event entity: %s", key)

        if new_entities:
            async_add_entities(new_entities)

        # Remove events that became unsupported
        entity_registry = er.async_get(hass)
        chip_id = data.get("chip_id") or entry.entry_id

        for key in list(created_events):  # Use list() to avoid RuntimeError during iteration
            if not _is_event_supported(key, supported_sensors):
                # Try both possible unique_id formats
                unique_id_with_chip = f"jaam_{chip_id}_{key}"
                unique_id_fallback = f"{entry.entry_id}_{key}"

                entity_id = entity_registry.async_get_entity_id("event", "jaam_ha", unique_id_with_chip)
                if not entity_id:
                    entity_id = entity_registry.async_get_entity_id("event", "jaam_ha", unique_id_fallback)

                if entity_id:
                    LOGGER.info("Removing event entity %s - no longer supported", entity_id)
                    entity_registry.async_remove(entity_id)
                    created_events.discard(key)

    # Register listener to be called on every coordinator update
    entry.async_on_unload(coordinator.async_add_listener(_check_and_add_events))
