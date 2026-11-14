## MODIFIED Requirements

### Requirement: HTML generated time shows in the display zone
The HTML readout SHALL show its generated time converted to the display zone, formatted as a 24-hour `HH:MM` clock time, the zone abbreviation, the abbreviated English month, the day of month with an English ordinal suffix, and the four-digit year (for example `21:23 CST Nov 12th 2026`).

#### Scenario: Generated time in Central
- **WHEN** the generated time is 03:23 UTC on November 13, 2026 and the display zone is the default
- **THEN** the HTML shows `21:23 CST Nov 12th 2026`

#### Scenario: Daylight saving
- **WHEN** the generated time is 21:01 UTC on July 10, 2026 and the display zone is the default
- **THEN** the HTML shows `16:01 CDT Jul 10th 2026`

#### Scenario: Ordinal suffixes
- **WHEN** the generated day of month (in the display zone) is 1, 2, 3, 4, 11, 12, 13, 21, 22 or 23
- **THEN** the suffix is `st`, `nd`, `rd`, `th`, `th`, `th`, `th`, `st`, `nd`, `rd` respectively

#### Scenario: CSV filename unaffected
- **WHEN** a run writes a CSV
- **THEN** its filename keeps the month-first `%m_%d_%y_%H_%M_UTC` stamp
