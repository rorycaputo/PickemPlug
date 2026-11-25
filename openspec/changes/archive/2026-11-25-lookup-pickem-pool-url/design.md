# Design

## Context

See proposal.md for the motivation. Here's what the live lobby page (`https://picks.cbssports.com/football/lobby`) looked like on 2026-11-25:

- **Logged in:** 200, with no redirect. The page embeds Apollo SSR state (`window[Symbol.for("ApolloSSRDataTransport")]`) where `"memberships":` appears 4 times. The first occurrence holds full objects: `{"__typename":"Member", ..., "pool":{"id","name","url","gameInstanceUid","season", ...}}`, with `pool.url` = `https://picks.cbssports.com/football/pickem/pools/kbxw63b2ge3dmmbqge3ta===` (no `entryId`). The pool's link is `<a data-cy="NFL 5 Alive" href="<pool.url>?entryId=…">`. The page has no "Log In" link.
- **Logged out:** also 200 with no redirect. Every `"memberships":` occurrence is `[]`, `currentUser.id` decodes to `User:undefined`, and the page has a "Log In" link to `https://www.cbssports.com/login/?xurl=https%3A%2F%2Fpicks.cbssports.com%2F…`. When the user tried that link in a browser, CBS redirected back to the lobby after login.
- Over plain HTTP, `pool.url` returns the pool page with its spreads (32 on that date).

The current flow is `get_pickem_lines` → `get_pickem_html` → `fetch_pickem_html_with_session(cookies, POOL_URL)`, falling back to `fetch_pickem_html_with_browser` → `selenium_pa.get_pickem_html(u, p, POOL_URL)`.

## Goals / Non-Goals

**Goals:**
- Each strategy looks the pool up in the lobby itself.
- Share one membership parser between the HTTP path and the Selenium path.
- Keep the change small: a few short functions, with no general parser for the Apollo state.

**Non-Goals:**
- Making the pool name or game configurable through CLI, environment or Lambda config. They stay module constants.
- Caching the looked-up URL between runs.
- Changing the saved-session format, the SSM handling, or how cookies are saved.

## Decisions

### 1. Parse only the `memberships` arrays, with `json.JSONDecoder.raw_decode`
`find_pool_url(page_html)` goes through each `"memberships":` occurrence and calls `raw_decode` on the text right after it. It returns `pool.url` for the first member whose `pool.gameInstanceUid == GAME_INSTANCE_UID` and `pool.name == POOL_NAME`, and skips any entry that's missing those fields (later occurrences are differently shaped event payloads). It also returns the sorted set of pool names it saw, so the error message can list them.
- *Alternatives:* (a) Extract and parse the whole Apollo push payload. It isn't pure JSON (it contains `undefined`), so that's fragile. (b) Regex the `<a data-cy=…>` anchor. That's simpler, but it ignores `gameInstanceUid`, and `data-cy` is a test hook that could change. (c) lxml on the anchor's `data-neuron-pool-data` attribute. That has `poolName` and `isPickemPool` but not `gameInstanceUid`.
- Each array is valid JSON, as observed, so `raw_decode` handles it without any knowledge of the surrounding structure.

### 2. The lobby is the login check; the pool page keeps its spreads check
`fetch_pickem_html_with_session(cookies)`, in one `requests.Session`:
1. It GETs the lobby. A request error, a final path in `LOGGED_OUT_PATHS`, or no `"memberships"` entries at all mean the session is logged out → return `None` and fall back to the browser login.
2. If there are memberships but none match, it raises `RuntimeError` listing the pool names it found. A browser login would land on the same lobby, so it can't help.
3. Otherwise it GETs `pool.url` with the same `requests.Session` and applies the pool-page check, renamed `is_pool_page_with_spreads` because the lobby now handles login. Step 1's condition is `is_logged_in_lobby`. Neither check tests the status code, because `apis.get` already raises on error statuses. It returns the HTML, or `None` if that check fails. The return contract is the same as today.

That answers the question in the request. The lobby is where we can actually tell logged in from logged out, because the pool page alone couldn't separate "logged out" from "wrong pool". The pool-page check still costs nothing and still catches the "no spreads" case the spec already covers, so it stays.

The signal for logged out is "no members in any `memberships` array", not the absence of "Log In" text or `User:undefined`, because the membership array is the same structure we're already parsing. A logged-in account with zero memberships of any kind is treated as logged out. The browser path then can't find the pool either, and the run ends with the existing "no Pickem page could be obtained" error. That's acceptable.

### 3. `get_pickem_html` and `get_pickem_lines` are unchanged
Each strategy does its own lobby lookup, so no URL has to be passed between them. `get_pickem_lines` → `get_pickem_html` stays the same, apart from dropping the `POOL_URL` argument from the browser call.

### 4. The Selenium login is lobby-only
`selenium_pa.get_pickem_html(u, p)`:
1. Open `LOBBY_URL` and click the "Log In" link. The logged-out lobby is confirmed to have one.
2. Submit the email and password, then wait until `pickem.find_pool_url(driver.page_source)` returns a URL. That one wait covers the redirect back to the lobby, the lobby loading, and the login having worked (a logged-out lobby has no memberships), with no separate redirect or cookie check.
3. Click `//a[starts-with(@href, '<pool_url>')]`.
4. Wait for `data-cy='spread'` as today, and return `(page_source, cookies)`.

- *Alternative considered:* when the HTTP lobby check found the pool URL but the pool page then failed, start Selenium at that URL so its `/join` login redirects straight to the pool. The old code relied on that redirect, so it works. But it would make the HTTP path return the URL too, thread it through `get_pickem_html`, and add a second browser branch to test, all for a case that almost never happens: both HTTP requests use the same session seconds apart. Rejected.

`selenium_pa` imports `LOBBY_URL` and `find_pool_url` from `pickem`. That's safe: `pickem` only imports `selenium_pa` lazily inside `fetch_pickem_html_with_browser`, so `pickem` is already loaded, and importing `pickem` still never loads selenium.
- *Alternative:* pass the parser in as an argument. That avoids the import but adds plumbing for no benefit.

### 5. Constants replace `POOL_URL`
`LOBBY_URL`, `GAME_INSTANCE_UID = 'cbs-football-pickem-manager'` and `POOL_NAME = 'NFL 5 Alive'` go in `pickem.py`. `POOL_URL` and the comment describing the `/join` redirect are removed.

## Risks / Trade-offs

- [CBS changes how it embeds the SSR state, or renames keys] → `find_pool_url` finds nothing. Logged in, that looks like "logged out", so the run goes to the browser fallback, which can't find the pool either and fails with "no Pickem page could be obtained". The local Selenium log and screenshot show the lobby. Same approach as the ESPN Bet version regex: inspect the live page and adjust, with no fallback literal.
- [The pool is renamed] → It's a clear error listing the current names, and the fix is a one-line change to the constant.
- [The browser's rendered `page_source` doesn't include the SSR `memberships` script the way the HTTP response does] → Step 2's wait would then time out on a logged-in lobby. Fall back to waiting for the pool's `<a>` and reading its `data-neuron-pool-data` (`poolName`, `isPickemPool`). The tasks include one real browser login run, done by moving the auth file aside temporarily, before the change is considered done.
- [An extra request on every run] → It's one small GET. It reuses the same `requests.Session` and timeout.

## Migration Plan

No data migration is needed. Deploy to Lambda as usual after merging: the Lambda currently has the old hardcoded URL. To roll back, revert the commit.
