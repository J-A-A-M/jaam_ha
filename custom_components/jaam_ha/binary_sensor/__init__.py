"""Binary sensor platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from homeassistant.components.binary_sensor import BinarySensorEntityDescription

from .home_air_alert import ENTITY_DESCRIPTIONS as HOME_AIR_ALERT_DESCRIPTIONS, JaamHAHomeAirAlertSensor
from .websocket_status import ENTITY_DESCRIPTIONS as WEBSOCKET_STATUS_DESCRIPTIONS, JaamHAWebSocketStatusSensor

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Combine all entity descriptions from different modules
ENTITY_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    *HOME_AIR_ALERT_DESCRIPTIONS,
    *WEBSOCKET_STATUS_DESCRIPTIONS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    # Create home air alert sensors
    home_air_alert_entities = [
        JaamHAHomeAirAlertSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in HOME_AIR_ALERT_DESCRIPTIONS
    ]

    # Create websocket status sensors
    websocket_status_entities = [
        JaamHAWebSocketStatusSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in WEBSOCKET_STATUS_DESCRIPTIONS
    ]

    # Add all entities
    async_add_entities([*home_air_alert_entities, *websocket_status_entities])
