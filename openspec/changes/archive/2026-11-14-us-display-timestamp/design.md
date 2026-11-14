# Design

## Context

`build_html` in `src/html_util.py` builds the subtitle with `time_util.to_display(generated_at).strftime("%d_%m_%y_%H_%M %Z")`. `generated_at` is already an aware datetime parsed from the CSV's UTC filename stamp (`csv_util.get_generated_at`). Filenames are already `%m_%d_%y_%H_%M_UTC`. See proposal.md.

## Goals / Non-Goals

**Goals:**
- Readable subtitle timestamp in the display zone.

**Non-Goals:**
- Changing CSV filename format or the filename parser.
- Changing other displayed times (game times, etc.).

## Decisions

- Add `format_display_time(dt)` to `src/time_util.py` returning e.g. `21:23 CST Nov 12th 2026`; `html_util` calls it. Keeps formatting next to `to_display` and makes it unit-testable.
- Build the string with `strftime` for the clock, zone and month (`%H:%M %Z %b`), then append the day with an ordinal suffix and the year. Locale is not a concern: the app runs in the US/default C locale, where `%b` is English. Ordinal rule: 11–13 → `th`; else last digit 1/2/3 → `st`/`nd`/`rd`; otherwise `th`.
- Day is not zero-padded (`Nov 2nd`), hour/minute are (`09:05`).
- Alternative considered: plain `strftime('%H:%M %Z %b %d')` — rejected, no ordinal suffix.

## Risks / Trade-offs

- [Zone abbreviation for non-US `DISPLAY_TZ` may be numeric like `+03`] → acceptable; same as today's `%Z`.
