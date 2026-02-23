"""Light level sensor for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import LIGHT_LUX

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="light_level",
        translation_key="light_level",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        has_entity_name=True,
        icon="mdi:brightness-6",
    ),
)


class JaamHALightLevelSensor(SensorEntity, JaamHAEntity):
    """Light level sensor class."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
