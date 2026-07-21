# Meridian Energy for Home Assistant

Unofficial integration that pulls your [Meridian Energy](https://www.meridianenergy.co.nz/)
usage into Home Assistant's Energy dashboard.

Not affiliated with or endorsed by Meridian Energy.

## What it does

- Email one-time-code login (current MyMeridian auth — no password)
- Half-hourly import + solar/export generation
- Per-interval consumption cost (NZD, excl. standing charge)
- Publishes **external statistics** for the Energy dashboard
- State sensors for lookback-window totals (import / export / cost)

Built on [`meridian-energy`](https://github.com/hardbyte/python-meridian-energy).

## Install

### HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories
2. URL: `https://github.com/hardbyte/ha-meridian-energy`, category: Integration
3. Download **Meridian Energy**, restart Home Assistant
4. Settings → Devices & services → Add Integration → Meridian Energy

### Manual

Copy `custom_components/meridian_energy` into your HA `config/custom_components/`
directory and restart.

## Setup

1. Enter the email on your Meridian account
2. Enter the 6-digit code Meridian emails you
3. On the Energy dashboard, add:
   - **Grid consumption** → `meridian_energy:<account>_import`
   - **Return to grid** → `meridian_energy:<account>_export` (if you have solar)
   - **Grid cost** → `meridian_energy:<account>_cost` (optional; already incl. GST)

Statistics appear under **Developer tools → Statistics** sourced from
`meridian_energy`.

## Notes

- Polls every 3 hours; each poll re-publishes the last 10 days (recorder de-dupes)
- Estimated half-hours are included (tagged in the API as `ESTIMATE`)
- Standing daily charge is **not** folded into the cost statistic
- Multi-account pickers are not implemented yet (first account is used)
- API shapes were reverse-engineered from Meridian's public web app; they can change

## Development

```bash
# library
cd ../python-meridian-energy && uv sync --group dev && uv run pytest

# this repo
ruff check custom_components
```

For local HA against an editable library, install `meridian-energy` into the
HA container/venv pointing at your checkout before starting the integration.

## Licence

MIT (inherited from the original codyc1515/ha-meridian-energy fork). The
companion Python library is Apache-2.0.
