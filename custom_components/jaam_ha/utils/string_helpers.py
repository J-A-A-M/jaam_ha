"""String helper utilities for jaam_ha."""

from __future__ import annotations

import re

from custom_components.jaam_ha.const import DEFAULT_DEVICE_TYPE, DEVICE_TYPE_LABELS


def slugify_name(name: str) -> str:
    """
    Convert a name to a slug.

    Example:
        >>> slugify_name("My Device Name")
        'my_device_name'
    """
    # Convert to lowercase and replace spaces/special chars with underscores
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug.strip("_")


def truncate_string(text: str, max_length: int = 255, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        text: The string to truncate
        max_length: Maximum length of the resulting string
        suffix: Suffix to append if truncated

    Returns:
        The truncated string with suffix if needed

    Example:
        >>> truncate_string("This is a very long text", 10)
        'This is...'
    """
    if len(text) <= max_length:
        return text

    truncate_at = max_length - len(suffix)
    return text[:truncate_at].rstrip() + suffix


def sanitize_string(text: str) -> str:
    """
    Remove potentially dangerous characters from a string.

    Args:
        text: The string to sanitize

    Returns:
        A sanitized string safe for use in filenames, IDs, etc.

    Example:
        >>> sanitize_string("My<>Device/Name")
        'MyDeviceName'
    """
    # Remove characters that might be problematic in filenames or IDs
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)


def build_display_name(device_type: str, device_name: str | None, chip_id: str) -> str:
    """
    Build the "<Fusion/Touch label> (<device name or chip id>)" title shown for a device.

    One place for every device-facing title - the discovery card, the config entry (hub)
    title and its later renames - so both device types always read the same way. When the
    device's own name already says it (jaam_touch's default name is literally "JAAM Touch"),
    the label is not repeated: "JAAM Touch", not "JAAM Touch (JAAM Touch)".
    """
    label = DEVICE_TYPE_LABELS.get(device_type, DEVICE_TYPE_LABELS[DEFAULT_DEVICE_TYPE])
    name = device_name or chip_id
    if label.lower() in name.lower():
        return name
    return f"{label} ({name})"
