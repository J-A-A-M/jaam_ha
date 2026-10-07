"""jaam_touch screen brightness numbers (day and night range) for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="brightness_day",
        translation_key="brightness_day",
        icon="mdi:brightness-6",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        has_entity_name=True,
    ),
    NumberEntityDescription(
        key="brightness_night",
        translation_key="brightness_night",
        icon="mdi:brightness-3",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        has_entity_name=True,
    ),
)


class JaamHABrightnessNumber(NumberEntity, JaamHAEntity):
    """jaam_touch brightness number entity.

    One class for both keys: `brightness_day` and `brightness_night`. Exposed as 0-100%
    (friendlier than the device's own 0-255 raw scale, same conversion jaam_ha's
    light.lamp already applies to its brightness).
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
        """Return the current brightness as a percentage."""
        level = self.coordinator.data.get(self.entity_description.key)
        if level is None:
            return None
        return round((level / 255) * 100)

    async def async_set_native_value(self, value: float) -> None:
        """Set the brightness from a percentage."""
        level = round((value / 100) * 255)
        client = self.coordinator.config_entry.runtime_data.client
        if self.entity_description.key == "brightness_night":
            await client.async_set_brightness_night(level)
        else:
            await client.async_set_brightness_day(level)
        await self.coordinator.async_request_refresh()
