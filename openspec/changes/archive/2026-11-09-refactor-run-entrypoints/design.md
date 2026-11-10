# Design

## Context

`__main__.py` holds everything: settings constants, `main()`, `build_table`, the team name map and display helpers. `lambda_function.py` is a copy of it with `main(event, context)`; the copy has already diverged (ESPN Bet commented out in `build_table`). `__main__.py` is the source of truth (ESPN active). Modules are imported flat (`import draft_kings`), the repo root has an empty `__init__.py`, and the README runs `python __main__.py`. There are no tests. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- One copy of the run logic, with two ~15-line entry points.
- Config passed in as an argument; no module-level settings read during a run.
- Local use stays one command, with flags instead of file edits.

**Non-Goals:**
- Making the run Lambda-safe (read-only filesystem, Selenium, credentials, timezones, error handling); these are later changes. The handler built here will still fail on Lambda until those land.
- Changing table math, output formats, or fetcher internals.
- Moving the team name map or display helpers into separate modules.

## Decisions

**Core module `pickem_plug.py`.** The body of `__main__.py` moves here unchanged apart from `main()` becoming `run(config)`. Chosen over keeping logic in `lambda_function.py` (Lambda-specific name) or `__main__.py` (not cleanly importable, and the suspected source of the name clash). A pure move keeps the diff reviewable and behavior identical.

**`RunConfig` as a frozen dataclass.** Fields: `fetch_pickem`, `fetch_draftkings`, `fetch_espnbet`, `fetch_oddshark` (all default `True`) and `override_csv_data: str | None = None` (replaces `OVERRIDE_CSV_DATA`). Output paths (`./out/...`) stay as module constants for now. Chosen over a plain dict (typos pass silently) and env vars (awkward locally). `RunConfig.from_event(event)` builds from a Lambda event and raises `ValueError` naming the key if a value is not a `bool`; unknown keys are ignored since EventBridge adds `time`, `source`, etc.

**CLI with `argparse.BooleanOptionalAction`.** Gives `--fetch-pickem` / `--no-fetch-pickem` per source, with defaults shown in `--help`. Chosen over positional "skip" flags because each flag matches a config field name one-to-one. Stdlib only; no new dependency.

**All fetch options default to True.** Requested by the user. The old constants were manual local-dev switches, not a documented default, so this is not treated as a behavior change; the README documents only the new way to run locally (flags), not the old constant values.

**`run` returns `RunResult(week, csv_path, html_path)`.** The handler returns `dataclasses.asdict(result)`, which is JSON-serializable. Printing of the table stays inside `run`, so CloudWatch and the terminal both show it.

**Entry points import the core by flat name.** `from pickem_plug import run, RunConfig`, matching the existing flat-import style, so the same files drop into a zip at the root.

**Tests: stdlib `unittest`.** A small `tests/test_config.py` covers defaults, `from_event` (missing keys, overrides, ignored extras, bad types) and CLI parsing. No network or fetchers involved.

## Risks / Trade-offs

- [A bare local run now fetches every source live, including the Selenium Pickem login] → `--help` shows the defaults and the flags to switch any source to cached data.
- [Pure move may hide a subtle break (e.g. a constant referenced from another module)] → grep for `__main__`/constant uses before moving; verify by running with all fetches off against cached files and diffing the output CSV/HTML against a run from before the change.
- [Handler still can't work on Lambda] → expected and called out as a non-goal, so nobody mistakes this change for deploy-ready.
- [Dropping `lambda_function.py`'s copy loses its ESPN-commented variant] → intentional; `__main__.py`'s active ESPN version is the one in use.
