# Proposal

## Why

The ESPN Bet calls in `src/apis.py` hardcode `x-app-version` and `apollographql-client-version` as `26.21.0`. The sportsbook rejects stale values with 403s (see the comment in `espn_bet.py`), so every site release means a manual code edit. The version is already present in the page chunk the app downloads each run, so it can be read instead of hardcoded.

## What Changes

- Finding: the version is the build-time constant `NEXT_PUBLIC_PACKAGE_JSON_VERSION`, shipped in the `/_next/static/chunks/pages/index-*.js` chunk that `espn_bet.py` already fetches (to get the persisted-query SHAs). In the chunk's env module it appears as `NEXT_PUBLIC_PACKAGE_JSON_VERSION: a.env.NEXT_PUBLIC_PACKAGE_JSON_VERSION || "<version>"`, minified in the live bundle as `...NEXT_PUBLIC_PACKAGE_JSON_VERSION||"26.19.1"`. The site's own JS sends this value as `x-app-version`, and the Apollo client uses it as its client `version`. The 2026-09-27 HAR confirms: the request header was `26.19.1` and the same chunk contained `"26.19.1"`.
- Extract that version from the already-fetched chunk, alongside the SHAs.
- Pass it into the Startup and marketplace calls, replacing the hardcoded `26.21.0` in both header sets (`x-app-version` and `apollographql-client-version`).
- If the version cannot be found in the chunk, fail with a clear error rather than sending a guessed value.

## Capabilities

### New Capabilities
- `espn-bet-fetch`: how the ESPN Bet source derives the values it needs from the site (persisted-query SHAs and app version) and sends them on its API calls.

### Modified Capabilities

## Impact

- `src/espn_bet.py`: new version extraction next to `get_sha_token`; `make_api_calls` passes it on.
- `src/apis.py`: `espn_startup_get` and `espn_marketplace_get` take the version instead of the literal.
- No new dependencies, no AWS/Lambda config change (HTTP only, same as today).
- Out of scope: other hardcoded headers (`x-install-id`, `x-dma`, datadog trace ids), the geo/variables in the query URLs.
