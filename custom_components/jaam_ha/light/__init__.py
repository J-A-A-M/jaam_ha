"""Light platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE, DEVICE_TYPE_FUSION

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
    # The lamp light is a jaam_fusion-only concept (map_mode_id == LAMP) - jaam_touch has
    # no equivalent, so this entity would just sit permanently off and send commands the
    # device doesn't understand. Not gated by supported_sensors like the dynamic platforms
    # below because fusion firmware never listed it there - it's unconditional on that
    # side, so it's gated on device_type here instead.
    if entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE) != DEVICE_TYPE_FUSION:
        return

    async_add_entities(
        JaamHALampLight(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in LAMP_DESCRIPTIONS
    )
