# Proposal

## Why

Time handling is inconsistent across the repo. Draft Kings and ESPN Bet return UTC, Odds Shark returns Eastern with no zone marker, and `date_util` assumes Eastern. All of it is compared against a naive `datetime.now()` in whatever zone the machine happens to use. The results are right only by accident: Draft Kings' window is correct on Lambda (UTC) but 6 hours off on a CST laptop, and the NFL week flips hours early on Lambda. ESPN Bet has no event-time filtering at all, so it is the one book not limited to the current week. Output timestamps (CSV filename, HTML "generated") also depend on the machine zone, not on what is intuitive for the user (Central).

## What Changes

- Add one small time module that owns the zone rules: the league zone (`America/New_York`), a display zone read from a `DISPLAY_TZ` environment variable (default `America/Chicago`), and a single `now()` that returns an aware UTC datetime and can be pinned in tests.
- Parse every source's times at the edge into aware datetimes: Draft Kings and ESPN Bet as UTC, Odds Shark as Eastern. No naive datetime crosses a module boundary.
- Make `date_util` (NFL week number, week end, MNF cutover) operate on aware datetimes in the league zone, so the week boundary is the same wherever the code runs.
- Add per-event start-time filtering to ESPN Bet using each event's UTC `startTime`, and use one shared "current NFL week" window for Draft Kings, ESPN Bet and Odds Shark. **BREAKING (behavior)**: Draft Kings currently uses "start within 7 days of now"; it moves to the same week-end window as Odds Shark.
- Name the CSV file with a UTC timestamp and a visible `_UTC` marker, so the file is self-describing and does not depend on `DISPLAY_TZ`.
- Derive the HTML "generated" time from the CSV it is built from, never from the current time: use the UTC stamp in the CSV filename. A CSV whose name has no UTC stamp (files made before this change) is not supported and is rejected with a clear error. Render it converted to `DISPLAY_TZ` with the zone abbreviation. A rebuild with `--override-csv` therefore shows when that CSV was made.
- Add `tzdata` to the Pipfile (Windows has no system zone database) and document `DISPLAY_TZ` in the README.

Out of scope: showing game times in the output, per-book "time pulled" stamps (the `todo actual timestamps for each book` in `pickem_plug.py`), parsing times out of the Pickem page (it renders UTC but nothing consumes it) and changing the CSV columns.

## Capabilities

### New Capabilities
- `time-handling`: How the system represents and converts time: aware datetimes only, the league zone for NFL week logic, the `DISPLAY_TZ` display zone, and how output files and the HTML are stamped.
- `week-window-filtering`: How each sportsbook source decides which events belong to the current NFL week, using each event's start time.

### Modified Capabilities
<!-- None: existing app-invocation and pickem-session-fetch requirements do not change. -->

## Impact

- Code: new time module; `date_util.py`, `odds_shark.py`, `draft_kings.py`, `espn_bet.py`, `pickem_plug.py`, `csv_util.py` (reads a CSV's generated time), `html_util.py` (takes the generated time instead of calling `now()`).
- Behavior: output CSV filenames gain a UTC marker (`..._HH_MM_UTC.csv`) and now use UTC; the HTML "generated" time now reflects the CSV's creation time (it also fixes the existing `todo actual csv timestamp for 'Generated' text on html`); Draft Kings' event window changes; ESPN Bet now drops events outside the current week.
- Dependencies/config: `tzdata` in the Pipfile; optional `DISPLAY_TZ` env var (defaults to Central, so nothing is required).
- Docs: README (env var and filename note), and `docs/LAMBDA_DISCOVERY.md` item 7 is resolved.
