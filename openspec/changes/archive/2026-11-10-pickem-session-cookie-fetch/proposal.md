# Proposal

## Why

The CBS Pickem fetch launches a full Firefox via Selenium on every run just to log in and read one server-rendered page. That blocks running on AWS Lambda, where there is no browser. A HAR capture of the login shows it is gated by reCAPTCHA Enterprise, so it cannot be replayed with plain HTTP. It also shows the login session lasts 30 days and that the logged-in pool page already contains the spreads. So most runs can skip the browser by reusing the saved session, and the browser is needed only to log in again.

## What Changes

- The live Pickem fetch first tries a plain HTTP GET of the pool page using session cookies read from a local JSON file in `resources/`.
- If that attempt does not return a logged-in page with spreads (no auth file, expired or rejected session, request error), the existing Selenium login runs as a fallback.
- A successful Selenium login writes (or refreshes) the auth JSON file, so the next run can use the GET path.
- The Selenium code is imported only when the fallback runs, and `selenium` moves out of the default install group, so a GET-only deployment does not need it installed. If the fallback is needed and Selenium is not installed, the run fails with a clear message instead of an import traceback.
- The new GET reuses the shared request helper in `apis.py` rather than adding a second HTTP path.
- The saved Pickem page used when the fetch option is false stays one file, `resources/pickem.html`, written by whichever strategy succeeded. The auth JSON is a separate file because it holds a credential, not page data.
- When both strategies fail, the run reports that clearly instead of failing later with an unrelated error.

Out of scope: AWS storage for the auth file (S3, Secrets Manager), alerting on session expiry, moving credentials out of `pickem.py`, the other Lambda blockers (read-only filesystem, timezones, packaging), and replaying the login with `requests`.

## Capabilities

### New Capabilities
- `pickem-session-fetch`: how Pickem spreads are obtained live: session-cookie GET first, browser login fallback, the persisted auth file and its contents, and the behavior when neither strategy works.

### Modified Capabilities

<!-- None. The existing fetch_pickem option still means "fetch live" or "use saved data"; only how a live fetch is performed changes. -->

## Impact

- Code: `pickem.py` (strategy order, auth file read/write, failure reporting), `selenium_pa.py` (return/persist session cookies after login), `apis.py` (reused, possibly small adjustments for cookie-bearing requests).
- Dependencies: `selenium` moves from `[packages]` to `[dev-packages]` in the Pipfile (and the lock file is regenerated), so the default install excludes it.
- Files: new gitignored `resources/pickem_auth.json` holding session cookies. It is a bearer credential and must never be committed; `resources/` is already gitignored.
- Docs: README setup and Pickem-source wording.
- Behavior: a normal run no longer opens a browser while the saved session is valid.
