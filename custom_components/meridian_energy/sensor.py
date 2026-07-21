"""Meridian Energy usage/cost sensor.

Pushes interval usage (and cost, when Meridian includes it) into HA's
recorder as external statistics, for use on the Energy dashboard.

NOTE: the `source`/`readingDirection` values checked below (IMPORT/EXPORT,
GENERATION) are inferred from the GraphQL schema shape, not from a captured
live response -- confirm against real data on first run and adjust the
classification in _direction_of() if Meridian uses different enum values.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .api import MeridianEnergyApi
from .const import CONF_ACCOUNT_NUMBER, DOMAIN, SENSOR_NAME

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=3)

# How far back to pull on every poll. Meridian's own app fetches a rolling
# window rather than incrementally, so we do the same and let the recorder
# de-dupe by statistic id + start time.
LOOKBACK = timedelta(days=10)

_EXPORT_DIRECTIONS = {"EXPORT", "GENERATION"}


def _direction_of(reading: dict) -> str:
    """Classify a reading as 'import' or 'export' consumption."""
    meta = reading.get("metaData") or {}
    filters = meta.get("utilityFilters") or {}
    direction = (filters.get("readingDirection") or "IMPORT").upper()
    return "export" if direction in _EXPORT_DIRECTIONS else "import"


def _reading_cost(reading: dict) -> float | None:
    for stat in (reading.get("metaData") or {}).get("statistics") or []:
        cost = stat.get("costInclTax") or {}
        amount = cost.get("estimatedAmount")
        if amount is not None:
            return float(amount)
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Meridian Energy sensor."""
    api: MeridianEnergyApi = hass.data[DOMAIN][entry.entry_id]
    account_number = entry.data[CONF_ACCOUNT_NUMBER]
    async_add_entities([MeridianEnergyUsageSensor(account_number, api)], True)


class MeridianEnergyUsageSensor(SensorEntity):
    """Pulls Meridian interval usage/cost into recorder external statistics."""

    _attr_icon = "mdi:meter-electric"
    _attr_name = SENSOR_NAME

    def __init__(self, account_number: str, api: MeridianEnergyApi) -> None:
        """Initialise the sensor for a given Meridian account number."""
        self._account_number = account_number
        self._api = api
        self._attr_unique_id = f"{DOMAIN}_{account_number}"
        self._attr_native_value: float | None = None

    async def async_update(self) -> None:
        """Fetch the latest usage window and publish it as statistics."""
        end_at = datetime.now().astimezone()
        start_at = end_at - LOOKBACK

        properties = await self._api.get_measurements(
            self._account_number, start_at=start_at, end_at=end_at
        )

        import_stats: list[StatisticData] = []
        export_stats: list[StatisticData] = []
        cost_stats: list[StatisticData] = []
        import_sum = export_sum = cost_sum = 0.0

        for prop in properties:
            edges = (prop.get("measurements") or {}).get("edges") or []
            for edge in edges:
                node = edge.get("node") or {}
                value = node.get("value")
                read_at = node.get("startAt") or node.get("readAt")
                if value is None or read_at is None:
                    continue

                start = datetime.fromisoformat(read_at).replace(
                    minute=0, second=0, microsecond=0
                )

                if _direction_of(node) == "export":
                    export_sum += float(value)
                    export_stats.append(StatisticData(start=start, sum=export_sum))
                else:
                    import_sum += float(value)
                    import_stats.append(StatisticData(start=start, sum=import_sum))

                cost = _reading_cost(node)
                if cost is not None:
                    cost_sum += cost
                    cost_stats.append(StatisticData(start=start, sum=cost_sum))

        if import_stats:
            async_add_external_statistics(
                self.hass,
                StatisticMetaData(
                    has_mean=False,
                    has_sum=True,
                    name=f"{SENSOR_NAME} (Import)",
                    source=DOMAIN,
                    statistic_id=f"{DOMAIN}:{self._account_number}_import",
                    unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                ),
                import_stats,
            )
            self._attr_native_value = import_sum

        if export_stats:
            async_add_external_statistics(
                self.hass,
                StatisticMetaData(
                    has_mean=False,
                    has_sum=True,
                    name=f"{SENSOR_NAME} (Export)",
                    source=DOMAIN,
                    statistic_id=f"{DOMAIN}:{self._account_number}_export",
                    unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                ),
                export_stats,
            )

        if cost_stats:
            async_add_external_statistics(
                self.hass,
                StatisticMetaData(
                    has_mean=False,
                    has_sum=True,
                    name=f"{SENSOR_NAME} (Cost)",
                    source=DOMAIN,
                    statistic_id=f"{DOMAIN}:{self._account_number}_cost",
                    unit_of_measurement="NZD",
                ),
                cost_stats,
            )
