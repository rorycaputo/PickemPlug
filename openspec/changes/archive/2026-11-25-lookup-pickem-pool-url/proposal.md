# Proposal

## Why

The Pickem pool URL is hardcoded in two places (`pickem.POOL_URL` and the Selenium login's start URL). When CBS moved the pool to a new id (`Pool:13854849` → `Pool:16600170`), the old URL started redirecting a logged-in user to `/football/lobby`, so every run failed with a misleading "session was not accepted" and an unnecessary browser login. The lobby page lists the account's pool memberships, so the URL can be looked up on each run instead.

## What Changes

- Each live Pickem fetch first loads `https://picks.cbssports.com/football/lobby` and takes the pool URL from the account's membership whose game is `cbs-football-pickem-manager` and whose pool name is `NFL 5 Alive`.
- The lobby load becomes the saved-session check: a logged-out lobby (no memberships) sends the run to the browser login, as a rejected pool page does today. The pool page keeps its existing check that spreads are present.
- The looked-up URL is used for the HTTP pool request.
- The browser login always starts at the lobby. CBS redirects back to the lobby after login, where the browser finds the same membership and clicks its link. The pool URL is almost never known before the browser runs, so there's no separate direct-to-pool path.
- A logged-in lobby with no matching membership stops the run with an error naming the pools it did find, instead of falling back to a browser login that can't help.
- The hardcoded pool URLs are removed, including the one in the Selenium login.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `pickem-session-fetch`: the saved session is checked against the lobby rather than the pool page, the pool URL comes from the lobby, the browser login finds the pool the same way, and a missing membership is a distinct error.

## Impact

- `src/pickem.py`: pool lookup from the lobby, and removal of `POOL_URL`.
- `src/selenium_pa.py`: logs in from the lobby, then finds and clicks the pool link. It no longer takes a pool URL.
- One extra HTTP request per live Pickem fetch, on both local runs and Lambda. No new dependencies, configuration or AWS changes; the saved-session format is unchanged.
