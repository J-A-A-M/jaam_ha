"""Service actions package for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from custom_components.jaam_ha.const import DOMAIN
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall


# Service schemas
SERVICE_SET_HOME_REGION_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): vol.Any(cv.string, [cv.string]),
        vol.Required("region_id"): vol.All(
            cv.positive_int,
            vol.Range(min=0, max=9999),
        ),
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """
    Register services for the integration.

    Services are registered here (in async_setup) to ensure they are available
    even without config entries and to enable proper service validation.

    This is a Silver Quality Scale requirement.
    """

    async def async_handle_set_home_region(call: ServiceCall) -> None:
        """
        Handle set_home_region service call.

        Args:
            call: The service call containing region_id parameter and optional target.

        Raises:
            HomeAssistantError: If no config entries are available or command fails.

        """
        region_id: int = call.data["region_id"]
        target_device_ids_raw = call.data.get("device_id")

        # Normalize device_id to list (can be string or list)
        target_device_ids: list[str] | None = None
        if target_device_ids_raw:
            if isinstance(target_device_ids_raw, str):
                target_device_ids = [target_device_ids_raw]
            else:
                target_device_ids = target_device_ids_raw

        # Get all config entries for this integration
        all_entries: list[JaamHAConfigEntry] = hass.config_entries.async_entries(DOMAIN)

        if not all_entries:
            raise HomeAssistantError(f"No {DOMAIN} config entries found. Please configure the integration first.")

        # Filter entries by target devices if specified
        entries_to_update: list[JaamHAConfigEntry] = []
        if target_device_ids:
            device_reg = dr.async_get(hass)
            for device_id in target_device_ids:
                device = device_reg.async_get(device_id)
                if not device:
                    continue
                # Find config entry for this device
                for entry in all_entries:
                    # Check if device belongs to this config entry
                    if entry.entry_id in device.config_entries:
                        entries_to_update.append(entry)
                        break
        else:
            # No target specified - apply to all devices
            entries_to_update = all_entries

        if not entries_to_update:
            raise HomeAssistantError("No matching devices found for the specified target.")

        # Set home region on selected devices
        errors = []
        for entry in entries_to_update:
            try:
                await entry.runtime_data.client.async_set_home_region(region_id)
            except Exception as err:  # noqa: BLE001
                # Catch all exceptions to collect errors from multiple devices
                errors.append(f"{entry.title}: {err}")

        if errors:
            raise HomeAssistantError(f"Failed to set home region: {'; '.join(errors)}")

    # Register service
    if not hass.services.has_service(DOMAIN, "set_home_region"):
        hass.services.async_register(
            DOMAIN,
            "set_home_region",
            async_handle_set_home_region,
            schema=SERVICE_SET_HOME_REGION_SCHEMA,
        )
