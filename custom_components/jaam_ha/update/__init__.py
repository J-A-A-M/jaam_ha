"""Update platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE, DEVICE_TYPE_FUSION

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
    # jaam_touch's TouchApi doesn't report fw_latest or handle update_firmware yet (its
    # OTA flow is still menu/beta-channel-only on-device, see jaam_touch's OtaUpdater) -
    # gate this off rather than show an update entity that can never show an update.
    if entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE) != DEVICE_TYPE_FUSION:
        return

    entities = [
        JaamHAFirmwareUpdate(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in FIRMWARE_DESCRIPTIONS
    ]

    async_add_entities(entities)
