"""Custom types for jaam_ha."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import JaamHAApiClient
    from .coordinator import JaamHADataUpdateCoordinator


type JaamHAConfigEntry = ConfigEntry[JaamHAData]


@dataclass
class JaamHAData:
    """Data for jaam_ha."""

    client: JaamHAApiClient
    coordinator: JaamHADataUpdateCoordinator
    integration: Integration
