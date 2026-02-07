"""Home danger sensor for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


# Alert types mapped to bit positions (bitmask)
ALERT_TYPES: dict[int, str] = {
    0: "air",  # Біт 0: повітряна тривога
    1: "artillery",  # Біт 1: артилерія
    2: "urban",  # Біт 2: міські бої
    3: "chemical",  # Біт 3: хімічна загроза
    4: "nuclear",  # Біт 4: ядерна загроза
    5: "drones",  # Біт 5: дрони (БПЛА)
    6: "missiles",  # Біт 6: ракети
    7: "kab",  # Біт 7: КАБи (керовані авіабомби)
    8: "ballistic",  # Біт 8: балістичні ракети
    9: "explosion",  # Біт 9: вибух
    10: "recon",  # Біт 10: розвідувальні дрони
}

# Icon mapping for alert types (priority order - highest to lowest)
ALERT_ICONS: dict[str, str] = {
    "nuclear": "mdi:radioactive",
    "ballistic": "mdi:rocket-launch",
    "missiles": "mdi:rocket-launch-outline",
    "explosion": "mdi:explosion",
    "chemical": "mdi:flask",
    "kab": "mdi:bomb",
    "drones": "mdi:quadcopter",
    "artillery": "mdi:cannon",
    "urban": "mdi:city",
    "recon": "mdi:eye-circle-outline",
    "air": "mdi:alarm-light",
}


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="home_alert_flags",
        translation_key="home_danger",
        has_entity_name=True,
    ),
)


class JaamHAHomeDangerSensor(SensorEntity, JaamHAEntity):
    """Home danger sensor class."""

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
        alert_flags = self.coordinator.data.get("home_alert_flags")
        if alert_flags is None:
            return None

        # No alert (-1 or 0)
        if alert_flags < 0:
            return "no_alert"

        # Parse bitmask and get active alerts
        active_alerts = self._get_active_alerts(alert_flags)

        if not active_alerts:
            return "no_alert"

        # Return comma-separated list of active alert translation keys
        return ", ".join(active_alerts)

    @property
    def icon(self) -> str:
        """Return dynamic icon based on active alerts (highest priority)."""
        alert_flags = self.coordinator.data.get("home_alert_flags")

        if alert_flags is None or alert_flags < 0:
            return "mdi:check-circle"

        active_alerts = self._get_active_alerts(alert_flags)
        if not active_alerts:
            return "mdi:check-circle"

        # Return icon for highest priority alert (first match in ALERT_ICONS dict)
        for alert_type, icon in ALERT_ICONS.items():
            if alert_type in active_alerts:
                return icon

        return "mdi:alert"

    @property
    def extra_state_attributes(self) -> dict[str, int | dict[str, bool]]:
        """Return additional state attributes."""
        alert_flags = self.coordinator.data.get("home_alert_flags")

        if alert_flags is None:
            return {}

        attributes: dict[str, int | dict[str, bool]] = {
            "alert_flags": alert_flags,
        }

        # Add individual alert states as boolean flags
        if alert_flags >= 0:
            alert_states: dict[str, bool] = {}
            for bit_pos, alert_type in ALERT_TYPES.items():
                alert_states[alert_type] = bool(alert_flags & (1 << bit_pos))
            attributes["alerts"] = alert_states

        return attributes

    def _get_active_alerts(self, alert_flags: int) -> list[str]:
        """Parse bitmask and return list of active alert types."""
        active_alerts: list[str] = []

        for bit_pos, alert_type in ALERT_TYPES.items():
            if alert_flags & (1 << bit_pos):
                active_alerts.append(alert_type)

        return active_alerts
