# Spec Delta

## Purpose

Defines how a Pickem Plug run is started and configured, from the local command line and from an AWS Lambda event, so both entry points behave the same and neither duplicates the run logic.

## ADDED Requirements

### Requirement: Single run behavior shared by all entry points
The system SHALL perform the same run (fetch sources, build the comparison table, write the CSV and HTML outputs) regardless of whether it is started from the command line or from a Lambda invocation. The only difference between entry points SHALL be how configuration is supplied.

#### Scenario: Same config gives same output
- **WHEN** the command line and the Lambda handler are given equivalent configuration
- **THEN** both produce the same table, CSV content and HTML content

### Requirement: Per-source fetch options default to live fetch
The system SHALL provide a fetch option for each of Pickem, DraftKings, ESPN Bet and Odds Shark. Each option SHALL default to true, meaning the source is fetched live. When an option is false, the system SHALL use that source's previously saved data instead of fetching.

#### Scenario: No options supplied
- **WHEN** a run is started with no fetch options
- **THEN** all four sources are fetched live

#### Scenario: One source set to use saved data
- **WHEN** a run is started with the Pickem fetch option set to false and the others unset
- **THEN** Pickem data is read from saved data and DraftKings, ESPN Bet and Odds Shark are fetched live

### Requirement: Local command-line configuration
The command-line entry point SHALL accept an on/off flag pair for each fetch option (for example `--fetch-pickem` and `--no-fetch-pickem`) and SHALL NOT require editing source files to change a setting. Flags not given SHALL use the defaults.

#### Scenario: Disable one source from the command line
- **WHEN** the user runs the command line with `--no-fetch-oddshark`
- **THEN** Odds Shark uses saved data and the other three sources are fetched live

#### Scenario: Help output
- **WHEN** the user runs the command line with `--help`
- **THEN** every fetch flag and its default is listed

### Requirement: Lambda event configuration
The Lambda handler SHALL read fetch options from top-level event keys named `fetch_pickem`, `fetch_draftkings`, `fetch_espnbet` and `fetch_oddshark`. Missing keys SHALL use the defaults. Other keys in the event (such as those added by a scheduler) SHALL be ignored.

#### Scenario: Scheduled event with no config
- **WHEN** the handler is invoked with a scheduler-style event containing no fetch keys
- **THEN** the run uses the defaults (all sources fetched live)

#### Scenario: Event overrides a default
- **WHEN** the handler is invoked with `{"fetch_espnbet": false}`
- **THEN** ESPN Bet uses saved data and the other sources are fetched live

#### Scenario: Invalid option value
- **WHEN** an event key holds a value that is not a boolean
- **THEN** the handler raises an error naming the key, and no sources are fetched

### Requirement: Run result is returned
A run SHALL return a summary containing at least the NFL week number and the paths of the CSV and HTML files it wrote. The Lambda handler SHALL return that summary as a JSON-serializable value.

#### Scenario: Handler return value
- **WHEN** the handler completes a run
- **THEN** it returns a dictionary with the week number, CSV path and HTML path
