# Tasks

## 1. Lobby lookup and HTTP path (`src/pickem.py`)

- [x] 1.1 Replace `POOL_URL` with `LOBBY_URL`, `GAME_INSTANCE_UID` and `POOL_NAME`, and remove the comment describing the `/join` redirect. Verify `grep -rn "kbxw63b2\|POOL_URL" src` finds nothing.
- [x] 1.2 Add `find_pool_url(page_html)`, which `raw_decode`s each `"memberships":` array and returns `(pool_url or None, pool names seen)` (design decision 1). Verify it against the live lobby: with the saved session it returns `…/pools/kbxw63b2ge3dmmbqge3ta===`, and logged out (no cookies) it returns `(None, [])`.
- [x] 1.3 Rework `fetch_pickem_html_with_session(cookies)` to do the lobby GET first, then the pool GET, returning the HTML or `None` as today. Logged in with no match raises with the pool names (design decision 2). Verify it live: the saved session returns HTML with spreads, empty cookies return `None` and print the logged-out message, and a temporarily changed `POOL_NAME` raises listing `NFL 5 Alive`.
- [x] 1.4 Drop the pool URL argument from the browser call in `fetch_pickem_html_with_browser` (design decision 3). Verify `python src --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark` completes through the saved session without starting a browser, and that `python -c "import sys; sys.path.insert(0,'src'); import pickem, lambda_function; print('selenium' in sys.modules)"` prints `False`.
- [x] 1.5 Name each page's check: move the lobby login condition into `is_logged_in_lobby(response, pool_names)`, rename `is_logged_in_pickem_page` to `is_pool_page_with_spreads`, drop its redundant `status_code == 200` (since `apis.get` already raises on error statuses), and change its failure message to say the pool page had no spreads. Verify `grep -rn is_logged_in_pickem_page src` finds nothing, and rerun the 1.3 live checks.

## 2. Browser login (`src/selenium_pa.py`)

- [x] 2.1 Change `get_pickem_html(u, p)` to open `LOBBY_URL`, click "Log In", submit the login, wait until `pickem.find_pool_url(driver.page_source)` returns a URL (after CBS redirects back to the lobby), click `//a[starts-with(@href, pool_url)]`, and wait for spreads (design decision 4). Verify with one real browser login: move `resources/pickem_auth.json` aside, run `python src --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark`, and check that Selenium clicks into the pool, spreads are read, and a new auth file is saved. If the run fails, restore the moved-aside file.

## 3. Integration checks

- [x] 3.1 Run the unit tests (`cd src && python -m unittest discover -s tests`) and verify all pass.
- [x] 3.2 Check README.md for any text that describes the pool URL or the Selenium start page. Verify none needs changing: the current lines only say "saved session first, Selenium if it has expired", which still holds.

## Workflow follow-up

- Redeploy the Lambda (`deploy/` scripts) after merging, because the deployed function still has the old hardcoded pool URL.
- If 2.1 produced a new local session, decide whether to upload it to SSM with `scripts/upload-pickem-auth.sh`. The current SSM session is still valid until 2026-12-10.
- Archive the change after review.
