"""
Config flow handler for jaam_ha.

This module provides backwards compatibility by re-exporting the flow handlers
from their respective modules. The actual implementation is split across:

- config_flow.py: Main config flow (user, reauth, reconfigure)
- subentry_flow.py: Template for future subentry flows
- schemas/: Voluptuous schemas for all forms
- validators/: Validation logic for user inputs

This structure keeps the code organized while allowing complex flows to grow
without becoming monolithic.

For more information:
https://developers.home-assistant.io/docs/config_entries_config_flow_handler
"""

from __future__ import annotations

from custom_components.jaam_ha.config_flow_handler.config_flow import JaamHAConfigFlowHandler

# Re-export for backwards compatibility and external imports
__all__ = [
    "JaamHAConfigFlowHandler",
]
