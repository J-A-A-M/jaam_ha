"""jaam_touch battery/wifi diagnostic sensors for jaam_ha.

Mirrors system_info.py's shape (several always-present-once-connected diagnostic
values, one generic class reading entity_description.key straight off coordinator
data) - jaam_fusion's system_info sensors don't apply to jaam_touch (different fields
entirely, see sensor/__init__.py's device_type gating), so this is its own module
rather than an extension of that one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTime,
)

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery_percent",
        translation_key="battery_percent",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        has_entity_name=True,
    ),
    SensorEntityDescription(
        key="battery_voltage_mv",
        translation_key="battery_voltage_mv",
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
        icon="mdi:battery-heart-variant",
    ),
    SensorEntityDescription(
        key="battery_runtime_hours",
        translation_key="battery_runtime_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
        icon="mdi:battery-clock",
    ),
    # Reuses the "wifi_signal" translation key jaam_fusion's own system_info sensor
    # already defines - same meaning (WiFi RSSI, dBm), never created for the same
    # config entry as that one (device_type gating in sensor/__init__.py), so there's
    # no ambiguity in reusing it.
    SensorEntityDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
        icon="mdi:wifi",
    ),
)


class JaamHATouchStatusSensor(SensorEntity, JaamHAEntity):
    """jaam_touch battery/wifi diagnostic sensor class."""

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
        return self.coordinator.data.get(self.entity_description.key)
