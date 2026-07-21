"""The Meridian Energy integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from .api import MeridianEnergyApi, MeridianEnergyAuth, MeridianTokenSet
from .const import CONF_TOKENS, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Meridian Energy from a config entry."""

    async def on_token_update(tokens: MeridianTokenSet) -> None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_TOKENS: tokens.to_dict()}
        )

    tokens = MeridianTokenSet.from_dict(entry.data[CONF_TOKENS])
    auth = MeridianEnergyAuth(tokens=tokens, on_token_update=on_token_update)
    api = MeridianEnergyApi(auth, get_async_client(hass))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
