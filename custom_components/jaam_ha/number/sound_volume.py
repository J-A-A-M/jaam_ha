"""jaam_touch UI sound volume number for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="sound_volume_day",
        translation_key="sound_volume_day",
        icon="mdi:volume-high",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        has_entity_name=True,
    ),
    NumberEntityDescription(
        key="sound_volume_night",
        translation_key="sound_volume_night",
        icon="mdi:volume-medium",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        has_entity_name=True,
    ),
)


class JaamHASoundVolumeNumber(NumberEntity, JaamHAEntity):
    """jaam_touch UI sound volume number entity (0-100%, matches the device's own scale).

    One class for both keys: `sound_volume_day` and `sound_volume_night`.
    """

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> float | None:
        """Return the current volume percentage."""
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        """Set the volume percentage."""
        client = self.coordinator.config_entry.runtime_data.client
        if self.entity_description.key == "sound_volume_night":
            await client.async_set_sound_volume_night(int(value))
        else:
            await client.async_set_sound_volume_day(int(value))
        await self.coordinator.async_request_refresh()
