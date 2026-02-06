"""Lamp light for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, LightEntity, LightEntityDescription
from homeassistant.components.light.const import ColorMode

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    LightEntityDescription(
        key="lamp",
        translation_key="lamp",
        has_entity_name=True,
    ),
)


class JaamHALampLight(JaamHAEntity, LightEntity):
    """Representation of the JAAM Lamp light."""

    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: LightEntityDescription,
    ) -> None:
        """Initialize the lamp light."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        # Light is on if we have data and map_mode is LAMP (mode_id = 4)
        if self.coordinator.data:
            return self.coordinator.data.get("map_mode_id") == 4
        return False

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if self.coordinator.data:
            # Convert from 0-100 to 0-255
            brightness_percent = self.coordinator.data.get("lamp_brightness")
            if brightness_percent is not None:
                return int((brightness_percent / 100) * 255)
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value."""
        if self.coordinator.data:
            color_hex = self.coordinator.data.get("lamp_color")
            if color_hex and isinstance(color_hex, str):
                # Convert hex color (#RRGGBB) to RGB tuple
                color_hex = color_hex.lstrip("#")
                if len(color_hex) == 6:
                    try:
                        return (
                            int(color_hex[0:2], 16),
                            int(color_hex[2:4], 16),
                            int(color_hex[4:6], 16),
                        )
                    except ValueError:
                        return None
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        client = self.coordinator.config_entry.runtime_data.client

        # Extract color and brightness from kwargs
        rgb_color = kwargs.get(ATTR_RGB_COLOR)
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        # Convert RGB to hex if provided
        color_hex = None
        if rgb_color is not None:
            color_hex = f"#{rgb_color[0]:02x}{rgb_color[1]:02x}{rgb_color[2]:02x}"

        # Convert brightness from 0-255 to 0-100 if provided
        brightness_percent = None
        if brightness is not None:
            brightness_percent = int((brightness / 255) * 100)

        # If just turning on without parameters, use current values or defaults
        if color_hex is None and brightness_percent is None:
            # Use current values if available
            if self.coordinator.data:
                color_hex = self.coordinator.data.get("lamp_color")
                brightness_percent = self.coordinator.data.get("lamp_brightness")
            # Use defaults if no current values
            if color_hex is None:
                color_hex = "#FFFFFF"
            if brightness_percent is None:
                brightness_percent = 100

        # First, set lamp mode (mode_id = 4)
        await client.async_set_map_mode(4)

        # Then set color and brightness
        await client.async_set_lamp(color=color_hex, brightness=brightness_percent)

        # Request coordinator refresh to update state
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        client = self.coordinator.config_entry.runtime_data.client

        # Set map mode to ALERTS (mode_id = 1)
        await client.async_set_map_mode(1)

        # Request coordinator refresh to update state
        await self.coordinator.async_request_refresh()
