# time-handling Specification

## Purpose

Defines how the system represents, converts and displays time so results do not depend on the zone of the machine it runs on (local laptop in Central, AWS Lambda in UTC).

## Requirements

### Requirement: Zone-aware times at module boundaries
The system SHALL represent every event time, current time and week boundary as a zone-aware value. Each source SHALL convert its times to aware values when it parses them, using the zone that source actually reports: Draft Kings and ESPN Bet in UTC, Odds Shark in Eastern. The system SHALL NOT compare a naive time with an aware one or rely on the machine's local zone.

#### Scenario: Same result in any machine zone
- **WHEN** the same saved source data and the same current instant are processed on a machine set to UTC and on one set to Central
- **THEN** the same events are selected and the same NFL week is computed

#### Scenario: UTC source time
- **WHEN** a source reports `2026-11-13T01:15:00Z`
- **THEN** it is treated as 8:15 PM Eastern on Thursday, November 12

#### Scenario: Eastern source time
- **WHEN** Odds Shark reports `Nov 12` and `20:15` under a `Time (ET)` header
- **THEN** it is treated as 8:15 PM Eastern on November 12, which is the same instant as `2026-11-13T01:15:00Z`

### Requirement: NFL week logic uses Eastern time
The NFL week number, week end and the Monday-night cutover (8:30 PM) SHALL be evaluated in the `America/New_York` zone, including across daylight saving changes, regardless of the machine zone or the display zone.

#### Scenario: Monday night cutover on UTC machine
- **WHEN** the current instant is Monday 8:00 PM Eastern and the machine zone is UTC
- **THEN** the current week is still the week that Monday night game belongs to

#### Scenario: Cutover passed
- **WHEN** the current instant is Monday 8:31 PM Eastern
- **THEN** the current week is the following week

### Requirement: Display zone is configurable and defaults to Central
The system SHALL read a display zone from the `DISPLAY_TZ` environment variable as an IANA zone name and SHALL use `America/Chicago` when it is unset. The display zone SHALL affect only how times are shown to the user and SHALL NOT affect which events or week are selected. A set but unrecognised value SHALL stop the run with an error naming the variable.

#### Scenario: Default display zone
- **WHEN** `DISPLAY_TZ` is not set
- **THEN** displayed times are in Central time

#### Scenario: Overridden display zone
- **WHEN** `DISPLAY_TZ` is set to `America/Los_Angeles`
- **THEN** displayed times are in Pacific time and the selected events and week are unchanged

#### Scenario: Invalid display zone
- **WHEN** `DISPLAY_TZ` is set to a value that is not a valid zone name
- **THEN** the run fails with an error that names `DISPLAY_TZ` and the bad value

### Requirement: CSV filenames are stamped in UTC
The CSV output filename SHALL contain the run's timestamp in UTC and SHALL mark it as UTC in the name, so the file's time can be read without knowing the display zone. The CSV contents SHALL NOT depend on the display zone.

#### Scenario: UTC filename stamp
- **WHEN** a run starts at 3:01 PM Central on November 10, 2026 (21:01 UTC) and writes a CSV
- **THEN** the filename timestamp reads 11_10_26_21_01 and carries a UTC marker

#### Scenario: Display zone does not change the CSV
- **WHEN** the same run is repeated with a different `DISPLAY_TZ`
- **THEN** the CSV filename and contents are identical

### Requirement: HTML generated time is the CSV's creation time
The HTML readout's generated time SHALL be the time the CSV it is built from was created, never the time the HTML was built. It SHALL be taken from the UTC stamp in the CSV filename. A CSV filename with no UTC stamp SHALL be rejected with an error rather than given a guessed time.

#### Scenario: Fresh run
- **WHEN** a run writes a CSV and then the HTML
- **THEN** the HTML's generated time is the instant stamped in that CSV's filename

#### Scenario: Rebuild from an existing CSV
- **WHEN** the HTML is rebuilt from a CSV named with a UTC stamp of 21:01 UTC on November 10, 2026, at a later time
- **THEN** the generated time is still 21:01 UTC on November 10, 2026

#### Scenario: CSV without a UTC stamp
- **WHEN** the HTML is to be built from a CSV whose filename has no UTC stamp
- **THEN** the run fails with an error naming the file and the expected `_UTC` filename pattern, and no HTML is written

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

### Requirement: Readout week is the week of the CSV's generated time
The NFL week shown in the HTML readout's title and header, and the week returned in the run result, SHALL be the NFL week of the CSV's generated time (the UTC stamp in its filename), never of the time the run happens to be executing. For a run that writes its own CSV the two are the same instant.

#### Scenario: Fresh run
- **WHEN** a run writes a CSV and then the HTML
- **THEN** the week in the HTML title and header, and in the run result, is the NFL week of the instant stamped in that CSV's filename

#### Scenario: Override CSV from an earlier week
- **WHEN** a run is given an override CSV whose UTC stamp falls in an earlier NFL week than the current time
- **THEN** the HTML title and header and the run result show the earlier week, matching the generated time shown on the page

#### Scenario: Run result matches the page
- **WHEN** any run completes
- **THEN** the week in the run result (and so in the Lambda handler's return value) equals the week shown in the HTML
