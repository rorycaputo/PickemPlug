# Spec Delta

## ADDED Requirements

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
