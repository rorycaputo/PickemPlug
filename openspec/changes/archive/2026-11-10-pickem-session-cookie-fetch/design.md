# Design

## Context

See proposal.md for motivation. Current state:

- `pickem.get_pickem_lines(fetch)` calls `selenium_pa.get_pickem_html(u, p)` at the top of `pickem.py`, which imports `selenium_pa` (and so `selenium`) at module load. On success it strips `<script>`/`<style>`, saves the result to `resources/pickem.html`, then parses `h3` + `data-cy="spread"`. With `fetch=False` it reads that saved file.
- `selenium_pa.get_pickem_html` returns the page source or `None`. If it returns `None`, `pickem.py` crashes later on `.xpath` of `None`.
- `apis.call_get_api_with_session(url, headers, params, session)` does a GET with a session and returns `(response, session)`, but on failure it *returns* the exception object instead of raising. Its default `session` argument is one `requests.Session()` created at import and shared by every call that omits it.
- A HAR of a real login (2026-11-10) showed: login needs a reCAPTCHA Enterprise token minted in a browser; `auth_session` (HttpOnly) and `auth_state` last 30 days; a GET of the pool page with those cookies returns the full spread markup; the pool URL redirects to a per-season pool id.

```
   get_pickem_lines(fetch=True)
            |
            v
   [1] read resources/pickem_auth.json --missing/bad--+
            |                                         |
            v                                         |
   [2] GET pool page w/ cookies (apis.py helper)      |
            |                                         |
     logged in + spreads? --no------------------------+
            | yes                                     v
            |                          [3] lazy import selenium_pa
            |                              browser login -> page + cookies
            |                              write pickem_auth.json  (on success)
            |                                         |
            +----------------+------------------------+
                             v
              save page -> resources/pickem.html -> parse (unchanged)
```

## Goals / Non-Goals

**Goals:**
- A run with a valid saved session starts no browser and imports no Selenium.
- The browser path stays exactly as capable as today, plus it persists the session.
- Reuse the existing `apis.py` GET helper instead of adding a second HTTP code path.
- Keep the parsing and saved-page behavior (`fetch=False`) unchanged.

**Non-Goals:**
- Replaying the CBS login over HTTP, or minting reCAPTCHA tokens. The browser stays the only way to log in.
- Storing or loading the auth file from S3 or any non-local place. The file is read and written through two small functions so the location can change later.
- Alerting on expiry, refreshing cookies from `Set-Cookie` on GET responses, and moving the hardcoded credentials.

## Decisions

**1. Auth file: JSON in `resources/pickem_auth.json`, separate from the saved page.**
Shape: `{"version": 1, "saved_at", "expires_at", "cookies": [{name, value, domain, path, secure, httpOnly, expiry}]}`, taken directly from Selenium's `get_cookies()` output. The saved-page file stays as is. The saved page is data that both strategies produce identically (the GET returns the same markup the browser's `page_source` did, and the script/style stripping already runs on both), so one file serves `fetch=False`. The auth file is a bearer credential with a different lifecycle (30 days vs every run), so it gets its own file. Alternatives: Netscape `cookies.txt` (no room for metadata, awkward `HttpOnly`), pickle (opaque and unsafe to load). `expires_at` is the earliest cookie expiry so a later change can warn before it lapses.

**2. Keep only the authenticating cookies, named in one constant.**
The HAR sent many consent and analytics cookies, which are not needed. Live testing showed `auth_session` + `auth_state` alone are redirected to `/join`; bisecting a real login's cookies found the pool page needs `pid` (a non-HttpOnly cookie CBS sets at login with a one-year expiry). The final set is `auth_session`, `auth_state` and `pid`: `pid` is the one that is required, and the other two are kept so the file still carries the real session. A smaller file leaks less and stays under any future size limit (SSM Standard is 4 KB). `expires_at` is the earliest expiry among these, so it reports the 30-day `auth_session` date even if `pid` outlives it.

**3. Reuse `apis.call_get_api_with_session`, with a fresh session per attempt.**
The new getter builds a new `requests.Session`, loads the cookies into it, and passes it explicitly, so the shared default session is never used and cookies do not leak between runs on a warm Lambda. Because that helper returns the exception object on failure, the getter treats anything that is not a `(response, session)` tuple as a failed attempt. The helper's default browser-like headers are used unchanged; adjust only if CBS rejects them. `requests` follows redirects by default, which handles the pool URL's per-season redirect.

**4. "Logged in" is decided from the response, not just the status.**
Success requires HTTP 200 after redirects, a final URL that is not under the login or join paths, and the markup containing `data-cy="spread"`. A 200 login page is the common failure mode, so status alone is not enough. The same check is the gate before the page is saved and parsed, so a login page never overwrites `resources/pickem.html`.

**5. Selenium is a lazy, optional import.**
`pickem.py` stops importing `selenium_pa` at the top. The fallback function imports it inside a `try`, so importing `pickem` (and the Lambda handler) never loads `selenium`. `ImportError` becomes the specific "session unusable and browser fallback unavailable" error from the spec. Python has no compile step; the practical dependency is the install, so `selenium` moves from `[packages]` to `[dev-packages]`. `pipenv install` then gives a GET-only environment (what a Lambda zip would use) and `pipenv install --dev` gives the local environment with the browser. Alternative: a separate Pipfile or requirements file for Lambda. Rejected for now because it duplicates dependency lists, and it can be revisited when packaging is designed.

**6. `selenium_pa` returns cookies as well as the page, and `pickem.py` owns the file.**
After the success wait, `selenium_pa` returns the page source together with `driver.get_cookies()` (a small tuple or result object). `pickem.py` filters, builds the envelope and writes the file, so the Selenium module stays a thin browser driver with no file knowledge. The write happens only after the page is confirmed good, which gives the "failed login leaves the file unchanged" behavior. `driver.get_cookies()` includes `HttpOnly` cookies.

**7. Fail loudly when both strategies fail.**
The current `None` flowing into `.xpath` is replaced by an explicit error that says no Pickem page could be obtained. This is within scope only because the new two-step flow adds another way to reach that state; wider failure handling across sources (discovery item 8) is not changed.

**8. Auth file writes use the existing file helper.**
`util.write_string_to_file` already creates the directory and writes UTF-8, so the JSON is dumped to a string and written through it.

## Risks / Trade-offs

- [Session cookies are a bearer credential on disk] → Stored under the already-gitignored `resources/`; the spec requires it to stay out of version control; no cookie values are printed to logs.
- [The two-cookie subset may be insufficient] → The GET falls back to the browser, so it fails safe; the first implementation task verifies the subset against the live site and widens the constant if needed.
- [The session may expire sooner than 30 days, or a datacenter IP may be blocked] → The browser fallback covers local runs. On Lambda the fallback is unavailable by design, so expiry surfaces as the clear error; alerting is a later change. IP blocking is tested when the Lambda is built (discovery item 9).
- [CBS changes the markup or the pool redirect] → Same exposure as today's Selenium path; the "spreads present" check turns it into a fallback or a clear error rather than bad data.
- [Moving `selenium` to dev-packages changes setup] → README setup is updated to `pipenv install --dev` for local use.
- [The helper returns exception objects rather than raising] → The getter normalizes this in one place; the helper itself is not rewritten, to avoid changing the other sources that use it.

## Open Questions

- Is `pid` alone enough to authenticate beyond the 30-day `auth_session` lifetime? A live bisect on 2026-11-10 showed the pool page works with `pid` only, and `pid` carries a one-year cookie expiry (2027-11-10). A cookie expiry is not proof of server-side session lifetime, so for now all three cookies are kept and `expires_at` stays the earliest expiry (about 30 days). To resolve: after day 30, delete `auth_session` and `auth_state` from the auth file and run a GET. If it still works, drop them from `AUTH_COOKIE_NAMES` and compute `expires_at` from the cookies the GET actually needs. Nothing reads `expires_at` yet and the browser fallback covers a rejected session, so this can be deferred without changing the specs or tasks; it matters once expiry alerting is added.
