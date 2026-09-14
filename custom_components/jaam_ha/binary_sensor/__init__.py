"""Binary sensor platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.jaam_ha.const import DOMAIN, PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.jaam_ha.entity import async_setup_dynamic_entities
from custom_components.jaam_ha.update.firmware import JaamHAFirmwareUpdate
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.helpers import issue_registry as ir

from .home_alerts import (
    ENTITY_DESCRIPTIONS as HOME_ALERTS_DESCRIPTIONS,
    MIN_FW_VERSION_ALERT_LEVELS,
    JaamHAHomeAlertSensor,
)
from .websocket_status import ENTITY_DESCRIPTIONS as WEBSOCKET_STATUS_DESCRIPTIONS, JaamHAWebSocketStatusSensor

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Combine all entity descriptions from different modules
ENTITY_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    *HOME_ALERTS_DESCRIPTIONS,
    *WEBSOCKET_STATUS_DESCRIPTIONS,
)

# Home alert descriptions gated behind a minimum firmware version (e.g. yellow/red alert level)
DYNAMIC_ALERT_DESCRIPTIONS = {
    desc.key: (desc, JaamHAHomeAlertSensor)
    for desc in HOME_ALERTS_DESCRIPTIONS
    if desc.key.removeprefix("home_alert_") in MIN_FW_VERSION_ALERT_LEVELS
}

# Home alert descriptions that are always created regardless of firmware version
STATIC_ALERT_DESCRIPTIONS = tuple(
    desc for desc in HOME_ALERTS_DESCRIPTIONS if desc.key not in DYNAMIC_ALERT_DESCRIPTIONS
)


def _is_alert_fw_supported(key: str, data: dict[str, Any]) -> bool:
    """Check if a version-gated alert sensor is supported by the installed firmware."""
    alert_type = key.removeprefix("home_alert_")
    min_version = MIN_FW_VERSION_ALERT_LEVELS.get(alert_type)

    # Not a version-gated alert type - always supported
    if min_version is None:
        return True

    fw_version = data.get("fw_version")
    # Firmware version not yet known - wait for coordinator data before creating the entity
    if fw_version is None:
        return False

    # Reuse the update entity's version ordering, which knows that a release beats any
    # beta of the same X.Y.Z (a naive tuple/string comparison would get that backwards),
    # and falls back to treating an unparseable fw_version as unsupported (fail closed).
    return not JaamHAFirmwareUpdate.version_is_newer(min_version, fw_version)


def _deprecated_air_alert_issue_id(entry: JaamHAConfigEntry) -> str:
    """Scope the repair issue per config entry so multiple JAAM devices don't interfere."""
    return f"deprecated_air_alert_sensor_{entry.entry_id}"


def _sync_deprecated_air_alert_issue(hass: HomeAssistant, entry: JaamHAConfigEntry, data: dict[str, Any]) -> None:
    """Create/clear the repair notice for the deprecated Air Alert sensor.

    Only relevant once the firmware actually exposes the replacement sensors (yellow/red
    alert level) - telling users to migrate to sensors their firmware doesn't have yet
    would be actively unhelpful, so the notice tracks the same support check as those
    sensors and disappears again if a device is ever downgraded.
    """
    issue_id = _deprecated_air_alert_issue_id(entry)

    if _is_alert_fw_supported("home_alert_yellow", data):
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_air_alert_sensor",
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = entry.runtime_data.coordinator

    # Create home alert sensors that are always available
    home_alert_entities = [
        JaamHAHomeAlertSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in STATIC_ALERT_DESCRIPTIONS
    ]

    # Create websocket status sensors
    websocket_status_entities = [
        JaamHAWebSocketStatusSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in WEBSOCKET_STATUS_DESCRIPTIONS
    ]

    async_add_entities([*home_alert_entities, *websocket_status_entities])

    async_setup_dynamic_entities(
        hass,
        entry,
        coordinator,
        async_add_entities,
        domain="binary_sensor",
        dynamic_descriptions=DYNAMIC_ALERT_DESCRIPTIONS,
        should_create=_is_alert_fw_supported,
    )

    # Keep the deprecated-sensor repair notice in sync with firmware support, and clean
    # it up if this config entry (device) is ever removed.
    def _check_deprecated_air_alert_issue() -> None:
        _sync_deprecated_air_alert_issue(hass, entry, coordinator.data or {})

    def _clear_deprecated_air_alert_issue() -> None:
        ir.async_delete_issue(hass, DOMAIN, _deprecated_air_alert_issue_id(entry))

    _check_deprecated_air_alert_issue()
    entry.async_on_unload(coordinator.async_add_listener(_check_deprecated_air_alert_issue))
    entry.async_on_unload(_clear_deprecated_air_alert_issue)
