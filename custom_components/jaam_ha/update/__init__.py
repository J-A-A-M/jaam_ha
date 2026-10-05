"""Update platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .firmware import ENTITY_DESCRIPTIONS as FIRMWARE_DESCRIPTIONS, JaamHAFirmwareUpdate

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the update platform."""
    entities = [
        JaamHAFirmwareUpdate(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in FIRMWARE_DESCRIPTIONS
    ]

    async_add_entities(entities)
