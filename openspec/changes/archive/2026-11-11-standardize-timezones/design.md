# Design

## Context

See proposal.md for motivation. Current state that shapes the approach:

- `date_util` builds week boundaries from naive `datetime` values and compares them with a naive `datetime.now()`. `get_nfl_week_end` also defaults to a naive `now()`.
- `draft_kings.py` slices the last 9 characters off `startEventDate` (`2026-11-13T01:15:00.0000000Z`, 7 fractional digits) and parses the remainder as naive.
- ESPN's payload uses 6 fractional digits (`...00.000000Z`). The first `startTime` in the file is on a featured parlay card, not a game. The per-game time is `fallbackEvent.startTime` on each `GridMarketCard` in the `MarketplaceShelf` (14 of 14 cards in the saved sample); the card's markets have `startTime: null`. `richEvent.gameInfo.startsAt` carries the same instant without fractional digits.
- `odds_shark.py` parses `Nov 12,` + `20:15` (header says `Time (ET)`), and fills "Today" and the year from the naive `now()`.
- The repo targets Python 3.10 (Pipfile), where `datetime.fromisoformat` does not accept a trailing `Z` or 7 fractional digits.
- Entry points: local CLI and Lambda both call `pickem_plug.run()`, which is the natural place to capture one run instant.

## Goals / Non-Goals

**Goals:**
- One place that defines the league zone, display zone and "now".
- Aware datetimes from the moment a source's time is parsed.
- Behavior independent of the machine zone, verifiable offline with saved data and a pinned instant.

**Non-Goals:**
- Parsing or comparing Pickem's rendered times.
- Showing game times or per-book pull times in the output.
- Embedding a timestamp inside the CSV contents (the filename stamp is the record).

## Decisions

**1. New `time_util.py`, matching the existing `*_util` modules.**
It holds `LEAGUE_TZ = ZoneInfo('America/New_York')`, `get_display_tz()`, `now()` (aware UTC), `parse_utc_iso(str)` and `to_display(dt)`. Alternative: put these in `date_util`. Rejected because `date_util` is NFL-calendar logic and the new helpers are used by sources and output code that should not need the calendar.

**2. Capture one run instant and pass it down.**
`run()` calls `time_util.now()` once and passes it to `get_nfl_week`, each source's line function, the CSV filename and the HTML. Source functions take an optional `now` that defaults to `time_util.now()`. This gives one consistent instant per run (the CSV filename stamp comes from it, and the HTML reads that stamp back) and lets verification pin the instant without patching. Alternative: patch `datetime` in tests. Rejected as brittle; `date_util` already takes `reference_dt` and this extends that pattern.

**3. `date_util` builds aware Eastern boundaries.**
`get_nfl_week(dt)` requires an aware `dt`, converts it to `LEAGUE_TZ` for the calendar math (season year, Labor Day and Super Bowl cutover use the Eastern calendar date) and builds boundaries as `datetime.combine(d, t, tzinfo=LEAGUE_TZ)`. Aware comparison is by instant, so daylight saving needs no special handling. A naive input raises `ValueError` rather than being guessed at. Alternative: keep everything naive in Eastern and convert only the input. Rejected: it leaves naive values flowing through, which is the problem being fixed.

**4. Shared window helper in `date_util`.**
`is_in_current_week(start, now)` returns `now <= start <= get_nfl_week_end(get_nfl_week(now), now)`. All three books call it, replacing Odds Shark's inline check and Draft Kings' `now + 7 days` rule. This is an intentional behavior change for Draft Kings (see proposal) so every book is compared over the same set of games.

**5. Parse UTC strings by truncation, not `fromisoformat`.**
`parse_utc_iso` takes the first 19 characters (`YYYY-MM-DDTHH:MM:SS`), parses them and attaches UTC. This copes with Draft Kings' 7 and ESPN's 6 fractional digits and the trailing `Z` on 3.10, and replaces the fixed `[:-9]` slice. Alternative: `dateutil`. Rejected to avoid a new dependency for one format.

**6. ESPN: read `fallbackEvent.startTime` on each card and skip the card if it is outside the window.**
The check happens before iterating the card's markets, so closed-market handling is unchanged. A card with no `fallbackEvent.startTime` is skipped. Using `richEvent.gameInfo.startsAt` as a fallback was considered; both are present in all sampled events, so one source keeps it simple.

**7. Odds Shark: attach Eastern to the parsed value, resolve "Today" and the year in Eastern.**
Get `now_et = now.astimezone(LEAGUE_TZ)`, use its date for "Today", its year for the missing year and its month for the Dec to Jan rollover, then `replace(tzinfo=LEAGUE_TZ)` on the parsed time. The "no date cell" sentinel (`now - 1 day`) stays aware.

**8. Display zone read per use, validated at the start of a run.**
`get_display_tz()` reads `DISPLAY_TZ`, defaults to `America/Chicago` and wraps `ZoneInfoNotFoundError` in an error that names the variable and value. `run()` calls it once before any fetching so a typo fails fast instead of after four network calls.

**9. Output stamping.**
CSV filename: `{base}_{now:%m_%d_%y_%H_%M}_UTC.csv`, with `now` in UTC. The CSV is the record of when it was generated, and the HTML never calls `now()`. `csv_util.get_generated_at(path)` returns an aware UTC datetime: it matches the filename against `_%m_%d_%y_%H_%M_UTC.csv` and raises a `ValueError` naming the file and the expected pattern if there is no match. Pre-change files such as `spreads_output_10_06_26_17_06.csv` have an unknown zone and are deliberately unsupported; a modification-time fallback was considered and dropped as unneeded. `run()` calls it on the CSV path in both cases (fresh write or `--override-csv`) and passes the result to `html_util.create_html(generated_at=...)`, which renders `to_display(generated_at)` with `%Z`. One path for both cases means a fresh run and a rebuild cannot disagree. Alternative: pass the run instant straight to the HTML on a fresh run. Rejected: it needs a second path for rebuilds and lets the two stamps drift. The existing field order of the HTML stamp (`%d_%m_%y_%H_%M`) is kept to avoid a gratuitous format change; the CSV filename keeps its `%m_%d_%y` order, so the two still differ in date order as they do today.

**10. Dependency.**
Add `tzdata` to `[packages]` in the Pipfile and refresh the lock, because Windows has no system zone database and the Lambda zip is built on Windows. `zoneinfo` itself is standard library on 3.9+.

## Risks / Trade-offs

- [Draft Kings now drops games already in progress, and no longer reaches into next week from early in the week] → Intended and consistent with Odds Shark; noted in the proposal so it can be vetoed.
- [Existing CSVs and anything matching the old filename pattern] → The new names add a `_UTC` suffix; the README's `--override-csv` example is updated. Nothing in the repo parses filenames.
- [Saved-data runs (`--no-fetch-*`) use the real current instant against old saved events, so the window can exclude everything] → Pre-existing for Odds Shark; unchanged. Verification pins `now` instead.
- [Filename stamps have minute resolution, and the HTML now depends on the filename pattern] → Minutes are all the HTML shows. A pre-change CSV fails loudly; renaming it with a UTC stamp makes it usable.
- [Naive Eastern strings from Odds Shark are ambiguous for one hour at the fall daylight-saving change] → Accepted; `fold=0` is used and NFL games are not scheduled in that hour.
- [ESPN payload shape changes (fields move)] → A card with no readable start time is excluded rather than included wrongly; this shows up as missing ESPN rows, the same failure style as today's other ESPN parsing.

## Migration Plan

No data migration. Deploying is a normal code deploy; `DISPLAY_TZ` is optional (Lambda can set it as an environment variable). Rollback is reverting the commit; old and new CSV filenames can coexist in `out/`.
