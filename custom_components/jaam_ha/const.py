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
