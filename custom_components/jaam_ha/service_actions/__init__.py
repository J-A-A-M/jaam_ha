"""Service actions package for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def async_setup_services(hass: HomeAssistant) -> None:
    """
    Register services for the integration.

    No custom services are currently defined for this integration.
    Standard light entity services (turn_on, turn_off) are automatically
    available through the light platform.
    """
