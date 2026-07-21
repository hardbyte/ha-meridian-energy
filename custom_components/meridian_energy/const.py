"""Constants for the Meridian Energy integration."""

from homeassistant.const import Platform

DOMAIN = "meridian_energy"
SENSOR_NAME = "Meridian Energy"

PLATFORMS = [Platform.SENSOR]

CONF_TOKENS = "tokens"
CONF_ACCOUNT_NUMBER = "account_number"
CONF_EMAIL = "email"

# How far back each poll re-publishes. HA recorder de-dupes by statistic id + start.
LOOKBACK_DAYS = 10
UPDATE_INTERVAL_HOURS = 3
