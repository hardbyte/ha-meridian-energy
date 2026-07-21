"""Config flow for the Meridian Energy integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_EMAIL
from homeassistant.helpers.httpx_client import get_async_client

from .api import MeridianAuthError, MeridianEnergyApi, MeridianEnergyAuth
from .const import CONF_ACCOUNT_NUMBER, CONF_TOKENS, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_EMAIL): str})
STEP_OTP_DATA_SCHEMA = vol.Schema({vol.Required("otp"): str})


class MeridianEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Meridian Energy."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise flow state."""
        self._email: str | None = None
        self._journey_id: str | None = None
        self._auth: MeridianEnergyAuth | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the account email and request an OTP."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            client = get_async_client(self.hass)
            self._auth = MeridianEnergyAuth()
            try:
                self._journey_id = await self._auth.request_otp(client, email)
            except MeridianAuthError as err:
                _LOGGER.debug("OTP request failed: %s", err)
                errors["base"] = "invalid_email"
            else:
                self._email = email
                return await self.async_step_otp()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Verify the emailed OTP code and finish setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._auth is not None
            assert self._email is not None
            assert self._journey_id is not None
            client = get_async_client(self.hass)
            try:
                await self._auth.verify_otp(
                    client, self._email, user_input["otp"].strip(), self._journey_id
                )
                api = MeridianEnergyApi(self._auth, client)
                accounts = await api.get_accounts()
            except MeridianAuthError as err:
                _LOGGER.debug("OTP verification failed: %s", err)
                errors["base"] = "invalid_otp"
            else:
                if not accounts:
                    return self.async_abort(reason="no_accounts")

                account_number = accounts[0]["number"]
                assert self._auth.tokens is not None

                await self.async_set_unique_id(account_number)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Meridian Energy ({account_number})",
                    data={
                        CONF_EMAIL: self._email,
                        CONF_ACCOUNT_NUMBER: account_number,
                        CONF_TOKENS: self._auth.tokens.to_dict(),
                    },
                )

        return self.async_show_form(
            step_id="otp",
            data_schema=STEP_OTP_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"email": self._email or ""},
        )
