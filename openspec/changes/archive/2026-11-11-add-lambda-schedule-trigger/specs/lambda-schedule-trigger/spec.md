# Spec Delta

## Purpose
Defines the checked-in list of schedules and the operator-run script that makes the `pickem` function's `live` alias run on those schedules.

## ADDED Requirements

### Requirement: The schedules are configured in a checked-in file
The triggers' settings SHALL be read from a checked-in JSON config file holding a list of schedules. Each schedule SHALL have a unique name, a schedule expression, whether it is enabled, and the event payload sent on each run, and MAY have a free-text note. The payload SHALL accept only the function's `fetch_*` boolean options. The function name and region SHALL be taken from the deploy config so the two files cannot disagree.

#### Scenario: Change a schedule
- **WHEN** a schedule expression in the file is changed and the script is run
- **THEN** that trigger runs on the new schedule without any other edit

#### Scenario: Several schedules
- **WHEN** the file lists three schedules with different expressions
- **THEN** after the script each one exists as its own trigger and fires on its own expression

#### Scenario: Invalid payload
- **WHEN** a payload contains a key other than `fetch_pickem`, `fetch_draftkings`, `fetch_espnbet` or `fetch_oddshark`, or a non-boolean value
- **THEN** the script exits non-zero naming the schedule and key, and nothing in AWS is changed

#### Scenario: Invalid schedule expression
- **WHEN** a schedule expression is not a `cron(...)` or `rate(...)` expression
- **THEN** the script exits non-zero before any AWS change

#### Scenario: Duplicate names
- **WHEN** two schedules have the same name
- **THEN** the script exits non-zero before any AWS change

### Requirement: Schedules stop after the regular season
The configured schedule expressions SHALL fire only on dates up to and including the last day of the 2026 regular season (Sunday, January 10, 2027). The config SHALL express this with explicit dates in the expressions, since triggers have no end date of their own.

#### Scenario: Last runs
- **WHEN** the schedules are applied
- **THEN** the Thursday morning run's last firing is Thursday, January 7, 2027, the Thursday evening run's last firing is the evening of that same Thursday, and the Sunday morning run's last firing is Sunday, January 10, 2027

#### Scenario: After the season
- **WHEN** the date is after January 10, 2027
- **THEN** no schedule fires

### Requirement: The triggers invoke the live alias
Each trigger SHALL invoke the function through its `live` alias, so a schedule run uses only a version that passed the deploy's smoke invoke. The script SHALL fail, changing nothing, when the `live` alias does not exist.

#### Scenario: Scheduled run
- **WHEN** a schedule fires
- **THEN** `pickem:live` is invoked with that schedule's payload

#### Scenario: No live alias yet
- **WHEN** the script runs before any deploy has created `live`
- **THEN** it exits non-zero telling the operator to deploy first

### Requirement: Applying the schedules is idempotent
Running the script SHALL leave AWS matching the config file whether or not the triggers already exist: it creates missing triggers, updates different ones, removes any other target on them, and removes triggers the script manages that the file no longer lists, along with their permission to invoke the function. Running it twice in a row SHALL change nothing the second time.

#### Scenario: First run
- **WHEN** no triggers exist
- **THEN** every listed trigger is created, enabled or disabled as configured, and allowed to invoke the function

#### Scenario: Drifted trigger
- **WHEN** a live trigger has a different schedule or payload than the file
- **THEN** after the script it has the file's values

#### Scenario: Schedule removed from the file
- **WHEN** a managed trigger is no longer listed in the file
- **THEN** after the script it and its invoke permission are gone

### Requirement: The triggers can be disabled without editing the file
The script SHALL accept a flag that disables every trigger, and a check flag that validates the config and reports each trigger's current schedule, state and payload without changing anything. A disabled trigger SHALL keep its schedule and payload.

#### Scenario: Pause
- **WHEN** the script runs with the disable flag
- **THEN** the triggers stay defined but no longer fire, and the next normal run re-enables those the file marks enabled

#### Scenario: Check only
- **WHEN** the script runs with the check flag
- **THEN** it prints the config and each trigger's current state and makes no AWS changes

### Requirement: The trigger setup holds no secrets and no roles
The schedule config SHALL hold only non-secret settings. The script SHALL NOT create or modify IAM roles, and SHALL NOT change the function's code, configuration or aliases.

#### Scenario: Function untouched
- **WHEN** the script runs
- **THEN** the function's code, environment variables, versions and aliases are unchanged
