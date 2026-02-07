"""
Core DataUpdateCoordinator implementation for jaam_ha.

This module contains the main coordinator class that manages data fetching
and updates for all entities in the integration. For WebSocket connections,
the coordinator maintains a persistent connection and processes real-time
updates from the device.

For more information on coordinators:
https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.api import JaamHAApiClientAuthenticationError, JaamHAApiClientError, JaamHADeviceData
from custom_components.jaam_ha.const import LOGGER
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from custom_components.jaam_ha.data import JaamHAConfigEntry


class JaamHADataUpdateCoordinator(DataUpdateCoordinator[JaamHADeviceData]):
    """
    Class to manage fetching data from the API.

    This coordinator handles WebSocket connection to the JAAM device and
    distributes real-time updates to all entities. It manages:
    - Persistent WebSocket connection
    - Real-time data updates via WebSocket messages
    - Error handling and recovery
    - Authentication failure detection (triggers reauth flow)
    - Data distribution to all entities

    For WebSocket connections, data updates come from the device in real-time
    rather than being polled on an interval. The coordinator maintains the
    connection and notifies entities when new data arrives.

    For more information:
    https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities

    Attributes:
        config_entry: The config entry for this integration instance.
    """

    config_entry: JaamHAConfigEntry

    async def _async_setup(self) -> None:
        """
        Set up the coordinator.

        This method is called automatically during async_config_entry_first_refresh()
        and is the ideal place for one-time initialization tasks such as:
        - Establishing WebSocket connection
        - Setting up event listeners
        - Initializing caches

        This runs before the first data fetch, ensuring any required setup
        is complete before entities start requesting data.
        """
        client = self.config_entry.runtime_data.client

        # Set up callback for real-time updates from WebSocket
        client.set_update_callback(self._handle_device_update)
        LOGGER.debug("Set update callback for device")

        # Set up callback for connection status changes
        client.set_connection_callback(self._handle_connection_status)
        LOGGER.debug("Set connection status callback for device")

        # Connect to the device WebSocket server
        try:
            LOGGER.info(
                "Starting WebSocket connection with device at %s:%s",
                self.config_entry.data.get("host"),
                self.config_entry.data.get("port"),
            )
            await client.async_connect()
        except JaamHAApiClientAuthenticationError as exception:
            LOGGER.warning("Authentication error during setup - %s", exception)
            raise ConfigEntryAuthFailed(
                translation_domain="jaam_ha",
                translation_key="authentication_failed",
            ) from exception
        except JaamHAApiClientError as exception:
            LOGGER.error("Error connecting to device - %s", exception)
            # Re-raise as UpdateFailed to trigger retry
            raise UpdateFailed(
                translation_domain="jaam_ha",
                translation_key="connection_failed",
            ) from exception

        LOGGER.debug("Coordinator setup complete for %s", self.config_entry.entry_id)

    def _handle_device_update(self, data: JaamHADeviceData) -> None:
        """
        Handle real-time data updates from WebSocket.

        This callback is invoked by the API client when new data arrives
        via WebSocket messages. It triggers entity updates.

        Args:
            data: Updated device data from WebSocket.

        """
        LOGGER.debug(
            "Device update received - chip_id: %s, data keys: %s",
            data.get("chip_id"),
            data.keys(),
        )

        # Check if device_name changed and update device registry
        # Note: We compare with cached value because self.data might be the same object as data
        if "device_name" in data:
            new_name = data.get("device_name")
            # Use cached value from previous update (not self.data which might be the same object as data)
            old_name = getattr(self, "_cached_device_name", None)

            LOGGER.debug(
                "Checking device_name: old='%s', new='%s'",
                old_name,
                new_name,
            )

            # Update device name if it changed
            if new_name and old_name != new_name:
                LOGGER.info("Device name changed from '%s' to '%s'", old_name, new_name)
                self._update_device_name(new_name)

            # Cache new value for next comparison
            self._cached_device_name = new_name

        # Update coordinator data and notify all listening entities
        self.async_set_updated_data(data)

    def _handle_connection_status(self, connected: bool) -> None:
        """
        Handle WebSocket connection status changes.

        This callback is invoked by the API client when the WebSocket connection
        status changes. When disconnected, it marks all entities as unavailable.
        When reconnected, entities will become available on the next data update.

        Args:
            connected: True if connected, False if disconnected.

        """
        if not connected:
            LOGGER.warning("WebSocket disconnected - marking entities as unavailable")
            # Mark coordinator as having an error, which makes all entities unavailable
            self.async_set_update_error(
                UpdateFailed(
                    translation_domain="jaam_ha",
                    translation_key="connection_lost",
                )
            )
        else:
            LOGGER.info("WebSocket connected")
            # On reconnection, entities will be marked available on next data update

    def _update_device_name(self, new_name: str) -> None:
        """
        Update device name in device registry.

        Args:
            new_name: New device name from device.

        """
        device_reg = dr.async_get(self.hass)
        chip_id = self.data.get("chip_id") if self.data else None
        device_identifier = chip_id or self.config_entry.entry_id

        # Find the device by identifier
        device = device_reg.async_get_device(identifiers={(self.config_entry.domain, device_identifier)})

        if device:
            device_reg.async_update_device(
                device.id,
                name=new_name,
            )
            LOGGER.info("Updated device name to '%s' in device registry", new_name)
        else:
            LOGGER.warning("Device not found in registry for identifier: %s", device_identifier)

    async def _async_update_data(self) -> JaamHADeviceData:
        """
        Fetch data from API endpoint.

        For WebSocket connections, this method returns the current cached data
        since updates happen in real-time via WebSocket messages. The coordinator
        is configured with update_interval, but this mainly serves as a watchdog
        to detect if the connection is still alive.

        Returns:
            The current device data.

        Raises:
            ConfigEntryAuthFailed: If authentication fails, triggers reauthentication.
            UpdateFailed: If data fetching fails for other reasons.
        """
        try:
            # For WebSocket, just return current data (updated in real-time)
            # This refresh mainly serves as a connection health check
            data = await self.config_entry.runtime_data.client.async_get_data()
            LOGGER.debug("Data refresh - chip_id: %s", data.get("chip_id"))
        except JaamHAApiClientAuthenticationError as exception:
            LOGGER.warning("Authentication error - %s", exception)
            raise ConfigEntryAuthFailed(
                translation_domain="jaam_ha",
                translation_key="authentication_failed",
            ) from exception
        except JaamHAApiClientError as exception:
            LOGGER.exception("Error communicating with device")
            raise UpdateFailed(
                translation_domain="jaam_ha",
                translation_key="update_failed",
            ) from exception
        else:
            return data

    async def async_shutdown(self) -> None:
        """
        Shut down the coordinator.

        Called when the integration is being unloaded. Closes the WebSocket
        connection and performs cleanup.
        """
        await super().async_shutdown()
        await self.config_entry.runtime_data.client.async_disconnect()
        LOGGER.debug("Coordinator shutdown complete for %s", self.config_entry.entry_id)
