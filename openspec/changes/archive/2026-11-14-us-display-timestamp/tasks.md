# Tasks

## 1. Readable generated timestamp

- [x] 1.1 Add `format_display_time(dt)` to `src/time_util.py` (converts to display zone, returns `HH:MM ZZZ Mon Dth YYYY` with ordinal suffix). Verify: `python -c` calls with 2026-11-13T03:23Z → `21:23 CST Nov 12th 2026` and 2026-07-10T21:01Z → `16:01 CDT Jul 10th 2026`, and days 1,2,3,4,11,12,13,21,22,23 give the correct suffixes.
- [x] 1.2 Use it for the subtitle in `build_html` (`src/html_util.py`) in place of the `%d_%m_%y_%H_%M %Z` format. Verify: build the HTML from an existing CSV (e.g. `python src --override-csv ... ` with fetches off) and confirm the `<h2>` reads `… — generated 21:23 CST Nov 12th 2026` style text.
- [x] 1.3 Confirm CSV filenames still end `_%m_%d_%y_%H_%M_UTC.csv` after an offline run. Verify: `ls out/csv` shows the new file in month-first order.
