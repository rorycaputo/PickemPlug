# Proposal

## Why

The app can only be run one way: `python __main__.py`, with its settings hard-coded as constants at the top of that file. To run it on AWS Lambda a second entry point is needed, and `lambda_function.py` was started as a full copy of `__main__.py`. The copies have already drifted (the ESPN Bet block is commented out in one and active in the other). A shared core with thin entry points and passed-in config fixes this before any deployment work builds on top of it.

## What Changes

- Move the run logic (everything currently in `__main__.py` except the entry point) into a new core module, `pickem_plug.py`, exposing `run(config)`.
- Add a `RunConfig` that replaces the module-level `FETCH_*` constants and `OVERRIDE_CSV_DATA`. Every `fetch_*` option defaults to **True**. The old constants were manual local-dev switches, so their current values carry no meaning for the new defaults.
- Reduce `__main__.py` to a small local CLI that builds a `RunConfig` from command-line flags and calls `run`.
- Reduce `lambda_function.py` to a small `lambda_handler(event, context)` that builds a `RunConfig` from the event payload and calls `run`. Handler string: `lambda_function.lambda_handler`.
- Have `run` return a summary (week number, CSV path, HTML path) instead of only printing and writing files.
- Update `README.md` with how to run the script locally (the new flags) and the Lambda handler/event usage.
- No change to fetchers, table math, HTML/CSV output format, or where files are written.

## Capabilities

### New Capabilities
- `app-invocation`: how a run is started and configured, from the local command line and from a Lambda event, including the per-source fetch options and their defaults.

### Modified Capabilities

None. There are no existing specs.

## Impact

- Code: `__main__.py` (shrinks to CLI), `lambda_function.py` (shrinks to handler), new `pickem_plug.py`, new `tests/` for config parsing, `README.md`.
- Local workflow: the dev switches that were edited in `__main__.py` become command-line flags (for example `--no-fetch-pickem` to use the cached Pickem HTML).
- Out of scope (later steps from LAMBDA_DISCOVERY.md): Selenium/browser on Lambda, read-only filesystem and `/tmp` or S3 output, credentials handling, timezones, partial-failure handling, packaging for Linux.
