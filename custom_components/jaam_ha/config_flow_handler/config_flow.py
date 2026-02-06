"""
Config flow for jaam_ha.

This module implements the main configuration flow including:
- Initial user setup
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
)
from custom_components.jaam_ha.config_flow_handler.validators import sanitize_host, validate_connection
from custom_components.jaam_ha.const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN, LOGGER
from homeassistant import config_entries

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
    - reconfigure: Update existing configuration
    - reauth: Handle connection issues

    For more details:
    https://developers.home-assistant.io/docs/config_entries_config_flow_handler
    """

    VERSION = 1

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
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                # Set unique ID based on device chip_id
                await self.async_set_unique_id(chip_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"JAAM {user_input[CONF_HOST]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=get_user_schema(user_input),
            errors=errors,
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
