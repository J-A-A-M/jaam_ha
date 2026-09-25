"""jaam_touch UI sound switch for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="sound_enabled",
        translation_key="sound_enabled",
        icon="mdi:volume-high",
        has_entity_name=True,
    ),
)


class JaamHASoundSwitch(SwitchEntity, JaamHAEntity):
    """jaam_touch UI sound switch entity."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool | None:
        """Return True if the switch is on."""
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.entity_description.key in self.coordinator.data
            and self.coordinator.data.get(self.entity_description.key) is not None
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_sound_enabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_sound_enabled(False)
        await self.coordinator.async_request_refresh()
