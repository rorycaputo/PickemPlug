# Spec Delta

## Purpose
Defines how the ESPN Bet fetch obtains the site-published values its API calls depend on, so it keeps working across site releases without code edits.

## ADDED Requirements

### Requirement: App version comes from the site's chunk
The system SHALL read the sportsbook's app version from the page script it fetches on each ESPN Bet run, and SHALL send that value as both `x-app-version` and `apollographql-client-version` on the Startup and marketplace API calls. The version SHALL NOT be hardcoded.

#### Scenario: Site publishes a new version
- **WHEN** the fetched script declares a version different from the one used on the previous run
- **THEN** both API calls send the new version in both headers with no code change

#### Scenario: Same value in both headers
- **WHEN** the ESPN Bet API calls are made
- **THEN** `x-app-version` and `apollographql-client-version` carry the identical version on every call

### Requirement: Missing version fails clearly
The system SHALL stop the ESPN Bet fetch with an error naming the app version when the fetched script contains no version, and SHALL NOT make the API calls with a guessed or stale value.

#### Scenario: Version not found
- **WHEN** the fetched script has no recognizable app version
- **THEN** the fetch stops with an error that names the missing app version, and no Startup or marketplace call is sent
