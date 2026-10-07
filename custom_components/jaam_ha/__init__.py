"""
Custom integration to integrate jaam_ha with Home Assistant.

This integration demonstrates best practices for:
- Config flow setup (user, reconfigure, reauth)
- DataUpdateCoordinator pattern for efficient data fetching
- Multiple platform types (sensor, binary_sensor, switch, select, number)
- Service registration and handling
- Device and entity management
- Proper error handling and recovery

For more details about this integration, please refer to:
https://github.com/J-A-A-M/jaam_ha

For integration development guidelines:
https://developers.home-assistant.io/docs/creating_integration_manifest
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import (
    CONF_DEVICE_TYPE,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_PORT,
    DEVICE_TYPE_TOUCH,
    DOMAIN,
    LOGGER,
)
from homeassistant.const import Platform
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.loader import async_get_loaded_integration

from .api import JaamHAApiClient
from .coordinator import JaamHADataUpdateCoordinator
from .data import JaamHAData
from .service_actions import async_setup_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import JaamHAConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]

# This integration is configured via config entries only
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Set up the integration.

    This is called once at Home Assistant startup to register service actions.
    Service actions must be registered here (not in async_setup_entry) to ensure:
    - Service action validation works correctly
    - Service actions are available even without config entries
    - Helpful error messages are provided

    This is a Silver Quality Scale requirement.

    Args:
        hass: The Home Assistant instance.
        config: The Home Assistant configuration.

    Returns:
        True if setup was successful.

    For more information:
    https://developers.home-assistant.io/docs/dev_101_services
    """
    await async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
) -> bool:
    """
    Set up this integration using UI.

    This is called when a config entry is loaded. It:
    1. Creates the API client with credentials from the config entry
    2. Initializes the DataUpdateCoordinator for data fetching
    3. Performs the first data refresh
    4. Sets up all platforms (sensors, switches, etc.)
    5. Registers services
    6. Sets up reload listener for config changes

    Data flow in this integration:
    1. User enters username/password in config flow (config_flow.py)
    2. Credentials stored in entry.data[CONF_USERNAME/CONF_PASSWORD]
    3. API Client initialized with credentials (api/client.py)
    4. Coordinator fetches data using authenticated client (coordinator/base.py)
    5. Entities access data via self.coordinator.data (sensor/, binary_sensor/, etc.)

    This pattern ensures credentials from setup flow are used throughout
    the integration's lifecycle for API communication.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being set up.

    Returns:
        True if setup was successful.

    For more information:
    https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
    """
    # Initialize client first
    client = JaamHAApiClient(
        host=entry.data[CONF_HOST],
        session=async_get_clientsession(hass),
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
    )

    # Initialize coordinator with config_entry
    coordinator = JaamHADataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        config_entry=entry,
        update_interval=timedelta(hours=1),
        always_update=False,  # Only update entities when data actually changes
    )

    # Store runtime data
    entry.runtime_data = JaamHAData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Earlier versions stored the device's own name as model_id, which HA renders as
    # "model (model_id)" - a duplicate next to the name. Entities no longer send it, but the
    # registry ignores a missing value, so clear the stored one explicitly. Same for the hub
    # title: sync it to the "<Fusion/Touch> (<name>)" form once the first data is in.
    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if device.model_id is not None:
            device_registry.async_update_device(device.id, model_id=None)
    first_data = coordinator.data or {}
    if first_data.get("device_name") or first_data.get("chip_id"):
        coordinator.sync_entry_title(first_data.get("device_name"), first_data.get("chip_id"))
        if first_data.get("device_name"):
            coordinator.update_device_name(first_data["device_name"], first_data.get("chip_id"))

    # jaam_touch has no web interface, so its device page must not show a "Visit" link.
    # Entities never send a configuration_url for it (see entity/base.py), but the device
    # registry ignores a missing/None value, so a URL stored by an earlier version stays
    # until it's cleared explicitly.
    if entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE) == DEVICE_TYPE_TOUCH:
        device_registry = dr.async_get(hass)
        for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
            if device.configuration_url is not None:
                device_registry.async_update_device(device.id, configuration_url=None)

        # The single live-range "Sound Volume" number is gone (the device only reports day and
        # night volume now) - drop the one an earlier version registered.
        entity_registry = er.async_get(hass)
        for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
            if entity.unique_id.endswith("_sound_volume"):
                entity_registry.async_remove(entity.entity_id)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
) -> bool:
    """
    Unload a config entry.

    This is called when the integration is being removed or reloaded.
    It ensures proper cleanup of:
    - All platform entities
    - WebSocket connection
    - Update listeners

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being unloaded.

    Returns:
        True if unload was successful.

    For more information:
    https://developers.home-assistant.io/docs/config_entries_index/#unloading-entries
    """
    # Shutdown coordinator (closes WebSocket connection)
    await entry.runtime_data.coordinator.async_shutdown()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: JaamHAConfigEntry,
) -> None:
    """
    Reload config entry.

    This is called when the integration configuration or options have changed.
    It unloads and then reloads the integration with the new configuration.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being reloaded.

    For more information:
    https://developers.home-assistant.io/docs/config_entries_index/#reloading-entries
    """
    await hass.config_entries.async_reload(entry.entry_id)
