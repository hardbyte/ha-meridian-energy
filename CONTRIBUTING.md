# Contributing

## Development

```bash
scripts/setup      # install requirements
scripts/develop    # run a local Home Assistant against ./config
scripts/lint       # ruff
```

The heavy lifting (auth, GraphQL, models) lives in
[`python-meridian-energy`](https://github.com/hardbyte/python-meridian-energy).
Prefer fixing API behaviour there and bumping the dependency here.

## Pull requests

1. Branch from `main`
2. Keep changes focused; update the README when behaviour changes
3. `scripts/lint` must pass
4. Open a PR against `main`

## Bug reports

Use the issue templates. Include HA version, integration version, and debug
logs for `custom_components.meridian_energy` (never paste OTP codes or tokens).

## Licence

Contributions are under the MIT License (see [LICENSE](LICENSE)).
