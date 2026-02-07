"""System info sensors for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfInformation, UnitOfTime

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="used_memory",
        translation_key="used_memory",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_entity_name=True,
        icon="mdi:memory",
    ),
    SensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        has_entity_name=True,
        icon="mdi:timer-outline",
    ),
    SensorEntityDescription(
        key="wifi_uptime",
        translation_key="wifi_uptime",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        has_entity_name=True,
        icon="mdi:router-wireless",
    ),
    SensorEntityDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        has_entity_name=True,
        icon="mdi:wifi",
    ),
    SensorEntityDescription(
        key="websocket_uptime",
        translation_key="websocket_uptime",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        has_entity_name=True,
        icon="mdi:lan-connect",
    ),
)


class JaamHASystemInfoSensor(SensorEntity, JaamHAEntity):
    """System info sensor class."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None

        return value
