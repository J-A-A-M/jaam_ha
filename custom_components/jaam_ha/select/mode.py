"""jaam_touch display mode select for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import TOUCH_MODE_ORDER
from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.select import SelectEntity, SelectEntityDescription

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    SelectEntityDescription(
        key="mode",
        translation_key="mode",
        icon="mdi:view-dashboard",
        has_entity_name=True,
    ),
)


class JaamHATouchModeSelect(SelectEntity, JaamHAEntity):
    """jaam_touch mode select entity (alarm_map/weather/radiation/energy)."""

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: SelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entity_description)

    @property
    def options(self) -> list[str]:
        """Return the list of available options.

        Only the modes enabled in the device's menu; all of them if the firmware doesn't
        report `enabled_modes` (older versions).
        """
        enabled = self.coordinator.data.get("enabled_modes")
        if enabled is None:
            return TOUCH_MODE_ORDER
        return [mode for mode in TOUCH_MODE_ORDER if mode in enabled]

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.data.get("mode")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self.options:
            return

        client = self.coordinator.config_entry.runtime_data.client
        await client.async_set_touch_mode(option)
        await self.coordinator.async_request_refresh()
