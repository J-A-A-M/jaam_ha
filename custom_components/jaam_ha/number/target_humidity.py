"""Target humidity number for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.api import JaamHAApiClientError
from custom_components.jaam_ha.const import LOGGER
from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="target_humidity",
        translation_key="target_humidity",
        icon="mdi:water-percent",
        device_class=NumberDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=30,
        native_max_value=80,
        native_step=5,
        mode=NumberMode.SLIDER,
        has_entity_name=True,
    ),
)


class JaamHAHumidityNumber(NumberEntity, JaamHAEntity):
    """Target humidity number class."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entity_description)
        # Default target humidity
        self._attr_native_value: float = 50.0

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set new target humidity."""
        try:
            # In production: Call API to set target humidity
            # await self.coordinator.config_entry.runtime_data.client.async_set_target_humidity(int(value))

            self._attr_native_value = value
            self.async_write_ha_state()
            LOGGER.debug("Target humidity set to %s%%", value)
        except JaamHAApiClientError as exception:
            LOGGER.exception("Failed to set target humidity")
            raise HomeAssistantError(
                translation_domain="jaam_ha",
                translation_key="number_set_failed",
            ) from exception
