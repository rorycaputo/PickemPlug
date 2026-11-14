# Proposal

## Why

The HTML readout subtitle shows its generated time as `12_11_26_21_23 CST`, which reads as day-month-year (European) and is hard to scan. Readers expect a US-style, human-readable timestamp.

## What Changes

- The HTML readout subtitle shows the generated time as a readable string, e.g. `21:23 CST Nov 12th 2026` (24-hour clock, zone abbreviation, abbreviated month, day with ordinal suffix, year), in the display zone.
- CSV filenames are **unchanged**: they are already US order (`%m_%d_%y_%H_%M_UTC`, e.g. `spreads_output_11_12_26_03_23_UTC.csv`). The `12_11_26` seen in the HTML was the HTML's own day-first format, not the filename. Filenames are also what the HTML time is parsed from, so changing them would break existing CSVs.

## Capabilities

### New Capabilities

### Modified Capabilities
- `time-handling`: the "HTML generated time shows in the display zone" requirement now specifies the readable format.

## Impact

- `src/html_util.py` (subtitle formatting in `build_html`); possibly a small formatting helper in `src/time_util.py`.
- No change to CSV naming, storage keys, Lambda handler, or time conversion logic.
