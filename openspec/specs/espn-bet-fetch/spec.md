# espn-bet-fetch Specification

## Purpose
Defines how the ESPN Bet fetch obtains the site-published values its API calls depend on, so it keeps working across site releases without code edits.

## Requirements

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

### Requirement: Geo values are consistent with Chicago
The Startup call SHALL send location values that describe one Chicago-area visitor: `x-dma: 602` and a latitude and longitude inside the Chicago DMA, at the same precision and accuracy a browser reports. The DMA and location SHALL be defined together in one place, so they cannot change independently. The geo values sent with the marketplace call SHALL match those sent with Startup.

#### Scenario: Startup call location
- **WHEN** the Startup call is sent
- **THEN** its latitude and longitude fall within the Chicago area, and its `x-dma` header is `602`

#### Scenario: Marketplace call DMA
- **WHEN** the marketplace call is sent
- **THEN** its `x-dma` header equals the one sent on Startup

### Requirement: GraphQL errors stop the fetch and are not cached
When the Startup or marketplace response carries a non-empty `errors` list, or has no `data`, the system SHALL stop the ESPN Bet fetch with an error naming the operation and the first error message. It SHALL NOT write that response to the saved-response cache.

#### Scenario: Marketplace query rejected
- **WHEN** the marketplace call returns HTTP 200 with a GraphQL `errors` list
- **THEN** the fetch stops with an error naming `CompetitionPageSectionLinesTabNode`, and the previously saved response is left unchanged

#### Scenario: Startup returns no token
- **WHEN** the Startup response has `errors` and no `data`
- **THEN** the fetch stops naming `Startup`, and no marketplace call is sent

### Requirement: The whole ESPN Bet fetch shares one session
The lines page, page script, Startup and marketplace requests SHALL be sent in the same session, in that order, so cookies set by earlier requests reach the later ones.

#### Scenario: Cookie from the lines page
- **WHEN** the lines page response sets a cookie
- **THEN** the page script, Startup and marketplace requests in that run send it
