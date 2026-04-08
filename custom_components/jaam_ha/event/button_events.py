"""Button events entity for jaam_ha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.jaam_ha.const import LOGGER
from custom_components.jaam_ha.entity import JaamHAEntity
from homeassistant.components.event import EventDeviceClass, EventEntity, EventEntityDescription

if TYPE_CHECKING:
    from custom_components.jaam_ha.coordinator import JaamHADataUpdateCoordinator


ENTITY_DESCRIPTIONS = (
    EventEntityDescription(
        key="button_events",
        translation_key="button_events",
        has_entity_name=True,
        device_class=EventDeviceClass.BUTTON,
    ),
)


class JaamHAButtonEventsEntity(EventEntity, JaamHAEntity):
    """Event entity for button events (all buttons)."""

    # Event types that this entity can generate
    _attr_event_types = ["click", "long_click"]

    def __init__(
        self,
        coordinator: JaamHADataUpdateCoordinator,
        entity_description: EventEntityDescription,
    ) -> None:
        """Initialize the event entity."""
        super().__init__(coordinator, entity_description)
        self._last_button_event: dict | None = None

    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.

        Called when coordinator receives new data from WebSocket.
        Checks if there's a new button_event and triggers the event.
        """
        super()._handle_coordinator_update()

        # Get button event data from coordinator.data
        button_event = self.coordinator.data.get("button_event")

        # Check if this is a new event (not the same as already processed)
        # Each event has unique timestamp, so repeated button presses will trigger
        if button_event and button_event != self._last_button_event:
            button_id = button_event.get("buttonId")
            event_type = button_event.get("event")

            # Validate event type
            if event_type in self._attr_event_types and button_id is not None:
                LOGGER.debug(
                    "Button event received - button_id: %s, event: %s",
                    button_id,
                    event_type,
                )

                # Remember last event BEFORE triggering (so icon property sees new data)
                self._last_button_event = button_event.copy()

                # Trigger event in Home Assistant
                self._trigger_event(
                    event_type,
                    {"button_id": button_id},
                )
                self.async_write_ha_state()

    @property
    def icon(self) -> str:
        """Return dynamic icon based on last event."""
        if not self._last_button_event:
            return "mdi:gesture-tap-button"

        button_id = self._last_button_event.get("buttonId")
        event_type = self._last_button_event.get("event")

        # Validate button_id and event_type
        if button_id is None or event_type is None:
            return "mdi:gesture-tap-button"

        # Icon mapping: button_id + event_type
        # Click = filled box, Long Click = outline box
        icon_map = {
            (1, "click"): "mdi:numeric-1-box",
            (1, "long_click"): "mdi:numeric-1-box-outline",
            (2, "click"): "mdi:numeric-2-box",
            (2, "long_click"): "mdi:numeric-2-box-outline",
            (3, "click"): "mdi:numeric-3-box",
            (3, "long_click"): "mdi:numeric-3-box-outline",
        }

        return icon_map.get((button_id, event_type), "mdi:gesture-tap-button")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is available if coordinator is available
        # and button_events is in supported_sensors
        if not super().available:
            return False

        supported_sensors = self.coordinator.data.get("supported_sensors", [])
        return "button_events" in supported_sensors
