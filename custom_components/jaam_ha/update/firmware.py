"""Firmware update entity for jaam_ha."""

from __future__ import annotations

import asyncio
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

ENTITY_DESCRIPTIONS = (
    UpdateEntityDescription(
        key="firmware",
        translation_key="firmware",
        device_class=UpdateDeviceClass.FIRMWARE,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
    ),
)


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

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend.

        Returns different icons based on update availability:
        - mdi:package-up: Update available
        - mdi:package-check: No update available (up to date)
        """
        installed = self.installed_version
        latest = self.latest_version

        # Show update available icon if versions differ
        if installed and latest and installed != latest:
            return "mdi:package-up"

        # Show up-to-date icon when versions match or no latest version
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
        """
        return self.update_percentage is not None

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

        try:
            # Send update command to device via API client
            client = self.coordinator.config_entry.runtime_data.client
            await client.async_update_firmware(target_version)
            LOGGER.info("Firmware update command sent successfully")

            # Request coordinator refresh to update state
            await self.coordinator.async_request_refresh()

        except Exception as exc:
            LOGGER.error("Failed to start firmware update: %s", exc)
            raise
