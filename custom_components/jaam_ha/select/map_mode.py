"""Map mode select for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.select import SelectEntity, SelectEntityDescription

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


# Map mode options
MAP_MODES: dict[str, int] = {
    "disabled": 0,
    "alert": 1,
    "weather": 2,
    "flag": 3,
    "lamp": 4,
}

MAP_MODE_ORDER: list[str] = ["disabled", "alert", "weather", "flag", "lamp"]


ENTITY_DESCRIPTIONS = (
    SelectEntityDescription(
        key="map_mode",
        translation_key="map_mode",
        icon="mdi:map-legend",
        has_entity_name=True,
    ),
)


class JaamHAMapModeSelect(SelectEntity, JaamHAEntity):
    """Map mode select entity."""

    _attr_options = MAP_MODE_ORDER

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
        map_mode_id = self.coordinator.data.get("map_mode_id")
        if map_mode_id is not None:
            # Find the key for the current mode ID
            for key, mode_id in MAP_MODES.items():
                if mode_id == map_mode_id:
                    return key
        return "disabled"  # Default mode

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in MAP_MODES:
            return

        client = self.coordinator.config_entry.runtime_data.client
        mode_id = MAP_MODES[option]
        await client.async_set_map_mode(mode_id)
        await self.coordinator.async_request_refresh()
