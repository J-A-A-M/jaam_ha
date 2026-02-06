"""
Connection validators.

Validation functions for device connection.

When this file grows, consider splitting into:
- connection.py: Connection validation
- discovery.py: Device discovery validators
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.api import JaamHAApiClient, JaamHAApiClientError
from custom_components.jaam_ha.const import DEFAULT_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def validate_connection(hass: HomeAssistant, host: str, port: int = DEFAULT_PORT) -> str:
    """
    Validate device connection by testing WebSocket connection.

    Args:
        hass: Home Assistant instance.
        host: The device hostname or IP address.
        port: The WebSocket port (default 81).

    Returns:
        Device chip_id for use as unique_id.

    Raises:
        JaamHAApiClientCommunicationError: If connection fails.
        JaamHAApiClientError: For other API errors.

    """
    client = JaamHAApiClient(
        host=host,
        session=async_get_clientsession(hass),
        port=port,
    )

    try:
        data = await client.async_connect()

        # Ensure we have a chip_id for unique_id
        if not data.get("chip_id"):
            msg = "Device did not provide chip_id"
            raise JaamHAApiClientError(msg)

        return data["chip_id"]
    finally:
        await client.async_disconnect()


__all__ = [
    "validate_connection",
]
