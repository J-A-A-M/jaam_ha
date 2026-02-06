"""Home alert sensor for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


# Alert type mapping
ALERT_TYPES: dict[int, str] = {
    -1: "no_alert",
    0: "alert",
    5: "drones",
    6: "missiles",
    7: "kabs",
    8: "ballistic",
    9: "explosion",
    10: "recon_drones",
}


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="home_alert_bit",
        translation_key="home_alert",
        icon="mdi:alert",
        has_entity_name=True,
    ),
)


class JaamHAHomeAlertSensor(SensorEntity, JaamHAEntity):
    """Home alert sensor class."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        alert_bit = self.coordinator.data.get("home_alert_bit")
        if alert_bit is not None and alert_bit in ALERT_TYPES:
            return ALERT_TYPES[alert_bit]
        return None

    @property
    def icon(self) -> str:
        """Return the icon based on alert state."""
        alert_bit = self.coordinator.data.get("home_alert_bit")

        # Map each alert type to a specific icon
        icon_map: dict[int, str] = {
            -1: "mdi:check-circle",  # No alert
            0: "mdi:alert",  # General alert
            5: "mdi:quadcopter",  # Drones
            6: "mdi:rocket-launch",  # Missiles
            7: "mdi:bomb",  # KABs
            8: "mdi:axis-arrow",  # Ballistic
            9: "mdi:explosion",  # Explosion
            10: "mdi:eye-circle-outline",  # Reconnaissance drones
        }

        if alert_bit is not None and isinstance(alert_bit, int):
            return icon_map.get(alert_bit, "mdi:alert")
        return "mdi:alert"

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Return additional state attributes."""
        alert_bit = self.coordinator.data.get("home_alert_bit")
        if alert_bit is not None:
            return {"alert_bit": alert_bit}
        return {}
