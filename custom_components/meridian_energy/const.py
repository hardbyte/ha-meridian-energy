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
# Meridian's own Firebase Web API key (project meridian-retail-ciam), taken from
# their public app.meridianenergy.nz bundle. Not a secret: Firebase Web API keys
# only identify the project to Google's client SDKs, access is controlled by
# Firebase Auth/Security Rules, and Meridian's own web/mobile apps ship this same
# key to every user already. Required to call the Identity Toolkit sign-in APIs.
FIREBASE_API_KEY = "AIzaSyCYCKXQhGmo7haJxAAyO_7mIPrV7jtxsK8"
AUTH_BASE_URL = "https://auth.meridianenergy.nz"
IDENTITY_TOOLKIT_URL = "https://identitytoolkit.googleapis.com/v1"
SECURE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
GRAPHQL_URL = "https://api.meridianenergy.nz/v1/graphql/"

DEFAULT_TIMEZONE = "Pacific/Auckland"
