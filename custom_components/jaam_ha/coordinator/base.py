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

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo

from custom_components.jaam_ha.api import JaamHAApiClientAuthenticationError, JaamHAApiClientError, JaamHADeviceData
from custom_components.jaam_ha.const import LOGGER
from homeassistant.components import zeroconf
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
    _unavailable_timer_task: asyncio.Task | None = None
    _zeroconf_browser: AsyncServiceBrowser | None = None
    _zeroconf_setup_done: bool = False

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
        LOGGER.debug("_async_setup called for entry %s", self.config_entry.entry_id)

        # Set up zeroconf listener FIRST (before connection attempt)
        # This allows instant reconnect even if initial connection fails
        # Use unique_id from config entry (which is the chip_id)
        chip_id = self.config_entry.unique_id
        if chip_id:
            LOGGER.debug("Calling _setup_zeroconf_listener with chip_id: %s", chip_id)
            await self._setup_zeroconf_listener(chip_id)
        else:
            LOGGER.warning("No unique_id in config entry - zeroconf listener not set up")

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

            # Update device model if it changed
            if new_name and old_name != new_name:
                LOGGER.info("Device model changed from '%s' to '%s'", old_name, new_name)
                self._update_device_model(new_name)

            # Cache new value for next comparison
            self._cached_device_name = new_name

        # Update coordinator data and notify all listening entities
        self.async_set_updated_data(data)

    def _handle_connection_status(self, connected: bool) -> None:
        """
        Handle WebSocket connection status changes.

        This callback is invoked by the API client when the WebSocket connection
        status changes. When disconnected, it waits 15 seconds before marking
        entities as unavailable (grace period for quick reconnects).
        When reconnected, entities will become available on the next data update.

        Args:
            connected: True if connected, False if disconnected.

        """
        if not connected:
            LOGGER.warning("WebSocket disconnected - waiting 15 seconds before marking unavailable")

            # Start timer to mark entities unavailable after grace period
            if self._unavailable_timer_task and not self._unavailable_timer_task.done():
                # Timer already running, don't start another one
                return

            self._unavailable_timer_task = asyncio.create_task(self._mark_unavailable_after_timeout())
        else:
            LOGGER.info("WebSocket connected")

            # Cancel unavailable timer if connection restored during grace period
            if self._unavailable_timer_task and not self._unavailable_timer_task.done():
                LOGGER.info("Connection restored during grace period - cancelling unavailable timer")
                self._unavailable_timer_task.cancel()
                self._unavailable_timer_task = None

            # On reconnection, entities will be marked available on next data update

    async def _mark_unavailable_after_timeout(self) -> None:
        """
        Wait 15 seconds and then mark all entities as unavailable.

        This provides a grace period for quick reconnects without showing
        unavailable status to the user.
        """
        try:
            await asyncio.sleep(15)
            LOGGER.warning("Grace period expired - marking entities as unavailable")
            # Mark coordinator as having an error, which makes all entities unavailable
            self.async_set_update_error(
                UpdateFailed(
                    translation_domain="jaam_ha",
                    translation_key="connection_lost",
                )
            )
        except asyncio.CancelledError:
            LOGGER.debug("Unavailable timer cancelled - connection restored")

    def _update_device_model(self, new_model: str) -> None:
        """
        Update device model in device registry.

        Args:
            new_model: New device model from device.

        """
        device_reg = dr.async_get(self.hass)
        chip_id = self.data.get("chip_id") if self.data else None
        device_identifier = chip_id or self.config_entry.entry_id

        # Find the device by identifier
        device = device_reg.async_get_device(identifiers={(self.config_entry.domain, device_identifier)})

        if device:
            device_reg.async_update_device(
                device.id,
                model=new_model,
            )
            LOGGER.info("Updated device model to '%s' in device registry", new_model)
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
        client = self.config_entry.runtime_data.client

        # Skip update if client is disconnected (during reconnect attempts)
        # This avoids noisy error logs during normal reconnection flow
        if not client.connected:
            LOGGER.debug("Skipping data update - client not connected (reconnecting)")
            raise UpdateFailed(
                translation_domain="jaam_ha",
                translation_key="connection_lost",
            )

        try:
            # For WebSocket, just return current data (updated in real-time)
            # This refresh mainly serves as a connection health check
            data = await client.async_get_data()
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

    async def _setup_zeroconf_listener(self, chip_id: str) -> None:
        """
        Set up zeroconf listener for instant reconnect.

        Listens for zeroconf service updates and triggers immediate reconnect
        when our device is discovered, bypassing the adaptive backoff delay.

        Args:
            chip_id: Device chip ID for matching zeroconf announcements.

        """
        # Only set up once
        if self._zeroconf_setup_done:
            return

        LOGGER.debug("Setting up zeroconf listener for chip_id: %s", chip_id)

        def zeroconf_service_update(
            *,
            zeroconf: Any,
            service_type: str,
            name: str,
            state_change: ServiceStateChange,
        ) -> None:
            """Handle zeroconf service updates (sync wrapper)."""
            if state_change not in (ServiceStateChange.Added, ServiceStateChange.Updated):
                return

            # Schedule async handler
            self.hass.async_create_task(self._handle_zeroconf_update(zeroconf, service_type, name, chip_id))

        # Get aiozeroconf instance from Home Assistant (async operation)
        aiozc = await zeroconf.async_get_async_instance(self.hass)

        # Create service browser
        self._zeroconf_browser = AsyncServiceBrowser(
            aiozc.zeroconf,
            "_jaam-ws._tcp.local.",
            handlers=[zeroconf_service_update],
        )

        # Register cleanup callback
        self.config_entry.async_on_unload(self._zeroconf_browser.async_cancel)
        self._zeroconf_setup_done = True
        LOGGER.debug("Zeroconf listener active for chip_id: %s", chip_id)

    async def _handle_zeroconf_update(
        self,
        zeroconf_instance: Any,
        service_type: str,
        name: str,
        expected_chip_id: str,
    ) -> None:
        """
        Handle async zeroconf service update.

        Args:
            zeroconf_instance: Zeroconf instance.
            service_type: Service type.
            name: Service name.
            expected_chip_id: Expected chip_id to match.

        """
        # Get service info to check chip_id
        info = AsyncServiceInfo(service_type, name)
        if not await info.async_request(zeroconf_instance, 3000):
            return

        # Check if this is our device by comparing chip_id
        discovered_chip_id_raw = info.properties.get(b"chipId") or info.properties.get(b"chip_id")
        if not discovered_chip_id_raw:
            return

        discovered_chip_id = (
            discovered_chip_id_raw.decode() if isinstance(discovered_chip_id_raw, bytes) else discovered_chip_id_raw
        )

        if str(discovered_chip_id) == str(expected_chip_id):
            LOGGER.info(
                "Zeroconf detected our device %s is back online at %s:%s, triggering immediate reconnect",
                expected_chip_id,
                info.server,
                info.port,
            )
            # Trigger immediate reconnect in client
            await self.config_entry.runtime_data.client.async_trigger_reconnect()

    async def async_shutdown(self) -> None:
        """
        Shut down the coordinator.

        Called when the integration is being unloaded. Closes the WebSocket
        connection and performs cleanup.
        """
        # Cancel unavailable timer if running
        if self._unavailable_timer_task and not self._unavailable_timer_task.done():
            self._unavailable_timer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._unavailable_timer_task

        await super().async_shutdown()
        await self.config_entry.runtime_data.client.async_disconnect()
        LOGGER.debug("Coordinator shutdown complete for %s", self.config_entry.entry_id)
