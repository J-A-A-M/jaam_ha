"""
API Client for jaam_ha.

This module provides the WebSocket API client for communicating with JAAM devices.
It handles WebSocket connections, command sending, and state updates.

For more information on creating API clients:
https://developers.home-assistant.io/docs/api_lib_index
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
import json
from typing import Any

import aiohttp
from aiohttp import WSMsgType

from custom_components.jaam_ha.const import LOGGER


class JaamHAApiClientError(Exception):
    """Base exception to indicate a general API error."""


class JaamHAApiClientCommunicationError(
    JaamHAApiClientError,
):
    """Exception to indicate a communication error with the API."""


class JaamHAApiClientAuthenticationError(
    JaamHAApiClientError,
):
    """Exception to indicate an authentication error with the API."""


# Type alias for device data
type JaamHADeviceData = dict[str, Any]


class JaamHAApiClient:
    """
    WebSocket API Client for JAAM device integration.

    This client handles WebSocket connections to JAAM devices, command sending,
    and state update notifications. It maintains a persistent connection and
    automatically handles reconnection on errors.

    The client connects to the device's WebSocket server (default port 81) and:
    - Receives initial_state message upon connection
    - Sends commands (set_map_mode, set_lamp, set_home_region)
    - Listens for broadcast updates (state changes, alerts)
    - Invokes callbacks when data updates are received

    For more information on API clients:
    https://developers.home-assistant.io/docs/api_lib_index

    Attributes:
        _host: The hostname or IP address of the JAAM device.
        _port: The WebSocket port (default 81).
        _session: The aiohttp ClientSession for making requests.
        _ws: The active WebSocket connection.
        _listen_task: Background task for listening to messages.
        _data: Current device state data.
        _update_callback: Callback invoked when data updates are received.

    """

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        port: int = 81,
    ) -> None:
        """
        Initialize the API Client.

        Args:
            host: The hostname or IP address of the JAAM device.
            session: The aiohttp ClientSession to use for requests.
            port: The WebSocket port (default 81).

        """
        self._host = host
        self._port = int(port)  # Ensure port is always an integer
        self._session = session
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._listen_task: asyncio.Task | None = None
        self._data: JaamHADeviceData | None = None
        self._update_callback: Callable[[JaamHADeviceData], None] | None = None
        self._connection_callback: Callable[[bool], None] | None = None
        self._connected = False
        self._should_reconnect = True
        self._reconnect_task: asyncio.Task | None = None
        self._connect_lock = asyncio.Lock()  # Prevent multiple concurrent connections

    @property
    def connected(self) -> bool:
        """Return True if WebSocket is connected."""
        return self._connected and self._ws is not None and not self._ws.closed

    @property
    def data(self) -> JaamHADeviceData | None:
        """Return current device data."""
        return self._data

    def set_update_callback(self, callback: Callable[[JaamHADeviceData], None]) -> None:
        """
        Set callback for data updates.

        Args:
            callback: Function to call when new data is received.

        """
        self._update_callback = callback

    def set_connection_callback(self, callback: Callable[[bool], None]) -> None:
        """
        Set callback for connection status changes.

        Args:
            callback: Function to call when connection status changes.
                     Called with True when connected, False when disconnected.

        """
        self._connection_callback = callback

    async def async_connect(self) -> JaamHADeviceData:
        """
        Connect to the JAAM device WebSocket server.

        Establishes WebSocket connection and waits for initial_state message.
        Uses a lock to prevent multiple concurrent connection attempts.

        Returns:
            Initial device state data.

        Raises:
            JaamHAApiClientCommunicationError: If connection fails.
            JaamHAApiClientError: For other errors.

        """
        async with self._connect_lock:
            # Check if already connected
            if self.connected:
                if self._data:
                    return self._data
                # Wait for initial state if connected but no data yet
                return await self._wait_for_initial_state()

            # Close any existing connection before creating new one
            await self._close_existing_connection()

            try:
                url = f"ws://{self._host}:{self._port}"
                LOGGER.info("Connecting to JAAM device at %s", url)

                async with asyncio.timeout(10):
                    self._ws = await self._session.ws_connect(
                        url,
                        heartbeat=30,
                        compress=15,
                    )

                self._connected = True
                LOGGER.info("WebSocket connected successfully")

                # Notify coordinator of connection
                if self._connection_callback:
                    self._connection_callback(True)

                # Wait for initial_state message
                initial_data = await self._wait_for_initial_state()
                LOGGER.info(
                    "Received initial state - chip_id: %s, fw_version: %s",
                    initial_data.get("chip_id"),
                    initial_data.get("fw_version"),
                )

                # Enable automatic reconnection
                self._should_reconnect = True

                # Start listening for updates in background
                self._listen_task = asyncio.create_task(self._listen())

                return initial_data  # noqa: TRY300

            except TimeoutError as exception:
                msg = f"Timeout connecting to {self._host}:{self._port}"
                LOGGER.error(msg)
                raise JaamHAApiClientCommunicationError(msg) from exception
            except (aiohttp.ClientError, OSError) as exception:
                msg = f"Error connecting to {self._host}:{self._port} - {exception}"
                LOGGER.error("%s - Type: %s", msg, type(exception).__name__)
                raise JaamHAApiClientCommunicationError(msg) from exception
            except JaamHAApiClientError:
                # Re-raise our own exceptions without wrapping
                raise
            except Exception as exception:
                msg = f"Unexpected error connecting - {exception}"
                LOGGER.error("%s - Type: %s", msg, type(exception).__name__)
                raise JaamHAApiClientError(msg) from exception

    async def async_disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        # Disable automatic reconnection
        self._should_reconnect = False
        self._connected = False

        # Cancel reconnect task if running
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task

        # Cancel listen task
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task

        # Close WebSocket connection
        if self._ws and not self._ws.closed:
            await self._ws.close()

        self._ws = None
        self._listen_task = None
        self._reconnect_task = None

    async def async_trigger_reconnect(self) -> None:
        """
        Trigger immediate reconnection attempt.

        Cancels any ongoing backoff wait and attempts to reconnect immediately.
        This is useful when external discovery (e.g., zeroconf) detects that
        the device is back online.
        Uses lock to prevent multiple concurrent reconnection attempts.
        """
        if not self._should_reconnect:
            return

        if self.connected:
            return

        # Check if lock is already acquired (connection attempt in progress)
        if self._connect_lock.locked():
            return

        LOGGER.info("Triggered immediate reconnection attempt (skipping backoff)")

        # Cancel current reconnect task if it's waiting
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task

        # Start new reconnect task immediately
        self._reconnect_task = asyncio.create_task(self._immediate_reconnect())

    async def _close_existing_connection(self) -> None:
        """Close existing WebSocket connection and clean up tasks."""
        # Cancel listen task
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None

        # Close WebSocket
        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._ws = None

    async def _immediate_reconnect(self) -> None:
        """Attempt immediate reconnection without backoff."""
        async with self._connect_lock:
            # Check if already connected (another task may have connected while waiting for lock)
            if self.connected:
                return

            # Close any existing connection
            await self._close_existing_connection()

            try:
                url = f"ws://{self._host}:{self._port}"
                LOGGER.info("Attempting immediate reconnection to %s", url)

                async with asyncio.timeout(10):
                    self._ws = await self._session.ws_connect(
                        url,
                        heartbeat=30,
                        compress=15,
                    )

                self._connected = True
                LOGGER.info("Immediate reconnection successful")

                # Notify coordinator of reconnection
                if self._connection_callback:
                    self._connection_callback(True)

                # Wait for initial_state message and update data
                try:
                    initial_data = await self._wait_for_initial_state()
                    LOGGER.info(
                        "Received initial state after immediate reconnection - chip_id: %s",
                        initial_data.get("chip_id"),
                    )

                    # Notify coordinator of new data
                    if self._update_callback:
                        self._update_callback(initial_data)

                except (JaamHAApiClientError, TimeoutError, json.JSONDecodeError) as exc:
                    LOGGER.error("Failed to get initial state after immediate reconnection: %s", exc)
                    # Connection established but failed to get state, close and resume normal reconnect
                    if self._ws and not self._ws.closed:
                        await self._ws.close()
                        self._connected = False
                    # Resume normal reconnect loop
                    if self._should_reconnect:
                        self._reconnect_task = asyncio.create_task(self._reconnect_loop())
                    return

                # Start listening again
                self._listen_task = asyncio.create_task(self._listen())

            except asyncio.CancelledError:
                pass
            except (TimeoutError, aiohttp.ClientError, OSError) as exc:
                LOGGER.warning("Immediate reconnection failed: %s", exc)
                # Resume normal reconnect loop with backoff
                if self._should_reconnect:
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _wait_for_initial_state(self) -> JaamHADeviceData:
        """
        Wait for initial_state message from device.

        Returns:
            Device state data from initial_state message.

        Raises:
            JaamHAApiClientCommunicationError: If no initial state received.

        """
        if not self._ws:
            msg = "WebSocket not connected"
            raise JaamHAApiClientCommunicationError(msg)

        try:
            async with asyncio.timeout(10):
                async for msg in self._ws:
                    if msg.type == WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            msg_type = data.get("type")

                            if msg_type == "initial_state":
                                return self._parse_initial_state(data)
                        except json.JSONDecodeError as exc:
                            LOGGER.error("Failed to parse JSON from message: %s", msg.data, exc_info=exc)
                    elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                        msg_text = f"WebSocket closed before receiving initial state (type: {msg.type})"
                        LOGGER.error(msg_text)
                        raise JaamHAApiClientCommunicationError(msg_text)
        except TimeoutError as exception:
            msg = "Timeout waiting for initial state"
            LOGGER.error(msg)
            raise JaamHAApiClientCommunicationError(msg) from exception

        msg = "No initial state received"
        raise JaamHAApiClientCommunicationError(msg)

    def _parse_initial_state(self, data: dict[str, Any]) -> JaamHADeviceData:
        """
        Parse initial_state message into device data.

        Args:
            data: The JSON data from initial_state message.

        Returns:
            Parsed device data as a dictionary.

        """
        LOGGER.info("Parsing initial_state message")

        lamp_data = data.get("lamp", {})

        device_data: JaamHADeviceData = {
            "connected": data.get("connected", False),
            "chip_id": data.get("chip_id"),
            "device_name": data.get("device_name"),
            "fw_version": data.get("fw_version"),
            "fw_latest": data.get("fw_latest"),
            "map_mode_id": data.get("map_mode_id"),
            "home_region": data.get("home_region"),
            "home_alert_flags": data.get("home_alert_flags"),
            "home_district_temp": data.get("home_district_temp"),
            "used_memory": data.get("used_memory"),
            "uptime": data.get("uptime"),
            "wifi_uptime": data.get("wifi_uptime"),
            "wifi_signal": data.get("wifi_signal"),
            "cpu_temp": data.get("cpu_temp"),
            "websocket_status": data.get("websocket_status"),
            "websocket_uptime": data.get("websocket_uptime"),
            "lamp_color": lamp_data.get("color"),
            "lamp_brightness": lamp_data.get("brightness"),
            "climate_temp": data.get("climate_temp"),
            "climate_humidity": data.get("climate_humidity"),
            "climate_pressure": data.get("climate_pressure"),
            "light_level": data.get("light_level"),
        }

        LOGGER.info(
            "Parsed device data - chip_id: %s, fw_version: %s",
            device_data.get("chip_id"),
            device_data.get("fw_version"),
        )

        self._data = device_data
        return device_data

    async def _listen(self) -> None:
        """Listen for messages from the WebSocket server."""
        if not self._ws:
            return

        try:
            async for msg in self._ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                    break
        except asyncio.CancelledError:
            # Task cancelled, normal shutdown
            pass
        except Exception as exc:  # noqa: BLE001
            # Connection error
            LOGGER.warning("WebSocket connection error: %s", exc)
        finally:
            self._connected = False
            # Notify coordinator of disconnection
            if self._connection_callback:
                self._connection_callback(False)
            LOGGER.warning("WebSocket disconnected")

            # Attempt to reconnect if not explicitly disconnected
            if self._should_reconnect:
                LOGGER.info("Starting automatic reconnection")
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Attempt to reconnect to WebSocket with adaptive backoff strategy."""
        attempt = 0
        max_delay = 60  # Maximum delay between attempts in seconds
        fast_retry_attempts = 12  # Try every 5 seconds for the first minute

        while self._should_reconnect:
            attempt += 1

            # First minute: retry every 5 seconds (12 attempts)
            # After first minute: exponential backoff (10, 20, 40, 60 max)
            if attempt <= fast_retry_attempts:
                delay = 5
            else:
                # Exponential backoff starting from attempt 13
                backoff_attempt = attempt - fast_retry_attempts
                delay = min(5 * (2**backoff_attempt), max_delay)

            LOGGER.info(
                "Reconnection attempt %d in %d seconds",
                attempt,
                delay,
            )

            try:
                await asyncio.sleep(delay)

                # Check if we should still reconnect after sleep
                if not self._should_reconnect:
                    break

                # Use lock to prevent concurrent connection attempts
                async with self._connect_lock:
                    # Check again after acquiring lock
                    if self.connected:
                        break

                    # Close any existing connection
                    await self._close_existing_connection()

                    # Attempt to reconnect
                    url = f"ws://{self._host}:{self._port}"
                    LOGGER.info("Attempting to reconnect to %s", url)

                    async with asyncio.timeout(10):
                        self._ws = await self._session.ws_connect(
                            url,
                            heartbeat=30,
                            compress=15,
                        )

                    self._connected = True
                    LOGGER.info("Reconnected successfully to device")

                    # Notify coordinator of reconnection
                    if self._connection_callback:
                        self._connection_callback(True)

                    # Wait for initial_state message and update data
                    try:
                        initial_data = await self._wait_for_initial_state()
                        LOGGER.info(
                            "Received initial state after reconnection - chip_id: %s", initial_data.get("chip_id")
                        )

                        # Notify coordinator of new data
                        if self._update_callback:
                            self._update_callback(initial_data)

                    except (JaamHAApiClientError, TimeoutError, json.JSONDecodeError) as exc:
                        LOGGER.error("Failed to get initial state after reconnection: %s", exc)
                        # Connection established but failed to get state, close and retry
                        if self._ws and not self._ws.closed:
                            await self._ws.close()
                        continue

                    # Start listening again
                    self._listen_task = asyncio.create_task(self._listen())

                    # Reset attempt counter on successful reconnection
                    attempt = 0
                    break

            except asyncio.CancelledError:
                break
            except (TimeoutError, aiohttp.ClientError, OSError) as exc:
                LOGGER.warning(
                    "Reconnection attempt %d failed: %s",
                    attempt,
                    exc,
                )
                # Continue loop for next attempt

    async def _handle_message(self, raw_data: str) -> None:  # noqa: C901
        """
        Handle incoming WebSocket message.

        Args:
            raw_data: Raw JSON string from WebSocket.

        """
        try:
            data = json.loads(raw_data)
            msg_type = data.get("type")

            if not msg_type:
                return

            # Update local state based on message type
            if msg_type == "map_mode_change":
                if self._data:
                    self._data["map_mode_id"] = data.get("map_mode_id")

            elif msg_type == "lamp_change":
                lamp_data = data.get("lamp", {})
                if self._data:
                    self._data["lamp_color"] = lamp_data.get("color")
                    self._data["lamp_brightness"] = lamp_data.get("brightness")

            elif msg_type == "home_region_change":
                if self._data:
                    self._data["home_region"] = data.get("home_region")

            elif msg_type == "home_alert_change":
                if self._data:
                    self._data["home_alert_flags"] = data.get("home_alert_flags")

            elif msg_type == "device_name_change":
                if self._data:
                    self._data["device_name"] = data.get("device_name")
                    LOGGER.info("Device name changed: %s", self._data.get("device_name"))

            elif msg_type == "system_info":
                if self._data:
                    self._data["used_memory"] = data.get("used_memory")
                    self._data["uptime"] = data.get("uptime")
                    self._data["wifi_uptime"] = data.get("wifi_uptime")
                    self._data["wifi_signal"] = data.get("wifi_signal")
                    self._data["cpu_temp"] = data.get("cpu_temp")
                    self._data["websocket_status"] = data.get("websocket_status")
                    self._data["websocket_uptime"] = data.get("websocket_uptime")

            elif msg_type == "home_district_temp_change":
                if self._data:
                    self._data["home_district_temp"] = data.get("home_district_temp")

            elif msg_type == "climate_data_change":
                if self._data:
                    self._data["climate_temp"] = data.get("climate_temp")
                    self._data["climate_humidity"] = data.get("climate_humidity")
                    self._data["climate_pressure"] = data.get("climate_pressure")

            elif msg_type == "light_level_change":
                if self._data:
                    self._data["light_level"] = data.get("light_level")

            elif msg_type == "firmware_update":
                if self._data:
                    self._data["fw_latest"] = data.get("fw_latest")

            elif msg_type == "fw_update_progress":
                if self._data:
                    progress = data.get("progress")
                    if progress == -1:
                        # Update failed - clear progress
                        LOGGER.error("Firmware update failed (progress: -1)")
                        self._data["fw_update_progress"] = None
                    elif progress == 100:
                        # Update completed successfully - clear progress
                        LOGGER.info("Firmware update completed successfully")
                        self._data["fw_update_progress"] = None
                    else:
                        # Update in progress (0-99)
                        self._data["fw_update_progress"] = progress

            # Notify coordinator of data update
            if self._update_callback and self._data:
                # Create a copy to ensure coordinator detects changes
                self._update_callback(dict(self._data))

        except json.JSONDecodeError as exc:
            # Ignore invalid JSON
            LOGGER.warning("Failed to parse JSON message: %s", raw_data, exc_info=exc)

    async def _send_command(self, command: dict[str, Any]) -> None:
        """
        Send command to device.

        Args:
            command: Command dictionary to send as JSON.

        Raises:
            JaamHAApiClientCommunicationError: If send fails.

        """
        if not self.connected or not self._ws:
            msg = "WebSocket not connected"
            raise JaamHAApiClientCommunicationError(msg)

        try:
            await self._ws.send_json(command)
        except (aiohttp.ClientError, OSError) as exception:
            msg = f"Error sending command - {exception}"
            raise JaamHAApiClientCommunicationError(msg) from exception

    async def async_set_map_mode(self, mode: str | int) -> None:
        """
        Set map mode on device.

        Args:
            mode: Mode name (off, alert, weather, flag, lamp) or mode ID (0-4).

        Raises:
            JaamHAApiClientCommunicationError: If command fails.

        """
        command: dict[str, Any] = {"type": "set_map_mode"}

        if isinstance(mode, int):
            command["mode_id"] = mode
        else:
            command["mode"] = mode

        await self._send_command(command)

    async def async_set_display_mode(self, mode: str | int) -> None:
        """
        Set display mode on device.

        Args:
            mode: Mode name (off, clock, weather, technical, microclimate, combined) or mode ID (0, 1, 2, 3, 4, 9).

        Raises:
            JaamHAApiClientCommunicationError: If command fails.

        """
        command: dict[str, Any] = {"type": "set_display_mode"}

        if isinstance(mode, int):
            command["mode_id"] = mode
        else:
            command["mode"] = mode

        await self._send_command(command)

    async def async_set_lamp(
        self,
        color: str | None = None,
        brightness: int | None = None,
    ) -> None:
        """
        Set lamp color and/or brightness.

        Args:
            color: Hex color code (e.g., "#FF0000").
            brightness: Brightness percentage (0-100).

        Raises:
            JaamHAApiClientCommunicationError: If command fails.

        """
        command: dict[str, Any] = {"type": "set_lamp"}

        if color is not None:
            command["color"] = color
        if brightness is not None:
            command["brightness"] = brightness

        await self._send_command(command)

    async def async_set_home_region(self, region_id: int) -> None:
        """
        Set home region on device.

        Args:
            region_id: Region ID (0-9999).

        Raises:
            JaamHAApiClientCommunicationError: If command fails.

        """
        command = {
            "type": "set_home_region",
            "region_id": region_id,
        }

        await self._send_command(command)

    async def async_update_firmware(self, version: str) -> None:
        """Update device firmware to specified version.

        Args:
            version: Firmware version to install.

        Raises:
            JaamHAApiClientCommunicationError: If command fails.

        """
        command = {
            "type": "update_firmware",
            "version": version,
        }

        await self._send_command(command)

    async def async_get_data(self) -> JaamHADeviceData:
        """
        Get current device data.

        For WebSocket client, data is updated in real-time via messages.
        This method returns the cached data.

        Returns:
            Current device data.

        Raises:
            JaamHAApiClientCommunicationError: If not connected or no data.

        """
        if not self.connected:
            msg = "Not connected to device"
            raise JaamHAApiClientCommunicationError(msg)

        if not self._data:
            msg = "No data available"
            raise JaamHAApiClientCommunicationError(msg)

        return self._data
