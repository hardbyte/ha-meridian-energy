"""Constants for the Meridian Energy integration."""

from homeassistant.const import Platform

DOMAIN = "meridian_energy"
SENSOR_NAME = "Meridian Energy"

PLATFORMS = [
    Platform.SENSOR,
]

CONF_TOKENS = "tokens"
CONF_ACCOUNT_NUMBER = "account_number"

BRAND = "meridian"
FIREBASE_API_KEY = "AIzaSyCYCKXQhGmo7haJxAAyO_7mIPrV7jtxsK8"
AUTH_BASE_URL = "https://auth.meridianenergy.nz"
IDENTITY_TOOLKIT_URL = "https://identitytoolkit.googleapis.com/v1"
SECURE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
GRAPHQL_URL = "https://api.meridianenergy.nz/v1/graphql/"

DEFAULT_TIMEZONE = "Pacific/Auckland"
