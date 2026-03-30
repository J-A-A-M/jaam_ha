"""Map mode select for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import MAP_MODE_ORDER, MAP_MODES
from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.select import SelectEntity, SelectEntityDescription

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    SelectEntityDescription(
        key="map_mode",
        translation_key="map_mode",
        icon="mdi:layers",
        has_entity_name=True,
    ),
)


class JaamHAMapModeSelect(SelectEntity, JaamHAEntity):
    """Map mode select entity."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: SelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entity_description)

    @property
    def options(self) -> list[str]:
        """Return the list of available options, filtered by device support."""
        supported_mode_ids = self.coordinator.data.get("supported_map_modes")
        current_mode_id = self.coordinator.data.get("map_mode_id")

        # If field is not present (None), return all modes (backward compatibility)
        if supported_mode_ids is None:
            return MAP_MODE_ORDER

        # Filter options to only include supported modes
        supported_options = []
        for option in MAP_MODE_ORDER:
            mode_id = MAP_MODES.get(option)
            if mode_id is not None and mode_id in supported_mode_ids:
                supported_options.append(option)

        # If no modes matched, return at least the current mode to avoid empty options
        if not supported_options:
            for option, mode_id in MAP_MODES.items():
                if mode_id == current_mode_id:
                    return [option]
            # Fallback to first option if current mode not found
            return [MAP_MODE_ORDER[0]] if MAP_MODE_ORDER else []

        return supported_options

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        map_mode_id = self.coordinator.data.get("map_mode_id")
        if map_mode_id is not None:
            # Find the key for the current mode ID
            for key, mode_id in MAP_MODES.items():
                if mode_id == map_mode_id:
                    return key
        # Default to first available option if no mode is set
        available_options = self.options
        return available_options[0] if available_options else None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in MAP_MODES:
            return

        client = self.coordinator.config_entry.runtime_data.client
        mode_id = MAP_MODES[option]
        await client.async_set_map_mode(mode_id)
        await self.coordinator.async_request_refresh()
