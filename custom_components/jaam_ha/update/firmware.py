"""Firmware update entity for jaam_ha."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

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

        # Support firmware installation
        self._attr_supported_features = UpdateEntityFeature.INSTALL

        # Cache for release notes (version -> release_notes)
        self._release_notes_cache: dict[str, str | None] = {}

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

    @property
    def release_summary(self) -> str | None:
        """Return the release summary/changelog.

        This is fetched from GitHub API asynchronously and cached.
        Returns cached value if available, None otherwise.
        Triggers async fetch in background if not cached.
        """
        version = self.latest_version
        if not version:
            return None

        # Return cached value if available
        if version in self._release_notes_cache:
            return self._release_notes_cache[version]

        # Trigger background fetch if not in cache
        self.hass.async_create_task(self._fetch_release_notes(version))
        return None

    async def _fetch_release_notes(self, version: str) -> None:
        """Fetch release notes from GitHub API.

        Args:
            version: Version tag to fetch release notes for.

        """
        # Check if already cached
        if version in self._release_notes_cache:
            return

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

                        # Trigger entity update to show the changelog
                        self.async_write_ha_state()

                        LOGGER.debug(
                            "Fetched release notes for version %s (%d chars)",
                            version,
                            len(release_body) if release_body else 0,
                        )
                    elif response.status == 404:
                        # Release not found, cache None to avoid repeated requests
                        self._release_notes_cache[version] = None
                        LOGGER.debug("No release found on GitHub for version %s", version)
                    else:
                        LOGGER.warning(
                            "GitHub API returned status %d for version %s",
                            response.status,
                            version,
                        )

        except TimeoutError:
            LOGGER.warning("Timeout fetching release notes for version %s", version)
        except aiohttp.ClientError as exc:
            LOGGER.warning("Error fetching release notes for version %s: %s", version, exc)
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Unexpected error fetching release notes: %s", exc)

    @property
    def in_progress(self) -> bool | int:
        """Return firmware update progress.

        Returns:
            False if no update in progress.
            Integer percentage (0-100) if update is in progress.
        """
        if self.coordinator.data is None:
            return False

        progress = self.coordinator.data.get("fw_update_progress")
        if progress is None:
            return False

        # Return progress percentage (0-100)
        return progress

    async def async_install(self, version: str | None, backup: bool, **kwargs: object) -> None:
        """Install firmware update.

        Args:
            version: Version to install (None for latest_version).
            backup: Whether to backup before update (ignored for this device).
            **kwargs: Additional arguments (ignored).

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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        await super().async_will_remove_from_hass()
