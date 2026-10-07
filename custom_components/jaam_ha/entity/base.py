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

        # Device name: the name set on the device itself (same for Fusion and Touch),
        # falling back to the chip id, then to the entry title.
        custom_name = self.coordinator.data.get("device_name") if self.coordinator.data else None
        if custom_name:
            device_name = custom_name
        elif chip_id:
            device_name = f"JAAM {chip_id}"
        else:
            device_name = self.coordinator.config_entry.title

        # "model" is the explicit Fusion/Touch label. The device's own custom name is shown
        # in the hub title (coordinator sync_entry_title) - not in model_id, which HA renders
        # as "model (model_id)" and which duplicated the name there.
        device_type = self.coordinator.config_entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)
        model_name = DEVICE_TYPE_LABELS.get(device_type, DEVICE_TYPE_LABELS[DEFAULT_DEVICE_TYPE])
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
            serial_number=device_identifier,
            sw_version=fw_version or "Unknown",
            configuration_url=config_url,
        )
