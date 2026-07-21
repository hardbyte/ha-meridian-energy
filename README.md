# Meridian Energy for Home Assistant

Unofficial Home Assistant integration for [Meridian Energy](https://www.meridianenergy.co.nz/) (NZ).

Pulls half-hourly usage (and optional solar export) into the **Energy dashboard** via Meridian's current MyMeridian API (email one-time code + GraphQL).

Not affiliated with or endorsed by Meridian Energy.

## Features

- Email OTP login (no password — matches the live MyMeridian app)
- Transparent Firebase token refresh
- Grid import + generation/export statistics
- Per-interval consumption cost in NZD (ex standing charge)
- Sensors for lookback-window totals
- Built on [`meridian-energy`](https://github.com/hardbyte/python-meridian-energy)

## Install (HACS)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Repository: `https://github.com/hardbyte/ha-meridian-energy`
3. Category: **Integration**
4. Download **Meridian Energy**, then **restart Home Assistant**
5. Settings → Devices & services → **Add Integration** → Meridian Energy

## Setup

1. Enter the email on your Meridian account  
2. Enter the 6-digit code Meridian emails you  
3. On the Energy dashboard, add external statistics:

| Energy dashboard field | Statistic ID |
|------------------------|--------------|
| Grid consumption | `meridian_energy:<account>_import` |
| Return to grid | `meridian_energy:<account>_export` |
| Grid cost | `meridian_energy:<account>_cost` |

`<account>` is the Meridian account number lowercased with non-alphanumerics
turned into underscores (e.g. `A-1B9AC44D` → `a_1b9ac44d`). Find the exact IDs
under **Developer tools → Statistics** (source `meridian_energy`).

## Behaviour

- Polls about every **3 hours**
- Each poll re-publishes the last **10 days**; the recorder de-dupes by statistic id + start
- Estimated half-hours (`ESTIMATE`) are included
- Standing daily charge is **not** included in the cost statistic
- First account on the login is used (multi-account picker not implemented yet)

## Development

```bash
# companion library
cd ../python-meridian-energy
uv sync --group dev
uv run pytest

# this integration
scripts/setup
scripts/develop   # local HA on :8123 with config/
scripts/lint
```

For a live HA instance, HACS installs from this repo; the integration's
`manifest.json` pulls `meridian-energy` from GitHub until it is on PyPI.

## History / licence

Originally forked from [codyc1515/ha-meridian-energy](https://github.com/codyc1515/ha-meridian-energy)
(CSV scrape of the retired `secure.meridianenergy.co.nz` portal). That upstream is
archived. This tree is a full rewrite against the current OTP + GraphQL stack and
is maintained independently.

MIT — see [LICENSE](LICENSE). Copyright retained for Cody C's original work;
subsequent rewrite by Brian Thorne.
