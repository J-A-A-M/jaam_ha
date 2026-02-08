"""
Config flow for jaam_ha.

This module implements the main configuration flow including:
- Initial user setup
- Zeroconf discovery
- Reconfiguration of existing entries
- Reauthentication flow

For more information:
https://developers.home-assistant.io/docs/config_entries_config_flow_handler
"""

from __future__ import annotations

from typing import Any

from custom_components.jaam_ha.config_flow_handler.schemas import (
    get_reauth_schema,
    get_reconfigure_schema,
    get_user_schema,
    get_zeroconf_confirm_schema,
)
from custom_components.jaam_ha.config_flow_handler.validators import sanitize_host, validate_connection
from custom_components.jaam_ha.const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN, LOGGER
from homeassistant import config_entries
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

# Map exception types to error keys for user-facing messages
ERROR_MAP = {
    "JaamHAApiClientAuthenticationError": "auth",
    "JaamHAApiClientCommunicationError": "connection",
}


class JaamHAConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for jaam_ha.

    This class manages the configuration flow for the integration, including
    initial setup, reconfiguration, and reauthentication.

    Supported flows:
    - user: Initial setup via UI
    - zeroconf: Automatic discovery
    - reconfigure: Update existing configuration
    - reauth: Handle connection issues

    For more details:
    https://developers.home-assistant.io/docs/config_entries_config_flow_handler
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._discovered_device_name: str | None = None
        self._discovered_host: str | None = None
        self._discovered_port: int | None = None
        self._discovered_chip_id: str | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle a flow initialized by the user.

        This is the entry point when a user adds the integration from the UI.

        Args:
            user_input: The user input from the config flow form, or None for initial display.

        Returns:
            The config flow result, either showing a form or creating an entry.

        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Sanitize host input
            user_input[CONF_HOST] = sanitize_host(user_input[CONF_HOST])

            # Use default port if not provided, ensure it's an integer
            if CONF_PORT not in user_input:
                user_input[CONF_PORT] = DEFAULT_PORT
            else:
                user_input[CONF_PORT] = int(user_input[CONF_PORT])

            try:
                chip_id = await validate_connection(
                    self.hass,
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                )
                LOGGER.debug("Connection validated, chip_id: %s", chip_id)
            except Exception as exception:  # noqa: BLE001
                LOGGER.error("Connection validation failed: %s", exception)
                errors["base"] = self._map_exception_to_error(exception)
            else:
                # Set unique ID based on device chip_id
                await self.async_set_unique_id(chip_id)
                self._abort_if_unique_id_configured()

                # Use discovered device name if available (from zeroconf), otherwise chip_id
                title = self._discovered_device_name or f"JAAM {chip_id}"

                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=get_user_schema(user_input),
            errors=errors,
        )

    async def async_step_zeroconf(
        self,
        discovery_info: ZeroconfServiceInfo,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle zeroconf discovery.

        This is called when a JAAM device is discovered via zeroconf.
        The device provides chip_id, version, and device_name in TXT metadata.

        Args:
            discovery_info: The zeroconf discovery information.

        Returns:
            The config flow result, either aborting or showing confirmation form.

        """
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT

        # Extract chip_id, version, and device_name from TXT metadata
        # properties may contain bytes or str, handle both cases
        chip_id_raw = discovery_info.properties.get("chipId") or discovery_info.properties.get("chip_id")
        version_raw = discovery_info.properties.get("version")
        device_name_raw = discovery_info.properties.get("deviceName") or discovery_info.properties.get("device_name")

        # Decode bytes to str if necessary
        chip_id = chip_id_raw.decode() if isinstance(chip_id_raw, bytes) else chip_id_raw
        version = version_raw.decode() if isinstance(version_raw, bytes) else version_raw
        device_name = device_name_raw.decode() if isinstance(device_name_raw, bytes) else device_name_raw

        # Abort if chip_id is missing
        if not chip_id:
            LOGGER.error(
                "Zeroconf discovery failed: missing chip_id in TXT metadata (properties: %s)",
                discovery_info.properties,
            )
            return self.async_abort(reason="cannot_connect")

        LOGGER.info(
            "Discovered JAAM device via zeroconf: %s (chip_id: %s, version: %s) at %s:%s",
            device_name or chip_id,
            chip_id,
            version,
            host,
            port,
        )

        # Set unique ID based on device chip_id from metadata
        await self.async_set_unique_id(str(chip_id))

        # Check if device is already configured
        # If so, update connection details and trigger reload to reconnect
        for entry in self._async_current_entries():
            if entry.unique_id == str(chip_id):
                # Device already configured - check if connection details changed
                if entry.data.get(CONF_HOST) != host or entry.data.get(CONF_PORT) != port:
                    LOGGER.info(
                        "Zeroconf detected device %s at new address: %s:%s -> %s:%s, reloading entry",
                        chip_id,
                        entry.data.get(CONF_HOST),
                        entry.data.get(CONF_PORT),
                        host,
                        port,
                    )
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={**entry.data, CONF_HOST: host, CONF_PORT: port},
                    )
                    # Reload entry to reconnect with new address
                    self.hass.async_create_task(self.hass.config_entries.async_reload(entry.entry_id))
                else:
                    LOGGER.debug(
                        "Zeroconf detected already configured device %s with same connection details",
                        chip_id,
                    )

                return self.async_abort(reason="already_configured")

        # Store discovery info for confirmation step
        # Use device_name from TXT if available, otherwise fallback to chip_id
        display_name = device_name or f"JAAM {chip_id}"
        self.context["title_placeholders"] = {
            "name": display_name,
        }

        # Store discovered data for use in confirmation step
        self._discovered_device_name = display_name
        self._discovered_host = host
        self._discovered_port = port
        self._discovered_chip_id = str(chip_id)

        # Show confirmation form instead of automatically creating entry
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle user confirmation of discovered device.

        Shows a confirmation form where the user can decide whether to add
        the discovered device to Home Assistant.

        Args:
            user_input: The user input from the confirmation form (empty dict on confirm).

        Returns:
            The config flow result, either showing a form or creating an entry.

        """
        if user_input is not None:
            # User confirmed, create config entry with discovered data
            return self.async_create_entry(
                title=self._discovered_device_name or "JAAM",
                data={
                    CONF_HOST: self._discovered_host,
                    CONF_PORT: self._discovered_port,
                },
            )

        # Show confirmation form with device info
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=get_zeroconf_confirm_schema(),
            description_placeholders={
                "name": self._discovered_device_name or "Unknown",
            },
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle reconfiguration of the integration.

        Allows users to update their device host/port without removing and re-adding
        the integration.

        Args:
            user_input: The user input from the reconfigure form, or None for initial display.

        Returns:
            The config flow result, either showing a form or updating the entry.

        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            # Sanitize host input
            user_input[CONF_HOST] = sanitize_host(user_input[CONF_HOST])

            # Use default port if not provided, ensure it's an integer
            if CONF_PORT not in user_input:
                user_input[CONF_PORT] = DEFAULT_PORT
            else:
                user_input[CONF_PORT] = int(user_input[CONF_PORT])

            try:
                await validate_connection(
                    self.hass,
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                )
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_reconfigure_schema(
                entry.data.get(CONF_HOST, ""),
                entry.data.get(CONF_PORT, DEFAULT_PORT),
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle reauthentication when connection fails.

        This flow is automatically triggered when the coordinator catches
        a communication error.

        Args:
            entry_data: The existing entry data (unused, per convention).

        Returns:
            The result of the reauth_confirm step.

        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle reauthentication confirmation.

        Shows the reauthentication form and processes updated connection info.

        Args:
            user_input: The user input with updated connection info, or None for initial display.

        Returns:
            The config flow result, either showing a form or updating the entry.

        """
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            # Sanitize host input
            user_input[CONF_HOST] = sanitize_host(user_input[CONF_HOST])

            # Use default port if not provided, ensure it's an integer
            if CONF_PORT not in user_input:
                user_input[CONF_PORT] = DEFAULT_PORT
            else:
                user_input[CONF_PORT] = int(user_input[CONF_PORT])

            try:
                await validate_connection(
                    self.hass,
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                )
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, **user_input},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=get_reauth_schema(
                entry.data.get(CONF_HOST, ""),
                entry.data.get(CONF_PORT, DEFAULT_PORT),
            ),
            errors=errors,
            description_placeholders={
                "host": entry.data.get(CONF_HOST, ""),
            },
        )

    def _map_exception_to_error(self, exception: Exception) -> str:
        """
        Map API exceptions to user-facing error keys.

        Args:
            exception: The exception that was raised.

        Returns:
            The error key for display in the config flow form.

        """
        LOGGER.warning("Error in config flow: %s", exception)
        exception_name = type(exception).__name__
        return ERROR_MAP.get(exception_name, "unknown")


__all__ = ["JaamHAConfigFlowHandler"]
