# Pickem Plug

Compares your CBS Pickem spreads against sportsbook lines and writes a CSV (to `out/csv/`) and an HTML readout (`out/readout.html`).

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
pipenv run python __main__.py --override-csv out/csv/spreads_output_11_11_26_02_16_UTC.csv
```

`pipenv run python __main__.py --help` lists all options and their defaults.

### Time zones

Times shown to you (the HTML "generated" time) use the `DISPLAY_TZ` environment variable, an IANA zone name that defaults to `America/Chicago`. Set it in your shell, the `.env` file, or the Lambda environment to change it. It only affects display.

## Tests

```
pipenv run python -m unittest discover tests
```

## AWS

### Lambda

- Handler: `lambda_function.lambda_handler`
- Optional event keys, all booleans defaulting to `true`: `fetch_pickem`, `fetch_draftkings`, `fetch_espnbet`, `fetch_oddshark`. Other keys (such as those a scheduler adds) are ignored. A non-boolean value makes the invocation fail before anything is fetched.
- Returns `{"week": ..., "csv_path": ..., "html_path": ...}`, where the paths are storage keys such as `out/readout.html`.

Example event: `{"fetch_espnbet": false}`

Note: the handler is wired up, but the run is not yet Lambda-ready. See `docs/LAMBDA_DISCOVERY.md`.

### Storage

Where files go is set by environment variables. Local runs need neither.

| Variable | Meaning |
|----------|---------|
| `PICKEM_STORAGE` | `local` (default): files under `resources/` and `out/`. `s3`: objects in a bucket. |
| `PICKEM_BUCKET` | Bucket name, required when `PICKEM_STORAGE=s3`. |

Bucket layout: `cache/` holds each source's last fetched response (the S3 equivalent of local `resources/`), `out/readout.html` the latest readout, and `out/csv/` every run's CSV.

In S3 mode the saved Pickem session is read from the SSM SecureString parameter `/pickemplug/pickem-auth`, never from the bucket. The app only reads it. Upload it with the local script, which creates the parameter on the first run and overwrites it afterwards:

```bash
bash scripts/upload-pickem-auth.sh --check   # one-time: verifies the AWS CLI, credentials and SSM access; writes nothing
bash scripts/upload-pickem-auth.sh           # upload resources/pickem_auth.json
```

The script needs the AWS CLI and a bash (Git Bash on Windows), and reads `AWS_DEFAULT_REGION` / `AWS_PROFILE` from the environment or `.env`. If `resources/pickem_auth.json` is missing, or its session has expired, it prompts you to run `python __main__.py --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark` to regenerate it (for an expired session you can also upload it anyway or abort). Repeat the upload whenever the session expires.

## Layout

| File | Role |
|------|------|
| `__main__.py` | Local command-line entry point |
| `lambda_function.py` | AWS Lambda entry point |
| `pickem_plug.py` | The run logic (`run(config)`, `RunConfig`) shared by both |
