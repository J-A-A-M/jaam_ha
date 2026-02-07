"""
Data schemas for config flow forms.

This package contains all voluptuous schemas used in config flows and
subentry flows. Schemas are organized into separate modules for better
maintainability as the integration grows.

Package structure:
-----------------
- config.py: Main config flow schemas (user, reauth, reconfigure)

When schemas grow (>300 lines per file), split further:
- config/user.py, config/reauth.py, config/reconfigure.py
- subentries/device.py, subentries/location.py

All schemas are re-exported from this __init__.py for convenient imports.
"""

from __future__ import annotations

from custom_components.jaam_ha.config_flow_handler.schemas.config import (
    get_reauth_schema,
    get_reconfigure_schema,
    get_user_schema,
    get_zeroconf_confirm_schema,
)

# Re-export all schemas for convenient imports
__all__ = [
    "get_reauth_schema",
    "get_reconfigure_schema",
    "get_user_schema",
    "get_zeroconf_confirm_schema",
]
