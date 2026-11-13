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

### Pickem login credentials

When the saved Pickem session has expired, the Selenium login needs your CBS credentials from the `PICKEM_EMAIL` and `PICKEM_PASSWORD` environment variables (plain-text password). Set them in your shell, or in a git-ignored `.env` file in the project root (VS Code's launch config loads it); copy `.env.example` to `.env` to get started. They are not needed while the saved session is still valid.

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

### Deploy

```bash
bash scripts/deploy-lambda.sh    # preflight, tests, build, session upload, deploy, smoke invoke, live alias
bash scripts/build-lambda.sh     # build only: writes build/<timestamp>-<sha>/package.zip, no AWS calls
```

`deploy/lambda.json` is the source of truth for the function's handler.

| Flag | Effect |
|------|--------|
| `--allow-dirty` | Deploy with uncommitted changes (recorded as `<sha>-dirty`) |
| `--skip-auth-upload` | Don't run `upload-pickem-auth.sh` |
| `--no-invoke` | Skip the smoke invoke; `live` is then not moved |

Each deploy publishes a numbered version described by its git sha, smoke-invokes it with every `fetch_*` off, and only then points the `live` alias at it. Schedulers should target `pickem:live` (see Schedule below).

Roll back by pointing `live` at an earlier version:

```bash
aws lambda update-alias --function-name pickem --name live --function-version <N> --region us-east-2
```

Set up:

The deploying IAM user needs `lambda:GetFunction`, `UpdateFunctionCode`, `UpdateFunctionConfiguration`, `PublishVersion`, `InvokeFunction`, `GetAlias`, `CreateAlias` and `UpdateAlias`, plus the SSM access the upload script needs.

The smoke invoke reads the bucket's `cache/` objects, so before the first deploy, seed them once from a fresh local run (never copy `pickem_auth.json`):

```bash
for f in pickem.html DK_markets_resp.json espn_markets_resp.json odds_shark.html; do
  aws s3 cp "resources/$f" "s3://<bucket>/cache/$f"
done
```


### Schedule

```bash
bash scripts/deploy-schedule.sh --check     # validate deploy/schedule.json, show the current rules; changes nothing
bash scripts/deploy-schedule.sh             # create or update the rules from the file
bash scripts/deploy-schedule.sh --disable   # apply, but leave every rule disabled
```

`deploy/schedule.json` holds a list of schedules. Each becomes its own EventBridge rule that invokes `pickem:live`. The script needs the `live` alias to exist (deploy first) and is safe to re-run. Rules it manages (names starting `pickem-`) that are no longer in the file are deleted.

| Field | Meaning |
|-------|---------|
| `name` | Rule name; must start with `pickem-` and be unique |
| `note` | Optional free text, for humans |
| `schedule` | `cron(...)` or `rate(...)`, in UTC |
| `enabled` | `false` creates the rule disabled |
| `event` | Payload sent on each run: only the `fetch_*` booleans (see Lambda above) |

The function name and region come from `deploy/lambda.json`. The environment variables set there are unaffected.

The shipped file runs a live fetch of all four sources three times a week for the rest of the 2026 regular season: Thursday 8 am and 6 pm Central, and Sunday 8 am Central, ending after Week 18 (Thursday Jan 7 and Sunday Jan 10, 2027). EventBridge rules use UTC and have no end date, so each run is split in two: a day-of-week cron for November and December, and exact dates for January. Central stays on standard time (UTC-6) throughout, so Thursday 6 pm is Friday 00:00 UTC (and Thursday Dec 31 6 pm is Jan 1 00:00 UTC). Scheduling next season means editing the dates in the file.

In addition to the deploy permissions above, the user needs `events:PutRule`, `PutTargets`, `RemoveTargets`, `DescribeRule`, `ListRules`, `ListTargetsByRule` and `DeleteRule`, plus `lambda:AddPermission`, `RemovePermission` and `GetPolicy`.

## Layout

| File | Role |
|------|------|
| `__main__.py` | Local command-line entry point |
| `lambda_function.py` | AWS Lambda entry point |
| `pickem_plug.py` | The run logic (`run(config)`, `RunConfig`) shared by both |
