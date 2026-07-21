"""Meridian Energy usage sensors and external statistics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics

try:
    from homeassistant.components.recorder.models import StatisticMeanType
except ImportError:  # pragma: no cover - older HA
    StatisticMeanType = None  # type: ignore[misc, assignment]
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from meridian_energy import (
    StatisticCursor,
    UsageSummary,
    build_incremental_statistics,
)

from . import MeridianConfigEntry
from .const import DOMAIN, SENSOR_NAME
from .coordinator import MeridianCoordinator

_LOGGER = logging.getLogger(__name__)

CONF_STAT_CURSORS = "stat_cursors"


def _statistic_slug(account_number: str) -> str:
    """Return a HA-valid external statistic object id for an account.

    External statistic ids must match ``domain:object_id`` where object_id is
    lowercase ``[a-z0-9_]+`` only — Meridian account numbers like ``A-1B9AC44D``
    need normalising.
    """
    slug = "".join(
        ch.lower() if ch.isalnum() else "_" for ch in account_number
    ).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "account"


def _cursor_from_dict(data: dict[str, Any] | None) -> StatisticCursor:
    """Load a statistic cursor from config entry data."""
    if not data:
        return StatisticCursor()
    last_start = data.get("last_start")
    if isinstance(last_start, str):
        last_start = datetime.fromisoformat(last_start)
    return StatisticCursor(sum=float(data.get("sum") or 0.0), last_start=last_start)


def _cursor_to_dict(cursor: StatisticCursor) -> dict[str, Any]:
    """Serialise a statistic cursor for config entry storage."""
    return {
        "sum": cursor.sum,
        "last_start": cursor.last_start.isoformat() if cursor.last_start else None,
    }


def _as_utc(value: datetime) -> datetime:
    """Normalise statistic timestamps to UTC (HA preference)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeridianConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Meridian Energy sensors from a config entry."""
    coordinator = entry.runtime_data
    account_number = coordinator.account_number
    async_add_entities(
        [
            MeridianImportSensor(coordinator, account_number),
            MeridianExportSensor(coordinator, account_number),
            MeridianCostSensor(coordinator, account_number),
        ]
    )

    def _on_update() -> None:
        _publish_statistics(hass, entry, coordinator)

    entry.async_on_unload(coordinator.async_add_listener(_on_update))
    _publish_statistics(hass, entry, coordinator)


@callback
def _publish_statistics(
    hass: HomeAssistant,
    entry: MeridianConfigEntry,
    coordinator: MeridianCoordinator,
) -> None:
    """Push new hourly deltas into recorder external statistics.

    Uses persisted cursors so cumulative sums only ever increase and sliding
    lookback windows cannot rewrite earlier history downward.
    """
    summary = coordinator.data
    if summary is None:
        return
    slug = _statistic_slug(coordinator.account_number)
    stored = dict(entry.data.get(CONF_STAT_CURSORS) or {})
    updated_cursors: dict[str, Any] = {}

    series = (
        ("import", f"{DOMAIN}:{slug}_import", UnitOfEnergy.KILO_WATT_HOUR, "energy"),
        ("export", f"{DOMAIN}:{slug}_export", UnitOfEnergy.KILO_WATT_HOUR, "energy"),
        ("cost", f"{DOMAIN}:{slug}_cost", "NZD", None),
    )

    for kind, statistic_id, unit, unit_class in series:
        points, cursor = build_incremental_statistics(
            summary.hourly,
            kind=kind,  # type: ignore[arg-type]
            cursor=_cursor_from_dict(stored.get(kind)),
        )
        updated_cursors[kind] = _cursor_to_dict(cursor)
        if not points:
            continue
        stats = [
            StatisticData(start=_as_utc(point.start), sum=point.sum) for point in points
        ]
        async_add_external_statistics(
            hass,
            _statistic_metadata(
                name=f"{SENSOR_NAME} ({kind.title()})",
                statistic_id=statistic_id,
                unit=unit,
                unit_class=unit_class,
            ),
            stats,
        )

    if updated_cursors != stored:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_STAT_CURSORS: updated_cursors}
        )


def _statistic_metadata(
    *,
    name: str,
    statistic_id: str,
    unit: str,
    unit_class: str | None,
) -> StatisticMetaData:
    """Build StatisticMetaData with optional HA 2026.11 fields."""
    kwargs: dict[str, Any] = {
        "has_mean": False,
        "has_sum": True,
        "name": name,
        "source": DOMAIN,
        "statistic_id": statistic_id,
        "unit_of_measurement": unit,
        "unit_class": unit_class,
    }
    if StatisticMeanType is not None:
        kwargs["mean_type"] = StatisticMeanType.NONE
    return StatisticMetaData(**kwargs)


class MeridianBaseSensor(CoordinatorEntity[MeridianCoordinator], SensorEntity):
    """Shared device info for Meridian sensors."""

    _attr_has_entity_name = True
    # No state_class: these are lookback-window totals for display, not meters.
    # Energy dashboard history comes from external statistics only.

    def __init__(self, coordinator: MeridianCoordinator, account_number: str) -> None:
        """Attach this sensor to the account device."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_number)},
            name=f"{SENSOR_NAME} {account_number}",
            manufacturer="Meridian Energy",
            model="MyMeridian",
        )

    @property
    def _summary(self) -> UsageSummary | None:
        """Latest usage summary from the coordinator."""
        return self.coordinator.data


class MeridianImportSensor(MeridianBaseSensor):
    """Total grid import over the lookback window."""

    _attr_name = "Import"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_icon = "mdi:transmission-tower-import"

    def __init__(self, coordinator: MeridianCoordinator, account_number: str) -> None:
        """Initialise the import total sensor."""
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{DOMAIN}_{account_number}_import"

    @property
    def native_value(self) -> float | None:
        """Return import kWh over the lookback window."""
        summary = self._summary
        return None if summary is None else round(summary.import_kwh, 3)


class MeridianExportSensor(MeridianBaseSensor):
    """Total generation/export over the lookback window."""

    _attr_name = "Export"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_icon = "mdi:transmission-tower-export"

    def __init__(self, coordinator: MeridianCoordinator, account_number: str) -> None:
        """Initialise the export total sensor."""
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{DOMAIN}_{account_number}_export"

    @property
    def native_value(self) -> float | None:
        """Return export kWh over the lookback window."""
        summary = self._summary
        return None if summary is None else round(summary.export_kwh, 3)


class MeridianCostSensor(MeridianBaseSensor):
    """Consumption cost (ex standing charge) over the lookback window."""

    _attr_name = "Cost"
    _attr_native_unit_of_measurement = "NZD"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:currency-usd"

    def __init__(self, coordinator: MeridianCoordinator, account_number: str) -> None:
        """Initialise the cost total sensor."""
        super().__init__(coordinator, account_number)
        self._attr_unique_id = f"{DOMAIN}_{account_number}_cost"

    @property
    def native_value(self) -> float | None:
        """Return consumption cost in NZD over the lookback window."""
        summary = self._summary
        return None if summary is None else round(summary.cost_nzd, 2)
