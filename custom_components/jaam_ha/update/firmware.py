"""Firmware update entity for jaam_ha."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

import aiohttp

from custom_components.jaam_ha.const import LOGGER
from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator

# GitHub repository URL for firmware releases
FIRMWARE_REPO_URL = "https://github.com/J-A-A-M/jaam_fusion"
GITHUB_API_URL = "https://api.github.com/repos/J-A-A-M/jaam_fusion"

# Regex pattern for parsing version strings (e.g., 5.0, 5.0.1, 5.0-b32, 5.0.1-b32)
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?(?:-b(\d+))?$")

ENTITY_DESCRIPTIONS = (
    UpdateEntityDescription(
        key="firmware",
        translation_key="firmware",
        device_class=UpdateDeviceClass.FIRMWARE,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
    ),
)


def parse_version(version: str) -> tuple[int, int, int, int] | None:
    """Parse version string into comparable tuple.

    Args:
        version: Version string (e.g., "5.0", "5.0.1", "5.0-b32", "5.0.1-b32")

    Returns:
        Tuple of (major, minor, patch, beta) where beta is 0 for release versions
        or beta number for beta versions. Returns None if parsing fails.

    Examples:
        "5.0" -> (5, 0, 0, 0)
        "5.0.1" -> (5, 0, 1, 0)
        "5.0-b32" -> (5, 0, 0, 32)
        "5.0.1-b32" -> (5, 0, 1, 32)
    """
    match = VERSION_PATTERN.match(version)
    if not match:
        return None

    major, minor, patch, beta = match.groups()
    return (int(major), int(minor), int(patch) if patch else 0, int(beta) if beta else 0)


class JaamHAFirmwareUpdate(UpdateEntity, JaamHAEntity):
    """Firmware update entity class."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: UpdateEntityDescription,
    ) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator, entity_description)

        # Support firmware installation, progress tracking, and release notes
        self._attr_supported_features = (
            UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS | UpdateEntityFeature.RELEASE_NOTES
        )

        # Cache for release notes (version -> release_notes)
        self._release_notes_cache: dict[str, str | None] = {}

        # Track last progress to detect changes
        self._last_progress: int | None = None

        # Track if installation was initiated (before coordinator data arrives)
        self._installation_initiated: bool = False

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Check if progress changed
        current_progress = self.coordinator.data.get("fw_update_progress") if self.coordinator.data else None

        if current_progress != self._last_progress:
            LOGGER.debug(
                "Firmware update progress changed from %s to %s",
                self._last_progress,
                current_progress,
            )
            self._last_progress = current_progress

        # Clear installation initiated flag when coordinator data arrives
        if current_progress is not None:
            # Progress data received - installation is confirmed by device
            self._installation_initiated = False
        elif self._installation_initiated and current_progress is None:
            # Installation was initiated but progress is None - update may have completed or failed
            # Keep the flag until we get actual progress or next coordinator update confirms completion
            pass

        # Always call parent to update the entity
        super()._handle_coordinator_update()

    @property
    def installed_version(self) -> str | None:
        """Return the installed firmware version."""
        if self.coordinator.data is None:
            return None

        return self.coordinator.data.get("fw_version")

    @property
    def latest_version(self) -> str | None:
        """Return the latest firmware version.

        Returns fw_latest from device if available, otherwise falls back
        to installed version.
        """
        if self.coordinator.data is None:
            return None

        return self.coordinator.data.get("fw_latest") or self.installed_version

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Return True if latest_version is newer than installed_version.

        Custom version comparison logic:
        - Release version (without -b suffix) is always newer than beta with same X.Y.Z
        - Example: "5.0.1" is newer than "5.0.1-b32"
        - Standard semantic versioning applies otherwise

        Args:
            latest_version: Latest available version
            installed_version: Currently installed version

        Returns:
            True if latest_version is newer than installed_version
        """
        if latest_version == installed_version:
            return False

        latest_parsed = parse_version(latest_version)
        installed_parsed = parse_version(installed_version)

        # If either version fails to parse, fall back to string comparison
        if not latest_parsed or not installed_parsed:
            LOGGER.debug(
                "Version parsing failed, using string comparison: %s vs %s",
                latest_version,
                installed_version,
            )
            return latest_version != installed_version

        latest_major, latest_minor, latest_patch, latest_beta = latest_parsed
        installed_major, installed_minor, installed_patch, installed_beta = installed_parsed

        # Compare major.minor.patch first
        if (latest_major, latest_minor, latest_patch) > (installed_major, installed_minor, installed_patch):
            return True
        if (latest_major, latest_minor, latest_patch) < (installed_major, installed_minor, installed_patch):
            return False

        # Same X.Y.Z - now compare beta status
        # If installed is beta and latest is release (beta=0), update is available
        if installed_beta > 0 and latest_beta == 0:
            return True

        # If installed is release and latest is beta, no update available
        if installed_beta == 0 and latest_beta > 0:
            return False

        # Both beta or both release - compare beta numbers
        return latest_beta > installed_beta

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend.

        Returns different icons based on update availability:
        - mdi:package-up: Update available
        - mdi:package-check: No update available (up to date)
        """
        installed = self.installed_version
        latest = self.latest_version

        # Show update available icon if versions differ and update is available
        if installed and latest and self.version_is_newer(latest, installed):
            return "mdi:package-up"

        # Show up-to-date icon when versions match or no update available
        return "mdi:package-check"

    @property
    def release_url(self) -> str | None:
        """Return the URL to the GitHub releases page.

        If latest_version is available, returns URL to specific release tag.
        Otherwise returns URL to the releases page.
        """
        version = self.latest_version
        if version:
            # GitHub releases use version without 'v' prefix (e.g., 5.0.1)
            # Support versions like: 5.0.1, 5.1, 5.1.3-b32
            return f"{FIRMWARE_REPO_URL}/releases/tag/{version}"

        # Fallback to releases page if no version available
        return f"{FIRMWARE_REPO_URL}/releases"

    async def async_release_notes(self) -> str | None:
        """Return the release notes.

        Fetches release notes from GitHub API and caches them.
        The returned string can contain markdown.
        """
        version = self.latest_version
        if not version:
            return None

        # Return cached value if available
        if version in self._release_notes_cache:
            return self._release_notes_cache[version]

        # Fetch release notes from GitHub
        try:
            session = async_get_clientsession(self.hass)
            url = f"{GITHUB_API_URL}/releases/tags/{version}"

            async with asyncio.timeout(10):
                async with session.get(
                    url,
                    headers={"Accept": "application/vnd.github.v3+json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        release_body = data.get("body", "")

                        # Cache the result
                        self._release_notes_cache[version] = release_body or None

                        LOGGER.debug(
                            "Fetched release notes for version %s (%d chars)",
                            version,
                            len(release_body) if release_body else 0,
                        )
                        return release_body or None

                    if response.status == 404:
                        # Release not found, cache None to avoid repeated requests
                        self._release_notes_cache[version] = None
                        LOGGER.debug("No release found on GitHub for version %s", version)
                        return None

                    LOGGER.warning(
                        "GitHub API returned status %d for version %s",
                        response.status,
                        version,
                    )
                    return None

        except TimeoutError:
            LOGGER.warning("Timeout fetching release notes for version %s", version)
            return None
        except aiohttp.ClientError as exc:
            LOGGER.warning("Error fetching release notes for version %s: %s", version, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Unexpected error fetching release notes: %s", exc)
            return None

    @property
    def update_percentage(self) -> int | None:
        """Return firmware update progress percentage.

        Returns:
            None if no update in progress.
            Integer percentage (0-100) if update is in progress.
        """
        if self.coordinator.data is None:
            return None

        progress = self.coordinator.data.get("fw_update_progress")
        if progress is None:
            return None

        # Return progress percentage (0-100)
        return progress

    @property
    def in_progress(self) -> bool:
        """Return True if update is in progress.

        This is used by Home Assistant to determine if installation is ongoing.
        Returns True if:
        - Installation was initiated locally (before coordinator data arrives)
        - OR update progress data is available from coordinator
        """
        return self._installation_initiated or self.update_percentage is not None

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install an update.

        Version can be specified to install a specific version. When `None`, the
        latest version needs to be installed.

        The backup parameter indicates a backup should be taken before
        installing the update (ignored for this device).
        """
        # Use latest_version if no specific version provided
        target_version = version or self.latest_version

        if not target_version:
            LOGGER.error("No firmware version available for installation")
            return

        LOGGER.info("Starting firmware update to version %s", target_version)

        # Mark installation as initiated immediately
        self._installation_initiated = True
        # Update state to show in_progress immediately
        self.async_write_ha_state()

        try:
            # Send update command to device via API client
            client = self.coordinator.config_entry.runtime_data.client
            await client.async_update_firmware(target_version)
            LOGGER.info("Firmware update command sent successfully")

            # Request coordinator refresh to update state
            await self.coordinator.async_request_refresh()

        except Exception as exc:
            LOGGER.error("Failed to start firmware update: %s", exc)
            # Clear installation flag on error
            self._installation_initiated = False
            self.async_write_ha_state()
            raise
