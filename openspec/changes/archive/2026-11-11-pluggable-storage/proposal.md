# Proposal

## Why

Every run reads and writes local files under `resources/` and `out/`, but Lambda's filesystem is read-only (blocker #2 in `docs/LAMBDA_DISCOVERY.md`), and the readout needs to end up somewhere a browser can reach. The saved CBS session also needs a home in AWS that suits a credential. The code needs a single switch that sends its files to S3, and the session to SSM, when it runs in AWS, while local runs stay exactly as they are.

## What Changes

- Add a storage switch read from the environment: `PICKEM_STORAGE=local|s3` (default `local`), plus `PICKEM_BUCKET` when `s3`. An invalid value or a missing bucket stops the run before anything is fetched.
- Route every read and write of saved source data, the CSV and the HTML readout through one storage layer that addresses files by logical key (`cache/...`, `out/...`). Locally these keys map to today's files. In S3 mode they are objects in the bucket.
- S3 layout: `cache/` holds the latest raw source responses, `out/readout.html` the latest readout, and `out/csv/` the archive of stamped CSVs.
- S3 writes set a Content-Type from the file extension (`text/html; charset=utf-8` for the readout, so browsers render it) and `Cache-Control: no-cache`.
- In S3 mode the saved Pickem session is read from the SSM SecureString parameter `/pickemplug/pickem-auth` instead of `resources/pickem_auth.json`. The system never writes that parameter: populating it stays a manual step outside this change.
- The HTML readout is built from the table rows in memory instead of reading back the CSV it just wrote. `--override-csv` still reads a CSV, now through the storage layer.
- New local CSVs are written to `out/csv/` instead of directly under `out/`. Existing CSVs in `out/` can still be passed to `--override-csv`.
- The run result's `csv_path` and `html_path` hold storage keys (for example `out/readout.html`) in both modes.
- `boto3` is imported only when S3 mode is active, so local runs don't need it.

Out of scope: creating the bucket, the SSM parameter, the CloudFront distribution, IAM, Lambda packaging and the deploy pipeline; a command for pushing the local session to SSM; storing the CBS email and password anywhere in AWS (only the local browser login uses them).

## Capabilities

### New Capabilities
- `run-storage`: where a run's saved source data, CSV and HTML readout live, how the local/S3 switch is configured and validated, the logical key layout and its local mapping, and the content metadata on S3 writes.

### Modified Capabilities
- `pickem-session-fetch`: the saved session is read from SSM in S3 mode and is never written there; the auth file location requirement becomes local-mode only.
- `app-invocation`: the run result returns storage keys rather than local file paths.

## Impact

- Code: new `storage.py`; `pickem.py`, `draft_kings.py`, `espn_bet.py`, `odds_shark.py` (saved-data reads/writes and the session load/save), `csv_util.py` (builds CSV text), `html_util.py` (builds HTML from rows, returns text), `pickem_plug.py` (keys, validation at start, result), `util.write_string_to_file` (no longer used by the run).
- Dependencies: `boto3` added to `[dev-packages]` for local verification of S3 mode. The Lambda Python runtime already provides it.
- Config/docs: `README.md` (existing CSV location, `--override-csv` example and Lambda return value, plus a brief new AWS section on the storage variables, bucket layout and SSM session), `AGENTS.md` (one bullet: the session is read from SSM and never written), `docs/LAMBDA_DISCOVERY.md` (blocker #2 status).
- Local behavior is unchanged apart from the `out/csv/` location for new CSVs, and saved pages now always being read as UTF-8.
