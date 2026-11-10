# Pickem Plug

Compares your CBS Pickem spreads against sportsbook lines and writes a CSV and an HTML readout to `out/`.

## Setup

```
pipenv install --dev
```

## Run locally

```
pipenv run python __main__.py
```

### Pickem login credentials

When the saved Pickem session has expired, the Selenium login needs your CBS credentials from the `PICKEM_EMAIL` and `PICKEM_PASSWORD` environment variables (plain-text password). Set them in your shell, or in a git-ignored `.env` file in the project root (VS Code's launch config loads it); copy `.env.example` to `.env` to get started. They are not needed while the saved session is still valid.

### Options

By default every source is fetched live. Each source has an on/off flag; turning one off makes it use the data saved from its last live fetch (in `resources/`) instead, which is handy for fast iteration or when a source is down.

| Flag | Source |
|------|--------|
| `--no-fetch-pickem` | Pickem (CBS; tries the saved login session first, Selenium login only if it has expired) |
| `--no-fetch-draftkings` | Draft Kings |
| `--no-fetch-espnbet` | ESPN Bet |
| `--no-fetch-oddshark` | Odds Shark |

Examples:

```
# Everything live
pipenv run python __main__.py

# Skip the CBS Pickem Selenium login, reuse the saved Pickem page
pipenv run python __main__.py --no-fetch-pickem

# Fully offline, from saved data only
pipenv run python __main__.py --no-fetch-pickem --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark

# Rebuild the HTML from an existing CSV without writing a new one
pipenv run python __main__.py --override-csv out/spreads_output_10_06_26_17_06.csv
```

`pipenv run python __main__.py --help` lists all options and their defaults.

## Tests

```
pipenv run python -m unittest discover tests
```

## AWS Lambda

- Handler: `lambda_function.lambda_handler`
- Optional event keys, all booleans defaulting to `true`: `fetch_pickem`, `fetch_draftkings`, `fetch_espnbet`, `fetch_oddshark`. Other keys (such as those a scheduler adds) are ignored. A non-boolean value makes the invocation fail before anything is fetched.
- Returns `{"week": ..., "csv_path": ..., "html_path": ...}`.

Example event: `{"fetch_espnbet": false}`

Note: the handler is wired up, but the run is not yet Lambda-ready. See `docs/LAMBDA_DISCOVERY.md`.

## Layout

| File | Role |
|------|------|
| `__main__.py` | Local command-line entry point |
| `lambda_function.py` | AWS Lambda entry point |
| `pickem_plug.py` | The run logic (`run(config)`, `RunConfig`) shared by both |
