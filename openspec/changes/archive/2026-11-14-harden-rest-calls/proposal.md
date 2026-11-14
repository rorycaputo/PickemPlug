# Proposal

## Why

The REST calls in `src/apis.py` and its callers were assembled from browser captures at different times. They use four different Firefox versions, a frozen Datadog trace ID that every run resends, a DraftKings client version that has drifted (`2537.2.1.7` against `2646.5.2` today), ESPN geo values that disagree with each other, and a malformed `Accept-Encoding`. The helpers also return exception objects instead of raising them, have no timeout on most calls, and share one `requests.Session` created at import, which a warm Lambda container keeps between invocations. Nothing has been blocked yet. This change is preventive: it makes each run look like one consistent, current Firefox visitor, fail cleanly, and stay light on the sites.

## What Changes

- Each source gets its own HTTP session, created for the run and closed after it. No session is created at import time or shared between sources or runs.
- Every request has a timeout. HTTP and network errors are raised instead of returned, and nothing is retried automatically, a 403 included.
- One Firefox browser profile is shared by every source: a single `FIREFOX_UA` constant (Firefox 159, matching the November 2026 captures), `Accept-Encoding: gzip, deflate, br`, and the same `Accept-Language` / `DNT` / `Sec-GPC` values. Navigation requests and API requests get the matching `Sec-Fetch-*` set.
- Trace headers (`traceparent`, `tracestate`, `x-datadog-*`) and `TE: trailers` are no longer sent. The `Pragma` / `Cache-Control: no-cache` headers copied from DevTools captures are removed wherever the captures show a short or private cache.
- DraftKings: the client version is read from the NFL league page (`window.sbwebversion`) before the markets call. That page fetch is marked in code as not strictly necessary. If it fails or has no version, the run uses `2646.5.2`, the value in the 2026-11-14 capture. The markets call is updated to match the capture: `templateVars`, the `x-pe-*` headers, and widget version `3.3.0`.
- ESPN Bet (theScore): `Sec-Fetch-Site` becomes `same-site`. The lines page, chunk, Startup and marketplace calls share one session. The geo sent to Startup is consistent with Chicago (DMA 602 and a Chicago-area location). A GraphQL response carrying `errors` stops the fetch and is not written to the saved-response cache.
- `pickem_login_post` is commented out, with its captured cookie blob and action hashes removed. The commented `Cookie` line in the default headers is deleted, along with `call_post_api`, which only the dead login used.

## Capabilities

### New Capabilities
- `source-http-requests`: how the app makes HTTP requests to every source: per-source sessions scoped to the run, timeouts, raised errors with no automatic retry, the shared Firefox browser profile, and the headers that must never be sent.
- `draftkings-fetch`: how the DraftKings fetch gets the client version its markets call depends on, and the fallback when it can't.

### Modified Capabilities
- `espn-bet-fetch`: adds geo values consistent with Chicago on the Startup call, and stops a GraphQL error response from being cached or parsed as lines.

## Impact

- Code: `src/apis.py` (rewritten helpers, header constants, login post commented out), `src/draft_kings.py`, `src/espn_bet.py`, `src/odds_shark.py`, `src/pickem.py` (catches the raised error so the existing browser fallback still runs).
- Behaviour: a source request failure now stops the run with the HTTP or network error, where today it fails later with an `AttributeError` or unpack error. The Pickem fallback behaviour in `pickem-session-fetch` is unchanged.
- Network: one extra GET per run to `sportsbook.draftkings.com/leagues/football/nfl` (about 2.2 MB of HTML). No other new requests.
- Dependencies: none added. `curl_cffi` was considered and declined; the transport stays `requests`.
- Out of scope: TLS/HTTP2 fingerprinting, the AWS egress IP and region (us-east-2), storing cookies across runs, and partial results when one source fails.
