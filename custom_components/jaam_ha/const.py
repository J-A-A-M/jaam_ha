"""Constants for jaam_ha."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN = "jaam_ha"
ATTRIBUTION = "Data provided by JAAM device"

# Platform parallel updates - applied to all platforms
PARALLEL_UPDATES = 1

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
DEFAULT_PORT = 81

# Map mode IDs
MAP_MODE_DISABLED = 0
MAP_MODE_ALERT = 1
MAP_MODE_WEATHER = 2
MAP_MODE_FLAG = 3
MAP_MODE_RANDOM = 4
MAP_MODE_LAMP = 5
MAP_MODE_ENERGY_SYSTEM = 6
MAP_MODE_RADIATION = 7

# Map modes mapping (option_name -> mode_id)
MAP_MODES: dict[str, int] = {
    "disabled": MAP_MODE_DISABLED,
    "alert": MAP_MODE_ALERT,
    "energy_system": MAP_MODE_ENERGY_SYSTEM,
    "weather": MAP_MODE_WEATHER,
    "radiation": MAP_MODE_RADIATION,
    "flag": MAP_MODE_FLAG,
    "random": MAP_MODE_RANDOM,
    "lamp": MAP_MODE_LAMP,
}

# Map mode options order for select entity
MAP_MODE_ORDER: list[str] = [
    "disabled",
    "alert",
    "energy_system",
    "weather",
    "radiation",
    "flag",
    "random",
    "lamp",
]

# Display mode IDs
DISPLAY_MODE_OFF = 0
DISPLAY_MODE_CLOCK = 1
DISPLAY_MODE_WEATHER = 2
DISPLAY_MODE_TECHNICAL = 3
DISPLAY_MODE_MICROCLIMATE = 4
DISPLAY_MODE_ENERGY_SYSTEM = 5
DISPLAY_MODE_RADIATION = 6
DISPLAY_MODE_COMBINED = 9

# Display modes mapping (option_name -> mode_id)
DISPLAY_MODES: dict[str, int] = {
    "off": DISPLAY_MODE_OFF,
    "clock": DISPLAY_MODE_CLOCK,
    "energy_system": DISPLAY_MODE_ENERGY_SYSTEM,
    "weather": DISPLAY_MODE_WEATHER,
    "radiation": DISPLAY_MODE_RADIATION,
    "technical": DISPLAY_MODE_TECHNICAL,
    "microclimate": DISPLAY_MODE_MICROCLIMATE,
    "combined": DISPLAY_MODE_COMBINED,
}

# Display mode options order for select entity
DISPLAY_MODE_ORDER: list[str] = [
    "off",
    "clock",
    "energy_system",
    "weather",
    "radiation",
    "technical",
    "microclimate",
    "combined",
]
