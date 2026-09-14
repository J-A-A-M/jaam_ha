"""Home alerts binary sensors for jaam_ha."""

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

# Alert types mapped to bit positions (bitmask)
ALERT_TYPES: dict[int, str] = {
    0: "air",  # Біт 0: повітряна тривога (Deprecated, замінено бітами 11/12 з 5.1)
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
    11: "yellow",  # Біт 11: жовтий рівень тривоги (прошивка 5.1+)
    12: "red",  # Біт 12: червоний рівень тривоги (прошивка 5.1+)
}

# Icon mapping for alert types
ALERT_ICONS: dict[str, str] = {
    "air": "mdi:alarm-light-outline",
    "artillery": "mdi:cannon",
    "urban": "mdi:city",
    "chemical": "mdi:flask",
    "nuclear": "mdi:radioactive",
    "drones": "mdi:quadcopter",
    "missiles": "mdi:rocket-launch-outline",
    "kab": "mdi:bomb",
    "ballistic": "mdi:rocket-launch",
    "explosion": "mdi:explosion",
    "recon": "mdi:eye-circle-outline",
    "yellow": "mdi:alert",
    "red": "mdi:alarm-light",
}

# Alert types that require a minimum firmware version (major, minor, patch, beta).
# Bits 11/12 (yellow/red alert level) were introduced in firmware 5.1 — see
# AlertModes::ALERT_LOW / AlertModes::ALERT in jaam_fusion's JaamConfig.h.
MIN_FW_VERSION_ALERT_LEVELS: dict[str, tuple[int, int, int, int]] = {
    "yellow": (5, 1, 0, 0),
    "red": (5, 1, 0, 0),
}

# Safe icon (when alert is not active)
SAFE_ICON = "mdi:shield-check-outline"

ENTITY_DESCRIPTIONS = tuple(
    BinarySensorEntityDescription(
        key=f"home_alert_{alert_type}",
        translation_key=f"home_alert_{alert_type}",
        device_class=BinarySensorDeviceClass.SAFETY,
        icon=ALERT_ICONS.get(alert_type, "mdi:alert"),
        has_entity_name=True,
    )
    for bit_position, alert_type in ALERT_TYPES.items()
)


class JaamHAHomeAlertSensor(BinarySensorEntity, JaamHAEntity):
    """Home alert binary sensor for jaam_ha."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

        # Extract alert type from key (home_alert_air -> air)
        self._alert_type = entity_description.key.replace("home_alert_", "")

        # Find bit position for this alert type
        self._bit_position = next(
            (bit for bit, alert in ALERT_TYPES.items() if alert == self._alert_type),
            None,
        )

    @property
    def is_on(self) -> bool:
        """Return true if this alert is active in home region."""
        if self._bit_position is None:
            return False

        home_alert_flags = self.coordinator.data.get("home_alert_flags")

        # Check if the specific bit for this alert type is set
        if home_alert_flags is not None and home_alert_flags > 0:
            return bool(home_alert_flags & (1 << self._bit_position))
        return False

    @property
    def icon(self) -> str:
        """Return the icon based on alert state."""
        if self.is_on:
            return ALERT_ICONS.get(self._alert_type, "mdi:alert")
        return SAFE_ICON

    @property
    def extra_state_attributes(self) -> dict[str, int | str | bool | None]:
        """Return additional state attributes."""
        home_alert_flags = self.coordinator.data.get("home_alert_flags")
        home_region = self.coordinator.data.get("home_region")
        return {
            "alert_type": self._alert_type,
            "bit_position": self._bit_position,
            "alert_flags": home_alert_flags,
            "home_region": home_region,
            "alert_active": self.is_on,
        }
