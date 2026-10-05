"""
Base entity class for jaam_ha.

This module provides the base entity class that all integration entities inherit from.
It handles common functionality like device info, unique IDs, and coordinator integration.

For more information on entities:
https://developers.home-assistant.io/docs/core/entity
https://developers.home-assistant.io/docs/core/entity/index/#common-properties
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import (
    ATTRIBUTION,
    CONF_DEVICE_TYPE,
    CONF_HOST,
    DEFAULT_DEVICE_TYPE,
    DEVICE_TYPE_LABELS,
    DEVICE_TYPE_TOUCH,
    LOGGER,
)
from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class JaamHAEntity(CoordinatorEntity[JaamHADataUpdateCoordinator]):
    """
    Base entity class for jaam_ha.

    All entities in this integration inherit from this class, which provides:
    - Automatic coordinator updates
    - Device info management
    - Unique ID generation
    - Attribution and naming conventions

    For more information:
    https://developers.home-assistant.io/docs/core/entity
    https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """
        Initialize the base entity.

        Args:
            coordinator: The data update coordinator for this entity.
            entity_description: The entity description defining characteristics.

        """
        super().__init__(coordinator)
        self.entity_description = entity_description

        # Generate unique_id using chip_id from device data: jaam_[chipID]_[key]
        LOGGER.debug(
            "[%s] Initializing entity, coordinator.data type: %s",
            entity_description.key,
            type(coordinator.data),
        )

        if coordinator.data:
            LOGGER.debug(
                "[%s] coordinator.data keys: %s",
                entity_description.key,
                coordinator.data.keys(),
            )
            LOGGER.debug(
                "[%s] coordinator.data contents: %s",
                entity_description.key,
                coordinator.data,
            )
            chip_id = coordinator.data.get("chip_id")
            LOGGER.debug(
                "[%s] Extracted chip_id: %s (type: %s)",
                entity_description.key,
                chip_id,
                type(chip_id),
            )

            if chip_id:
                self._attr_unique_id = f"jaam_{chip_id}_{entity_description.key}"
                LOGGER.info(
                    "[%s] Using chip_id-based unique_id: %s",
                    entity_description.key,
                    self._attr_unique_id,
                )
            else:
                # Fallback if chip_id is not available
                self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{entity_description.key}"
                LOGGER.warning(
                    "[%s] chip_id not found, using fallback unique_id: %s",
                    entity_description.key,
                    self._attr_unique_id,
                )
        else:
            # Fallback if data is not yet loaded
            self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{entity_description.key}"
            LOGGER.warning(
                "[%s] coordinator.data is None, using fallback unique_id: %s",
                entity_description.key,
                self._attr_unique_id,
            )

    @property
    def device_info(self) -> DeviceInfo:
        """
        Return device info for this entity.

        This property dynamically generates device info from current coordinator data,
        allowing sw_version and other device properties to update when data changes.
        """
        # Get chip_id as device identifier
        chip_id = self.coordinator.data.get("chip_id") if self.coordinator.data else None
        device_identifier = chip_id or self.coordinator.config_entry.entry_id

        # Get device name
        if chip_id:
            device_name = f"JAAM {chip_id}"
        else:
            device_name = self.coordinator.config_entry.title

        # "model" is the explicit Fusion/Touch label (not the device's own custom name) -
        # so it's obvious at a glance which firmware/protocol family this device is without
        # opening it to guess from which entities exist. The device's own custom name (e.g.
        # jaam_fusion's user-set "device_name" setting) goes in model_id instead, so it's
        # still visible but doesn't get confused with the type label; omitted entirely when
        # it's identical to the type label (jaam_touch always reports "JAAM Touch" as its
        # device_name, which would just be a redundant duplicate here).
        device_type = self.coordinator.config_entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)
        model_name = DEVICE_TYPE_LABELS.get(device_type, DEVICE_TYPE_LABELS[DEFAULT_DEVICE_TYPE])
        custom_name = self.coordinator.data.get("device_name") if self.coordinator.data else None
        model_id = custom_name if custom_name and custom_name != model_name else None
        fw_version = self.coordinator.data.get("fw_version") if self.coordinator.data else None

        # Build configuration URL from config entry. jaam_touch has no web interface, so it
        # gets none (otherwise the device page shows a "Visit" link to a dead page).
        host = self.coordinator.config_entry.data.get(CONF_HOST)
        config_url = f"http://{host}" if host and device_type != DEVICE_TYPE_TOUCH else None

        return DeviceInfo(
            identifiers={
                (
                    self.coordinator.config_entry.domain,
                    device_identifier,
                ),
            },
            name=device_name,
            manufacturer="JAAM",
            model=model_name,
            model_id=model_id,
            serial_number=device_identifier,
            sw_version=fw_version or "Unknown",
            configuration_url=config_url,
        )
