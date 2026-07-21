"""Meridian Energy usage sensors and external statistics."""

from __future__ import annotations

import logging

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from meridian_energy import UsageSummary

from . import MeridianConfigEntry
from .const import DOMAIN, SENSOR_NAME
from .coordinator import MeridianCoordinator

_LOGGER = logging.getLogger(__name__)


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
        _publish_statistics(hass, coordinator)

    entry.async_on_unload(coordinator.async_add_listener(_on_update))
    _publish_statistics(hass, coordinator)


@callback
def _publish_statistics(hass: HomeAssistant, coordinator: MeridianCoordinator) -> None:
    """Push the latest usage window into recorder external statistics."""
    summary = coordinator.data
    if summary is None:
        return
    slug = _statistic_slug(coordinator.account_number)

    def _stats(kind: str) -> list[StatisticData]:
        return [
            StatisticData(start=point.start, sum=point.sum)
            for point in summary.statistics
            if point.kind == kind
        ]

    import_stats = _stats("import")
    export_stats = _stats("export")
    cost_stats = _stats("cost")

    if import_stats:
        async_add_external_statistics(
            hass,
            StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"{SENSOR_NAME} (Import)",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{slug}_import",
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            ),
            import_stats,
        )
    if export_stats:
        async_add_external_statistics(
            hass,
            StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"{SENSOR_NAME} (Export)",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{slug}_export",
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            ),
            export_stats,
        )
    if cost_stats:
        async_add_external_statistics(
            hass,
            StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"{SENSOR_NAME} (Cost)",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{slug}_cost",
                unit_of_measurement="NZD",
            ),
            cost_stats,
        )


class MeridianBaseSensor(CoordinatorEntity[MeridianCoordinator], SensorEntity):
    """Shared device info for Meridian sensors."""

    _attr_has_entity_name = True

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
    _attr_state_class = SensorStateClass.TOTAL
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
    _attr_state_class = SensorStateClass.TOTAL
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
    _attr_state_class = SensorStateClass.TOTAL
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
