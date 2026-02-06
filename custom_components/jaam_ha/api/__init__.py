"""API package for jaam_ha."""

from .client import (
    JaamHAApiClient,
    JaamHAApiClientAuthenticationError,
    JaamHAApiClientCommunicationError,
    JaamHAApiClientError,
)

__all__ = [
    "JaamHAApiClient",
    "JaamHAApiClientAuthenticationError",
    "JaamHAApiClientCommunicationError",
    "JaamHAApiClientError",
]
