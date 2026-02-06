"""Home danger binary sensor for jaam_ha."""

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
        key="home_danger",
        translation_key="home_danger",
        device_class=BinarySensorDeviceClass.SAFETY,
        icon="mdi:home-alert",
        has_entity_name=True,
    ),
)


class JaamHAHomeDangerSensor(BinarySensorEntity, JaamHAEntity):
    """Home danger binary sensor for jaam_ha."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if there is danger in home region (alert active)."""
        home_alert_bit = self.coordinator.data.get("home_alert_bit")
        # Danger when alert_bit >= 0 (any alert type)
        # Safe when alert_bit == -1 (no alert)
        if home_alert_bit is not None:
            return home_alert_bit >= 0
        return False

    @property
    def icon(self) -> str:
        """Return the icon based on danger state."""
        if self.is_on:
            return "mdi:home-alert"
        return "mdi:home-circle-outline"

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None]:
        """Return additional state attributes."""
        home_alert_bit = self.coordinator.data.get("home_alert_bit")
        home_region = self.coordinator.data.get("home_region")
        return {
            "alert_bit": home_alert_bit,
            "home_region": home_region,
        }
