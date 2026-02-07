"""Home air alert binary sensor for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="home_air_alert",
        translation_key="home_air_alert",
        device_class=BinarySensorDeviceClass.SAFETY,
        icon="mdi:alarm-light",
        has_entity_name=True,
    ),
)


class JaamHAHomeAirAlertSensor(BinarySensorEntity, JaamHAEntity):
    """Home air alert binary sensor for jaam_ha."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if air alert is active in home region."""
        home_alert_flags = self.coordinator.data.get("home_alert_flags")
        # Check if bit 0 (air alert) is set
        if home_alert_flags is not None and home_alert_flags > 0:
            return bool(home_alert_flags & (1 << 0))
        return False

    @property
    def icon(self) -> str:
        """Return the icon based on air alert state."""
        if self.is_on:
            return "mdi:alarm-light"
        return "mdi:home-circle-outline"

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None]:
        """Return additional state attributes."""
        home_alert_flags = self.coordinator.data.get("home_alert_flags")
        home_region = self.coordinator.data.get("home_region")
        return {
            "alert_flags": home_alert_flags,
            "home_region": home_region,
            "air_alert_active": self.is_on,
        }
