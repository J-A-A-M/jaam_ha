"""Light platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .lamp import ENTITY_DESCRIPTIONS as LAMP_DESCRIPTIONS, JaamHALampLight

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    async_add_entities(
        JaamHALampLight(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in LAMP_DESCRIPTIONS
    )
