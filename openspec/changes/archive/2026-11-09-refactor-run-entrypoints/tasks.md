# Tasks

## 1. Baseline

- [x] 1.1 Run the current `python __main__.py` with all four constants set to False (cached files in `resources/`) and save the resulting CSV and `out/readout.html` outside the repo as the comparison baseline; verify both files exist (note: tonight's cached `pickem.html` has no unfinished games, so the baseline reads `resources/pickem_backup.html` via a runner in the scratchpad; reuse the same method in 4.1)

## 2. Core module and config

- [x] 2.1 Create `pickem_plug.py` by moving everything from `__main__.py` except the `if __name__` block; convert `main()` to `run(config)` returning `RunResult(week, csv_path, html_path)`; verify `python -c "import pickem_plug"` succeeds
- [x] 2.2 Add `RunConfig` (four `fetch_*` fields default True, `override_csv_data` default None) and replace the `FETCH_*` / `OVERRIDE_CSV_DATA` constants; verify `grep -n "FETCH_" pickem_plug.py` finds no remaining constants
- [x] 2.3 Add `RunConfig.from_event(event)` that reads the four event keys, ignores unknown keys, and raises `ValueError` naming the key for non-bool values
- [x] 2.4 Add `tests/test_config.py` (unittest) covering defaults, overrides, ignored extra keys and bad types; verify `python -m unittest discover tests` passes

## 3. Entry points

- [x] 3.1 Rewrite `__main__.py` as a CLI using `argparse.BooleanOptionalAction` for each fetch flag, calling `run`; verify `python __main__.py --help` lists all four flags with defaults, and add CLI-parsing cases to `tests/test_config.py` that pass
- [x] 3.2 Rewrite `lambda_function.py` as `lambda_handler(event, context)` building a config via `from_event` and returning `asdict(run(config))`; add handler tests (scheduler-style event, override, bad type) with `run` mocked, and verify they pass
- [x] 3.3 Update `README.md` with how to run locally (the fetch flags and their all-True defaults, with no reference to the old constants' values) and the Lambda handler string and event keys; verify each documented command runs as written

## 4. Integration check

- [x] 4.1 Run `python __main__.py --no-fetch-pickem --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark` and diff the CSV and HTML against the 1.1 baseline; verify they are identical apart from the filename timestamp
- [x] 4.2 Run `python -c "import lambda_function; print(lambda_function.lambda_handler({'fetch_pickem': False, 'fetch_draftkings': False, 'fetch_espnbet': False, 'fetch_oddshark': False}, None))"` and verify it prints the week, CSV path and HTML path
