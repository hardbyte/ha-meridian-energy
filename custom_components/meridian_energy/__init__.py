"""The Meridian Energy integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.httpx_client import get_async_client
from meridian_energy import (
    MeridianEnergyApi,
    MeridianEnergyAuth,
    ReauthenticationRequiredError,
    TokenSet,
)

from .const import CONF_ACCOUNT_NUMBER, CONF_TOKENS, PLATFORMS
from .coordinator import MeridianCoordinator

_LOGGER = logging.getLogger(__name__)

MeridianConfigEntry = ConfigEntry[MeridianCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MeridianConfigEntry) -> bool:
    """Set up Meridian Energy from a config entry."""

    async def on_token_update(tokens: TokenSet) -> None:
        """Persist refreshed Firebase tokens onto the config entry."""
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_TOKENS: tokens.to_dict()}
        )

    try:
        tokens = TokenSet.from_dict(entry.data[CONF_TOKENS])
    except (KeyError, TypeError, ValueError) as err:
        raise ConfigEntryAuthFailed("Stored Meridian tokens are invalid") from err

    httpx_client = get_async_client(hass)
    auth = MeridianEnergyAuth(
        tokens=tokens,
        on_token_update=on_token_update,
        httpx_client=httpx_client,
    )
    api = MeridianEnergyApi(
        auth,
        httpx_client,
        owns_client=False,
    )
    account_number = entry.data[CONF_ACCOUNT_NUMBER]
    coordinator = MeridianCoordinator(hass, api, account_number, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except ReauthenticationRequiredError as err:
        raise ConfigEntryAuthFailed("Meridian session expired") from err

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MeridianConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
