"""DataUpdateCoordinator for Meridian Energy."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from meridian_energy import (
    MeridianEnergyApi,
    ReauthenticationRequiredError,
    UsageSummary,
)
from meridian_energy.errors import MeridianApiError, MeridianAuthError

from .const import DOMAIN, LOOKBACK_DAYS, UPDATE_INTERVAL_HOURS

_LOGGER = logging.getLogger(__name__)


class MeridianCoordinator(DataUpdateCoordinator[UsageSummary]):
    """Fetch usage for one Meridian account."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: MeridianEnergyApi,
        account_number: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the coordinator for a single Meridian account."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
            config_entry=entry,
        )
        self.api = api
        self.account_number = account_number

    async def _async_update_data(self) -> UsageSummary:
        """Pull the latest lookback window of usage from Meridian."""
        try:
            return await self.api.get_usage(
                self.account_number,
                days=LOOKBACK_DAYS,
                include_generation=True,
            )
        except ReauthenticationRequiredError as err:
            raise ConfigEntryAuthFailed("Meridian session expired") from err
        except MeridianAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MeridianApiError as err:
            raise UpdateFailed(str(err)) from err
