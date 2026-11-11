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
The HTML readout SHALL show its generated time converted to the display zone and SHALL include the zone abbreviation.

#### Scenario: Generated time in Central
- **WHEN** the generated time is 21:01 UTC on November 10, 2026 and the display zone is the default
- **THEN** the HTML shows a 15:01 clock time with the CST abbreviation

#### Scenario: Daylight saving
- **WHEN** the generated time is 21:01 UTC on July 10 and the display zone is the default
- **THEN** the HTML shows a 16:01 clock time with the CDT abbreviation
