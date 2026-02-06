"""WebSocket status binary sensor for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="websocket_status",
        translation_key="websocket_status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
    ),
)


class JaamHAWebSocketStatusSensor(BinarySensorEntity, JaamHAEntity):
    """WebSocket status binary sensor for jaam_ha."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if WebSocket connection is active."""
        websocket_status = self.coordinator.data.get("websocket_status")
        if websocket_status is not None:
            return bool(websocket_status)
        return False

    @property
    def icon(self) -> str:
        """Return the icon based on connection status."""
        if self.is_on:
            return "mdi:lan-connect"
        return "mdi:lan-disconnect"

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Return additional state attributes."""
        websocket_uptime = self.coordinator.data.get("websocket_uptime")
        return {
            "uptime": websocket_uptime,
        }
