# Spec Delta

## Purpose

Defines how the DraftKings fetch gets the site-published client version its markets call depends on, and how it continues when that value cannot be read.

## ADDED Requirements

### Requirement: Client version comes from the league page
On each live DraftKings fetch, the system SHALL request the DraftKings NFL league page before the markets call and read the client version the page publishes. It SHALL send that value as both `X-Client-Version` and `x-pe-cv` on the markets call. The page request SHALL use the same session as the markets call.

#### Scenario: Site publishes a new version
- **WHEN** the league page declares a client version different from the one used on the previous run
- **THEN** the markets call sends the new version in both headers, with no code change

#### Scenario: Same value in both headers
- **WHEN** the markets call is made
- **THEN** `X-Client-Version` and `x-pe-cv` carry the identical version

### Requirement: Known version is used when the page gives none
When the league page request fails, or the page has no recognizable client version, the system SHALL log that the fallback is in use and make the markets call with the fixed version `2646.5.2` (the value observed on 2026-11-14). The league page failure SHALL NOT stop the DraftKings fetch.

#### Scenario: League page request fails
- **WHEN** the league page request returns an error status or times out
- **THEN** the run logs the fallback, and the markets call is sent with version `2646.5.2`

#### Scenario: Version missing from the page
- **WHEN** the league page loads but contains no client version
- **THEN** the run logs the fallback, and the markets call is sent with version `2646.5.2`

#### Scenario: Markets call fails
- **WHEN** the markets call itself fails
- **THEN** the DraftKings fetch stops with that error; there is no fallback for the markets data

### Requirement: Saved data run makes no requests
When the DraftKings fetch option is false, the system SHALL read the saved markets response and SHALL NOT request the league page or the markets API.

#### Scenario: Fetch disabled
- **WHEN** a run has the DraftKings fetch option set to false
- **THEN** no DraftKings request is sent and the lines come from the saved response
