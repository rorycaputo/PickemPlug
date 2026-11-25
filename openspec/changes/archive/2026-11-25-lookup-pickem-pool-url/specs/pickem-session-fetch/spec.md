# Spec Delta

## MODIFIED Requirements

### Requirement: Saved session is tried first
When Pickem is fetched live, the system SHALL first request the CBS Pickem lobby page over HTTP using the session cookies stored in the auth file, without starting a browser, and then request the pool page found in the lobby with the same cookies.

#### Scenario: Valid saved session
- **WHEN** a live Pickem fetch runs and the auth file holds a session CBS still accepts
- **THEN** the pool URL is taken from the lobby page, the spreads are read from the pool page returned by the HTTP request, and no browser is started

### Requirement: Browser login fallback
The system SHALL run the browser login only when the HTTP attempt does not produce a logged-in page containing spreads. This covers a missing or unreadable auth file, an expired or rejected session, a logged-out lobby page, a redirect to the login page, a request error, and a page with no spreads.

#### Scenario: No auth file
- **WHEN** a live Pickem fetch runs and no auth file exists
- **THEN** the browser login runs and its page is used for the spreads

#### Scenario: Expired session
- **WHEN** the lobby page requested with the saved session lists no pool memberships, because CBS treats the request as logged out
- **THEN** the system treats the session as invalid and runs the browser login

#### Scenario: Redirect to login
- **WHEN** the lobby or pool request is redirected to the CBS login page or a pool join page
- **THEN** the system treats the session as invalid and runs the browser login

#### Scenario: Request failure
- **WHEN** the lobby or pool HTTP request fails with a network or HTTP error
- **THEN** the system runs the browser login instead of stopping

## ADDED Requirements

### Requirement: Pool URL comes from the lobby
The system SHALL take the Pickem pool URL from the lobby's list of the account's pool memberships, choosing the membership whose game is `cbs-football-pickem-manager` and whose pool name is `NFL 5 Alive`. The system SHALL NOT contain a hardcoded pool URL or pool id.

#### Scenario: Pool id changes
- **WHEN** CBS moves the account's `NFL 5 Alive` pool to a new pool id
- **THEN** the next live fetch requests the new pool's URL without a code change

#### Scenario: Other memberships ignored
- **WHEN** the lobby lists memberships for other games or other pool names alongside `NFL 5 Alive`
- **THEN** the `NFL 5 Alive` pick'em pool's URL is used

### Requirement: Missing pool membership stops the run
When the lobby shows a logged-in account but none of its memberships matches the configured game and pool name, the system SHALL stop the Pickem fetch with an error that names the pools the lobby listed, and SHALL NOT run the browser login.

#### Scenario: Pool renamed or left
- **WHEN** the saved session is logged in and the lobby lists memberships, none of them named `NFL 5 Alive` in the pick'em game
- **THEN** the run stops with an error listing the pool names found, and no browser is started

### Requirement: Browser login reaches the pool
The browser login SHALL log in from the lobby page and, once back on the logged-in lobby, find the pool using the same game and pool-name match as the HTTP attempt, then open it by clicking the pool's link.

#### Scenario: Browser opens the pool from the lobby
- **WHEN** the browser login runs because the saved session was missing, unreadable, logged out or not accepted by the pool page
- **THEN** the browser logs in, returns to the lobby, finds the `NFL 5 Alive` pick'em membership, clicks its link, and uses the pool page for the spreads

#### Scenario: Pool not found in the browser
- **WHEN** the browser has logged in but the lobby lists no matching membership
- **THEN** the browser login fails, the existing auth file is left unchanged, and the run stops with the error that no Pickem page could be obtained
