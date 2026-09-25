"""Button platform for jaam_ha.

jaam_touch-only for now - jaam_fusion's WS API has no command this platform could back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import (
    CONF_DEVICE_TYPE,
    DEFAULT_DEVICE_TYPE,
    DEVICE_TYPE_TOUCH,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)

from .reboot import ENTITY_DESCRIPTIONS as REBOOT_DESCRIPTIONS, JaamHARebootButton

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    if entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE) != DEVICE_TYPE_TOUCH:
        return

    async_add_entities(
        JaamHARebootButton(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in REBOOT_DESCRIPTIONS
    )
