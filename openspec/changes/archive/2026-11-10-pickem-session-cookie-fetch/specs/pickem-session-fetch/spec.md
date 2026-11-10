# Spec Delta

## Purpose

Defines how Pickem spreads are obtained during a live fetch: reuse a saved CBS login session over plain HTTP first, fall back to a browser login only when needed, and keep the saved session current. It lets most runs avoid a browser entirely.

## ADDED Requirements

### Requirement: Saved session is tried first
When Pickem is fetched live, the system SHALL first request the Pickem pool page over HTTP using the session cookies stored in the auth file, without starting a browser.

#### Scenario: Valid saved session
- **WHEN** a live Pickem fetch runs and the auth file holds a session CBS still accepts
- **THEN** the spreads are read from the page returned by the HTTP request and no browser is started

### Requirement: Browser login fallback
The system SHALL run the browser login only when the HTTP attempt does not produce a logged-in page containing spreads. This covers a missing or unreadable auth file, an expired or rejected session, a redirect to the login page, a request error, and a page with no spreads.

#### Scenario: No auth file
- **WHEN** a live Pickem fetch runs and no auth file exists
- **THEN** the browser login runs and its page is used for the spreads

#### Scenario: Expired session
- **WHEN** the HTTP request is redirected to the CBS login page
- **THEN** the system treats the session as invalid and runs the browser login

#### Scenario: Request failure
- **WHEN** the HTTP request fails with a network or HTTP error
- **THEN** the system runs the browser login instead of stopping

### Requirement: Successful browser login refreshes the auth file
After a successful browser login, the system SHALL write the session cookies needed for later HTTP requests to the auth file, replacing its previous contents.

#### Scenario: Auth file created
- **WHEN** the browser login succeeds and no auth file existed
- **THEN** an auth file is created and the next live fetch uses the HTTP attempt first

#### Scenario: Auth file replaced
- **WHEN** the browser login succeeds because the saved session had expired
- **THEN** the auth file holds the new session's cookies

#### Scenario: Browser login fails
- **WHEN** the browser login does not succeed
- **THEN** the existing auth file is left unchanged

### Requirement: Auth file contents
The auth file SHALL be a JSON document in `resources/` containing a format version, the time it was saved, the time the earliest-expiring cookie expires, and a list of cookies each with at least a name, value, domain, path and expiry when one exists. The system SHALL store only the cookies needed to authenticate the HTTP request. The auth file SHALL NOT be committed to version control.

#### Scenario: Auth file shape
- **WHEN** the browser login writes the auth file
- **THEN** the file is valid JSON with a version, a saved-at time, an expires-at time and a non-empty cookie list

#### Scenario: Auth file excluded from git
- **WHEN** the auth file exists in the working tree
- **THEN** version control ignores it

#### Scenario: Unreadable auth file
- **WHEN** the auth file exists but is not valid JSON or has an unknown version
- **THEN** it is treated as missing and the browser login runs

### Requirement: Saved page is shared by both strategies
Whichever strategy succeeds, the system SHALL save the fetched Pickem page to the same saved-page file, and a run with the Pickem fetch option set to false SHALL read spreads from that file without using the auth file.

#### Scenario: Saved page from HTTP fetch
- **WHEN** a live fetch succeeds through the HTTP attempt
- **THEN** the saved-page file is updated and a later run with the Pickem fetch option false uses it

#### Scenario: Saved page from browser fallback
- **WHEN** a live fetch succeeds through the browser login
- **THEN** the saved-page file is updated in the same way

### Requirement: Browser support is optional for HTTP-only use
The system SHALL NOT require the browser automation library to be installed in order to import or run the HTTP attempt. When the browser fallback is needed and the library is not installed, the run SHALL fail with a message saying the saved session is unusable and that the browser fallback is unavailable.

#### Scenario: HTTP-only environment with a valid session
- **WHEN** the browser automation library is not installed and the saved session is valid
- **THEN** the Pickem fetch succeeds

#### Scenario: HTTP-only environment with an expired session
- **WHEN** the browser automation library is not installed and the saved session is not accepted
- **THEN** the run fails with a message naming the expired session and the unavailable browser fallback

### Requirement: Clear failure when no strategy works
If both the HTTP attempt and the browser login fail to produce a page with spreads, the system SHALL stop the Pickem fetch with an error that says both strategies failed, rather than continuing with missing data.

#### Scenario: Both strategies fail
- **WHEN** the HTTP attempt is rejected and the browser login then fails
- **THEN** the run stops with an error stating that no Pickem page could be obtained
