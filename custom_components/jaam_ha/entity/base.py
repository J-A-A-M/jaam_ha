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

from custom_components.jaam_ha.const import ATTRIBUTION, CONF_HOST, LOGGER
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

        # Set device info with chip_id as identifier and name
        chip_id = coordinator.data.get("chip_id") if coordinator.data else None
        device_identifier = chip_id if chip_id else coordinator.config_entry.entry_id
        device_name = f"JAAM {chip_id}" if chip_id else coordinator.config_entry.title
        fw_version = coordinator.data.get("fw_version") if coordinator.data else None

        # Build configuration URL from config entry
        host = coordinator.config_entry.data.get(CONF_HOST)
        config_url = f"http://{host}" if host else None

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    device_identifier,
                ),
            },
            name=device_name,
            manufacturer="JAAM",
            sw_version=fw_version or "Unknown",
            configuration_url=config_url,
        )

        LOGGER.debug(
            "[%s] Device info set - name: %s, identifier: %s, fw_version: %s",
            entity_description.key,
            device_name,
            device_identifier,
            fw_version,
        )
