"""Number platform for jaam_ha.

jaam_touch-only for now - jaam_fusion has no equivalent "plain numeric value" settings
exposed over its WS API (its one comparable value, lamp brightness, is part of
light.lamp's own brightness attribute, not a separate number entity).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import (
    CONF_DEVICE_TYPE,
    DEFAULT_DEVICE_TYPE,
    DEVICE_TYPE_TOUCH,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from homeassistant.components.number import NumberEntityDescription

from .brightness_day import ENTITY_DESCRIPTIONS as BRIGHTNESS_DAY_DESCRIPTIONS, JaamHABrightnessDayNumber
from .brightness_night import ENTITY_DESCRIPTIONS as BRIGHTNESS_NIGHT_DESCRIPTIONS, JaamHABrightnessNightNumber
from .sound_volume import ENTITY_DESCRIPTIONS as SOUND_VOLUME_DESCRIPTIONS, JaamHASoundVolumeNumber

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Combine all entity descriptions from different modules
ENTITY_DESCRIPTIONS: tuple[NumberEntityDescription, ...] = (
    *BRIGHTNESS_DAY_DESCRIPTIONS,
    *BRIGHTNESS_NIGHT_DESCRIPTIONS,
    *SOUND_VOLUME_DESCRIPTIONS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    if entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE) != DEVICE_TYPE_TOUCH:
        return

    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        JaamHABrightnessDayNumber(coordinator=coordinator, entity_description=entity_description)
        for entity_description in BRIGHTNESS_DAY_DESCRIPTIONS
    )
    async_add_entities(
        JaamHABrightnessNightNumber(coordinator=coordinator, entity_description=entity_description)
        for entity_description in BRIGHTNESS_NIGHT_DESCRIPTIONS
    )
    async_add_entities(
        JaamHASoundVolumeNumber(coordinator=coordinator, entity_description=entity_description)
        for entity_description in SOUND_VOLUME_DESCRIPTIONS
    )
