"""Shared helper for platforms whose entities are gated by a runtime support check.

Used by the switch, sensor, and binary_sensor platforms to create entities only when
supported by the current device data (hardware capability or firmware version), and to
add/remove them dynamically as that support changes at runtime - without requiring the
user to remove and re-add the integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

from custom_components.jaam_ha.const import LOGGER
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import Entity, EntityDescription
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_EntityT = TypeVar("_EntityT", bound="Entity")

SupportCheck = Callable[[str, dict[str, Any]], bool]


def find_dynamic_entity_id(
    entity_registry: er.EntityRegistry,
    domain: str,
    chip_id: str,
    entry_id: str,
    key: str,
) -> str | None:
    """Look up an entity_id for `key`, trying both possible unique_id formats."""
    unique_id_with_chip = f"jaam_{chip_id}_{key}"
    unique_id_fallback = f"{entry_id}_{key}"

    return entity_registry.async_get_entity_id(domain, "jaam_ha", unique_id_with_chip) or (
        entity_registry.async_get_entity_id(domain, "jaam_ha", unique_id_fallback)
    )


def async_setup_dynamic_entities(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    coordinator: JaamHADataUpdateCoordinator,
    async_add_entities: AddEntitiesCallback,
    *,
    domain: str,
    dynamic_descriptions: dict[str, tuple[EntityDescription, type[_EntityT]]],
    should_create: SupportCheck,
    should_remove: SupportCheck | None = None,
) -> None:
    """Create capability-gated entities now, and add/remove them as support changes.

    `should_create(key, data)` decides, from the current coordinator data, whether the
    entity for `key` should exist. `should_remove(key, data)` decides whether an already
    created entity should be removed from the registry; it defaults to
    `not should_create(key, data)` but can be given separately (e.g. to avoid removing an
    entity just because one field is transiently missing from a single update, while still
    requiring that field to be present before creating it in the first place).

    Registers a coordinator listener so entities keep appearing/disappearing automatically
    on every future update, matching hardware or firmware support as it changes.
    """
    def _default_should_remove(key: str, data: dict[str, Any]) -> bool:
        return not should_create(key, data)

    if should_remove is None:
        should_remove = _default_should_remove

    created_keys: set[str] = set()

    def _add_supported(data: dict[str, Any]) -> None:
        new_entities = [
            entity_class(coordinator=coordinator, entity_description=entity_description)
            for key, (entity_description, entity_class) in dynamic_descriptions.items()
            if key not in created_keys and should_create(key, data)
        ]
        for entity in new_entities:
            created_keys.add(entity.entity_description.key)
            LOGGER.info("Dynamically adding new %s entity: %s", domain, entity.entity_description.key)

        if new_entities:
            async_add_entities(new_entities)

    def _remove_unsupported(data: dict[str, Any]) -> None:
        entity_registry = er.async_get(hass)
        chip_id = data.get("chip_id") or entry.entry_id

        for key in list(created_keys):  # Use list() to avoid RuntimeError during iteration
            if not should_remove(key, data):
                continue

            entity_id = find_dynamic_entity_id(entity_registry, domain, chip_id, entry.entry_id, key)
            if entity_id:
                LOGGER.info("Removing %s entity %s - no longer supported", domain, entity_id)
                entity_registry.async_remove(entity_id)
                created_keys.discard(key)

    initial_data = coordinator.data or {}
    _add_supported(initial_data)
    _remove_unsupported(initial_data)

    def _check_dynamic_entities() -> None:
        """Re-evaluate support on every coordinator update."""
        data = coordinator.data or {}
        _add_supported(data)
        _remove_unsupported(data)

    entry.async_on_unload(coordinator.async_add_listener(_check_dynamic_entities))
