"""
Input sanitizers and normalizers.

Functions for cleaning and normalizing user inputs.

When adding many sanitizers, consider organizing by type:
- text.py: Text input sanitizers
- network.py: URL, host, port sanitizers
- identifiers.py: Device ID, serial number normalizers
"""

from __future__ import annotations


def sanitize_host(host: str) -> str:
    """
    Sanitize host input.

    Removes whitespace and converts to lowercase for consistency.

    Args:
        host: Raw host input (hostname or IP address).

    Returns:
        Sanitized host.

    """
    return host.strip().lower()


__all__ = [
    "sanitize_host",
]
