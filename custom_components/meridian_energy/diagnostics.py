"""Diagnostics support for Meridian Energy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant

from . import MeridianConfigEntry
from .const import CONF_ACCOUNT_NUMBER, CONF_TOKENS
from .sensor import CONF_STAT_CURSORS

TO_REDACT = {
    CONF_EMAIL,
    CONF_TOKENS,
    "id_token",
    "refresh_token",
    "customToken",
    "access_token",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MeridianConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (tokens/email redacted)."""
    coordinator = entry.runtime_data
    summary = coordinator.data

    summary_info: dict[str, Any] | None = None
    if summary is not None:
        summary_info = {
            "import_kwh": summary.import_kwh,
            "export_kwh": summary.export_kwh,
            "cost_nzd": summary.cost_nzd,
            "export_credit_nzd": summary.export_credit_nzd,
            "cost_currency": summary.cost_currency,
            "hourly_buckets": len(summary.hourly),
            "measurement_count": len(summary.measurements),
            "first_hour": (
                summary.hourly[0].start.isoformat() if summary.hourly else None
            ),
            "last_hour": (
                summary.hourly[-1].start.isoformat() if summary.hourly else None
            ),
        }

    cursors = entry.data.get(CONF_STAT_CURSORS) or {}

    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "domain": entry.domain,
                "version": entry.version,
                "unique_id": entry.unique_id,
                "data": {
                    CONF_ACCOUNT_NUMBER: entry.data.get(CONF_ACCOUNT_NUMBER),
                    CONF_EMAIL: entry.data.get(CONF_EMAIL),
                    CONF_STAT_CURSORS: cursors,
                    # tokens deliberately omitted except redacted placeholder
                    CONF_TOKENS: entry.data.get(CONF_TOKENS),
                },
            },
            TO_REDACT,
        ),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                repr(coordinator.last_exception) if coordinator.last_exception else None
            ),
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "account_number": coordinator.account_number,
        },
        "summary": summary_info,
    }
