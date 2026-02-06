"""
Validators for config flow inputs.

This package contains validation functions for user inputs across all flow types.
Validation logic is organized into separate modules for better maintainability
as the integration grows.

Package structure:
-----------------
- credentials.py: Connection validation
- sanitizers.py: Input sanitization and normalization

When validators grow (>300 lines per file), split further:
- connection/websocket.py, connection/http.py
- sanitizers/text.py, sanitizers/network.py, sanitizers/identifiers.py
- discovery/bluetooth.py, discovery/zeroconf.py, discovery/ssdp.py
- devices/validation.py, devices/discovery.py

All validators are re-exported from this __init__.py for convenient imports.
"""

from __future__ import annotations

from custom_components.jaam_ha.config_flow_handler.validators.credentials import validate_connection
from custom_components.jaam_ha.config_flow_handler.validators.sanitizers import sanitize_host

# Re-export all validators for convenient imports
__all__ = [
    "sanitize_host",
    "validate_connection",
]
