"""jaam_touch reboot button for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    ButtonEntityDescription(
        key="reboot",
        translation_key="reboot",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        has_entity_name=True,
    ),
)


class JaamHARebootButton(ButtonEntity, JaamHAEntity):
    """jaam_touch reboot button entity.

    jaam_touch-only - jaam_fusion's JaamApi has no WS reboot command (its only reboot
    path is the unauthenticated LogServer-equivalent HTTP endpoint, which this
    integration doesn't talk to at all).
    """

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator, entity_description)

    async def async_press(self) -> None:
        """Reboot the device."""
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_reboot()
