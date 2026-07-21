"""Constants for the Meridian Energy integration."""

from homeassistant.const import Platform

DOMAIN = "meridian_energy"
SENSOR_NAME = "Meridian Energy"

PLATFORMS = [Platform.SENSOR]

CONF_TOKENS = "tokens"
CONF_ACCOUNT_NUMBER = "account_number"
CONF_EMAIL = "email"

# How far back each poll fetches. New hours are appended via stat cursors;
# already-published hours are skipped. Pagination handles >1500 rows.
LOOKBACK_DAYS = 30
UPDATE_INTERVAL_HOURS = 3
