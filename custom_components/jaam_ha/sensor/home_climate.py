"""Room climate sensors for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfPressure, UnitOfTemperature

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="climate_temp",
        translation_key="climate_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        has_entity_name=True,
        icon="mdi:thermometer",
    ),
    SensorEntityDescription(
        key="climate_humidity",
        translation_key="climate_humidity",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        has_entity_name=True,
        icon="mdi:water-percent",
    ),
    SensorEntityDescription(
        key="climate_pressure",
        translation_key="climate_pressure",
        native_unit_of_measurement=UnitOfPressure.MMHG,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        has_entity_name=True,
        icon="mdi:gauge",
    ),
)


class JaamHAHomeClimateSensor(SensorEntity, JaamHAEntity):
    """Room climate sensor class."""

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
