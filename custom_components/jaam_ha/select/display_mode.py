"""Display mode select for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.select import SelectEntity, SelectEntityDescription

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


# Display mode options
DISPLAY_MODES: dict[str, int] = {
    "off": 0,
    "clock": 1,
    "weather": 2,
    "technical": 3,
    "microclimate": 4,
    "combined": 9,
}

DISPLAY_MODE_ORDER: list[str] = [
    "off",
    "clock",
    "weather",
    "technical",
    "microclimate",
    "combined",
]


ENTITY_DESCRIPTIONS = (
    SelectEntityDescription(
        key="display_mode",
        translation_key="display_mode",
        icon="mdi:monitor",
        has_entity_name=True,
    ),
)


class JaamHADisplayModeSelect(SelectEntity, JaamHAEntity):
    """Display mode select entity."""

    _attr_options = DISPLAY_MODE_ORDER

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: SelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entity_description)

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        display_mode_id = self.coordinator.data.get("display_mode_id")
        if display_mode_id is not None:
            # Find the key for the current mode ID
            for key, mode_id in DISPLAY_MODES.items():
                if mode_id == display_mode_id:
                    return key
        return "off"  # Default mode

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in DISPLAY_MODES:
            return

        client = self.coordinator.config_entry.runtime_data.client
        mode_id = DISPLAY_MODES[option]
        await client.async_set_display_mode(mode_id)
        await self.coordinator.async_request_refresh()
