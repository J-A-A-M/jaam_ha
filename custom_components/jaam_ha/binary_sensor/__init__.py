"""Binary sensor platform for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.jaam_ha.const import LOGGER, PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.jaam_ha.update.firmware import JaamHAFirmwareUpdate
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.helpers import entity_registry as er

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
VERSION_GATED_ALERT_DESCRIPTIONS = {
    desc.key: desc
    for desc in HOME_ALERTS_DESCRIPTIONS
    if desc.key.removeprefix("home_alert_") in MIN_FW_VERSION_ALERT_LEVELS
}

# Home alert descriptions that are always created regardless of firmware version
STATIC_ALERT_DESCRIPTIONS = tuple(
    desc for desc in HOME_ALERTS_DESCRIPTIONS if desc.key not in VERSION_GATED_ALERT_DESCRIPTIONS
)


def _is_alert_fw_supported(key: str, fw_version: str | None) -> bool:
    """Check if a version-gated alert sensor is supported by the installed firmware."""
    alert_type = key.removeprefix("home_alert_")
    min_version = MIN_FW_VERSION_ALERT_LEVELS.get(alert_type)

    # Not a version-gated alert type - always supported
    if min_version is None:
        return True

    # Firmware version not yet known - wait for coordinator data before creating the entity
    if fw_version is None:
        return False

    # Reuse the update entity's version ordering, which knows that a release beats any
    # beta of the same X.Y.Z (a naive tuple/string comparison would get that backwards),
    # and falls back to treating an unparseable fw_version as unsupported (fail closed).
    return not JaamHAFirmwareUpdate.version_is_newer(min_version, fw_version)


def _find_alert_entity_id(
    entity_registry: er.EntityRegistry,
    chip_id: str,
    entry_id: str,
    key: str,
) -> str | None:
    """Look up a home alert sensor's entity_id, trying both possible unique_id formats."""
    unique_id_with_chip = f"jaam_{chip_id}_{key}"
    unique_id_fallback = f"{entry_id}_{key}"

    return entity_registry.async_get_entity_id(
        "binary_sensor", "jaam_ha", unique_id_with_chip
    ) or entity_registry.async_get_entity_id("binary_sensor", "jaam_ha", unique_id_fallback)


def _remove_unsupported_alerts(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    data: dict[str, Any],
) -> None:
    """Remove version-gated alert sensors from the registry if the firmware no longer supports them."""
    fw_version = data.get("fw_version")
    entity_registry = er.async_get(hass)
    chip_id = data.get("chip_id") or entry.entry_id

    for key in VERSION_GATED_ALERT_DESCRIPTIONS:
        if _is_alert_fw_supported(key, fw_version):
            continue

        entity_id = _find_alert_entity_id(entity_registry, chip_id, entry.entry_id, key)
        if entity_id:
            LOGGER.info("Removing alert sensor %s - not supported by firmware version %s", entity_id, fw_version)
            entity_registry.async_remove(entity_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = entry.runtime_data.coordinator

    # Track which version-gated alert sensors have been created (by entity_description.key)
    created_alert_keys: set[str] = set()

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

    # Add initial version-gated alert sensors if the current firmware supports them
    data = coordinator.data or {}
    fw_version = data.get("fw_version")
    for key, entity_description in VERSION_GATED_ALERT_DESCRIPTIONS.items():
        if _is_alert_fw_supported(key, fw_version):
            home_alert_entities.append(
                JaamHAHomeAlertSensor(coordinator=coordinator, entity_description=entity_description)
            )
            created_alert_keys.add(key)

    # Add all entities
    async_add_entities([*home_alert_entities, *websocket_status_entities])

    # Remove version-gated alert sensors that are not supported by the current firmware
    _remove_unsupported_alerts(hass, entry, data)

    # Listener to dynamically add/remove version-gated alert sensors after firmware updates
    def _check_and_add_alerts() -> None:
        """Check coordinator data and add/remove version-gated alert sensors as firmware version changes."""
        data = coordinator.data or {}
        fw_version = data.get("fw_version")
        new_entities = []

        for key, entity_description in VERSION_GATED_ALERT_DESCRIPTIONS.items():
            if key in created_alert_keys:
                continue

            if _is_alert_fw_supported(key, fw_version):
                new_entities.append(
                    JaamHAHomeAlertSensor(coordinator=coordinator, entity_description=entity_description)
                )
                created_alert_keys.add(key)
                LOGGER.info("Dynamically adding new alert sensor: %s (firmware %s)", key, fw_version)

        if new_entities:
            async_add_entities(new_entities)

        entity_registry = er.async_get(hass)
        chip_id = data.get("chip_id") or entry.entry_id

        for key in list(created_alert_keys):  # Use list() to avoid RuntimeError during iteration
            if _is_alert_fw_supported(key, fw_version):
                continue

            entity_id = _find_alert_entity_id(entity_registry, chip_id, entry.entry_id, key)
            if entity_id:
                LOGGER.info("Dynamically removing alert sensor %s - no longer supported", entity_id)
                entity_registry.async_remove(entity_id)
                created_alert_keys.discard(key)

    # Register listener to be called on every coordinator update
    entry.async_on_unload(coordinator.async_add_listener(_check_and_add_alerts))
