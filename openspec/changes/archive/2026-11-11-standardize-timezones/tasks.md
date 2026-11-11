# Tasks

## 1. Time module and dependency

- [x] 1.1 Add `tzdata` to `[packages]` in the Pipfile, refresh `Pipfile.lock`, and verify `python -c "from zoneinfo import ZoneInfo; ZoneInfo('America/Chicago')"` succeeds in the pipenv environment
- [x] 1.2 Create `time_util.py` with `LEAGUE_TZ`, `get_display_tz()` (reads `DISPLAY_TZ`, default `America/Chicago`, clear error naming the variable on a bad value), `now()` returning aware UTC, `parse_utc_iso()` (first 19 characters, UTC) and `to_display()`; verify with `python -c` that `parse_utc_iso('2026-11-13T01:15:00.0000000Z')` and the 6-digit variant both give 8:15 PM Eastern, that unset `DISPLAY_TZ` gives Central, and that `DISPLAY_TZ=Nope/Zone` raises an error mentioning `DISPLAY_TZ`

## 2. NFL week logic in Eastern

- [x] 2.1 Convert `date_util` to aware Eastern: `get_nfl_week` and `get_nfl_week_end` take aware datetimes (naive raises `ValueError`), boundaries are built with `LEAGUE_TZ`, and `get_nfl_week_end` defaults its reference to `time_util.now()`; verify with `python -c` that 2026-11-10 at 00:59 UTC (Monday 7:59 PM ET) and 01:31 UTC (Monday 8:31 PM ET) give consecutive weeks, and that the same instant expressed in UTC and in Chicago gives the same week
- [x] 2.2 Add `is_in_current_week(start, now)` to `date_util`; verify with `python -c` that a start of 2026-11-15 18:00 UTC is in the window at now = 2026-11-10 21:01 UTC, and that a start the following Sunday and a start one minute before `now` are not

## 3. Sources parse at the edge

- [x] 3.1 Update `odds_shark.py` to resolve "Today", the year and the Dec to Jan rollover in Eastern, attach `LEAGUE_TZ` to parsed times, accept an optional `now`, and use `is_in_current_week`; verify by running `get_odds_shark_spreads(fetch=False, now=...)` against the saved `resources/odds_shark.html` with now pinned to 2026-11-10 21:01 UTC and getting only games up to the end of that NFL week, and that a "Today" row with now at 01:00 UTC on Nov 13 resolves to Nov 12
- [x] 3.2 Update `draft_kings.py` to parse `startEventDate` with `parse_utc_iso`, accept an optional `now`, and filter with `is_in_current_week`; verify against the saved `resources/DK_markets_resp.json` with the same pinned `now` that the included events match Odds Shark's set of games and no events after that week's end appear
- [x] 3.3 Update `espn_bet.py` to read `fallbackEvent.startTime` from each `GridMarketCard`, skip cards with no start time or outside the window before reading their markets, keep the closed-market exclusion, and accept an optional `now`; verify against the saved `resources/espn_markets_resp.json` with the same pinned `now` that the included games match the Draft Kings set and that a card with its start time removed is excluded

## 4. Run and output stamping

- [x] 4.1 In `pickem_plug.run()`, capture one instant with `time_util.now()`, call `get_display_tz()` before any fetching, pass the instant to `get_nfl_week` and each source, and build the CSV filename as `..._%m_%d_%y_%H_%M_UTC.csv` from that instant in UTC; verify an offline run (`--no-fetch-pickem --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark`) writes a CSV whose name ends in `_UTC.csv` and that an invalid `DISPLAY_TZ` fails before any source is read
- [x] 4.2 Add `csv_util.get_generated_at(path)` (UTC stamp from the filename; a name without one raises a `ValueError` naming the file and expected pattern), give `html_util.create_html` a required aware `generated_at` argument instead of its own `datetime.now()`, render it converted to the display zone with the `%Z` abbreviation, and have `run()` pass `get_generated_at` of the CSV path for both a fresh write and `--override-csv`; verify with CSVs named `..._11_10_26_21_01_UTC.csv` and `..._07_10_26_21_01_UTC.csv` that the HTML shows 15:01 CST and 16:01 CDT, that rebuilding the first one later still shows 15:01, that an unstamped `spreads_output_10_06_26_17_06.csv` is rejected with the error and no HTML is written, and that `DISPLAY_TZ=America/Los_Angeles` changes only the HTML text and not the CSV name or contents
- [x] 4.3 Run `python -m unittest discover tests` and an offline end-to-end run, and verify the existing tests still pass and the outputs are produced

## 5. Documentation

- [x] 5.1 Update `README.md` to document `DISPLAY_TZ` (default Central, display only) and the UTC-stamped CSV filename, fix the `--override-csv` example filename, and verify the documented env var and filename pattern match what a run produces
- [x] 5.2 Mark item 7 (timezones) in `docs/LAMBDA_DISCOVERY.md` as resolved by this change and verify its table row and step list no longer describe it as outstanding
