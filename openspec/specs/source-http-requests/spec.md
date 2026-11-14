# source-http-requests Specification

## Purpose

Defines how the app makes HTTP requests to the sources it reads (Pickem, DraftKings, ESPN Bet, covers.com), so each run presents one consistent, current browser, fails clearly, and stays light on the sites.

## Requirements

### Requirement: One session per source per run
The system SHALL use a separate HTTP session for each source in a run, and all of that source's requests in the run SHALL share it. A session SHALL NOT be created at import time and SHALL NOT be reused by another source or a later run, including later invocations in a warm Lambda container.

#### Scenario: Cookies flow within a source
- **WHEN** an earlier request for a source sets a cookie
- **THEN** that source's later requests in the same run send it

#### Scenario: No state carried between runs
- **WHEN** two runs happen in the same process
- **THEN** the second run's first request for a source sends no cookies set during the first run

#### Scenario: Sources do not share cookies
- **WHEN** a DraftKings response sets a cookie
- **THEN** no ESPN Bet, covers.com or Pickem request in that run sends it

### Requirement: Every request has a timeout
Every source request SHALL have a finite timeout. A request that exceeds it SHALL fail as a request error.

#### Scenario: Unresponsive site
- **WHEN** a source site accepts the connection but never responds
- **THEN** the request fails once its timeout passes, well within the Lambda timeout

### Requirement: Request failures stop the source with the original error
When a source request fails with an HTTP error status or a network error, the system SHALL raise that error to the source's caller rather than returning a value in its place. Except where a capability defines a fallback (Pickem's browser login, DraftKings' client version), the run SHALL stop with an error naming the failed request.

#### Scenario: HTTP error from a lines source
- **WHEN** the DraftKings markets request returns a 5xx status
- **THEN** the run stops with an error showing the status and URL, not an attribute or unpacking error

#### Scenario: Pickem request error still falls back
- **WHEN** the saved-session Pickem request fails with an HTTP or network error
- **THEN** the browser login fallback runs as before

### Requirement: No automatic retries
The system SHALL NOT retry a failed source request automatically. A 403 or 429 response SHALL be treated as a failure on the first attempt.

#### Scenario: Blocked request
- **WHEN** a source request returns 403
- **THEN** no further request is sent to that URL in the run

### Requirement: One current Firefox profile for every source
Every source request SHALL identify as the same Firefox release on Windows, with the same User-Agent, Accept-Language, DNT and Sec-GPC values. Accept-Encoding SHALL list only encodings the app can decode (gzip, deflate, br). The Firefox version SHALL be defined in one place.

#### Scenario: Same browser everywhere
- **WHEN** a run fetches every source
- **THEN** every request carries the identical User-Agent string

#### Scenario: Compressed response
- **WHEN** a source responds with brotli or gzip compression
- **THEN** the body is decoded correctly

### Requirement: Fetch-context headers match the request kind
Page loads SHALL send top-level navigation headers (`Sec-Fetch-Mode: navigate`, `Sec-Fetch-Dest: document`). API calls SHALL send `Sec-Fetch-Mode: cors` with a `Sec-Fetch-Site` that matches the real relationship between the page's site and the API host.

#### Scenario: API host on a sibling subdomain
- **WHEN** an API call goes to a subdomain of the same registrable domain as the page (for example `sportsbook.us-il.thescore.bet` from `sportsbook.thescore.bet`)
- **THEN** it sends `Sec-Fetch-Site: same-site`

### Requirement: No frozen or capture-only headers
The system SHALL NOT send trace headers (`traceparent`, `tracestate`, `x-datadog-*`), `TE: trailers`, or captured cookie values written into source. It SHALL NOT send `Pragma: no-cache` or `Cache-Control: no-cache` to a source whose responses are shown to be uncached or cached for only seconds.

#### Scenario: Marketplace call
- **WHEN** the ESPN Bet marketplace call is sent
- **THEN** it carries no trace or Datadog header

#### Scenario: DraftKings markets call
- **WHEN** the DraftKings markets call is sent
- **THEN** it carries neither `Pragma` nor `Cache-Control`
