# Tasks

## 1. Make Selenium optional

- [x] 1.1 Move `selenium` from `[packages]` to `[dev-packages]` in the Pipfile and regenerate `Pipfile.lock`; verify `Pipfile` lists it only under dev and the lock's `default` section no longer contains it
- [x] 1.2 Remove the top-level `import selenium_pa` from `pickem.py` (the browser path imports it lazily in group 4); verify `python -c "import sys; sys.modules['selenium'] = None; import pickem"` succeeds
- [x] 1.3 Confirm `resources/` is gitignored for the new auth file; verify `git check-ignore resources/pickem_auth.json` prints the path

## 2. Auth file read and write

- [x] 2.1 Add the authenticating-cookie names as a single constant (start with `auth_session` and `auth_state`) and a function in `pickem.py` that builds the auth JSON envelope (version, saved_at, expires_at as the earliest cookie expiry, filtered cookie list) from Selenium cookie dicts; verify by calling it with a sample cookie list from a Python shell and checking the output shape against the spec
- [x] 2.2 Add a function that loads the auth file and returns the cookies, treating a missing file, invalid JSON or an unknown version as "no session" with a one-line message and no cookie values printed; verify with a missing file, a file containing `{`, and a file with `"version": 99`
- [x] 2.3 Add a function that writes the auth JSON through `util.write_string_to_file` to `resources/pickem_auth.json`; verify the file appears, parses as JSON, and is ignored by git

## 3. HTTP session attempt

- [x] 3.1 Add a function that builds a fresh `requests.Session`, loads the saved cookies, requests the Pickem pool page through `apis.call_get_api_with_session` with that explicit session, and returns the page HTML or `None`; treat a non-tuple return (the helper returns exception objects on failure) as a failed attempt; verify by pointing it at a bad URL and seeing `None` rather than an exception
- [x] 3.2 Add the logged-in check (HTTP 200 after redirects, final URL not under the login or join paths, markup contains `data-cy="spread"`) and apply it before returning the page; verify it rejects a saved login-page body and accepts the spread markup (using a page saved from a real run)
- [x] 3.3 Run the attempt against the live site using cookies from a real login; verify it returns spread markup. If it does not, widen the cookie-name constant from 2.1 and record the final list in the design's decision on cookie subset

## 4. Browser fallback persists the session

- [x] 4.1 Change `selenium_pa.get_pickem_html` to return the page source together with `driver.get_cookies()` on success and `None` on failure; verify by running it once locally and checking both parts are returned and `auth_session` is among the cookies
- [x] 4.2 Add a fallback function in `pickem.py` that imports `selenium_pa` inside a `try`, calls it, and on success writes the auth file via 2.3; on `ImportError` raises the "session unusable, browser fallback unavailable" error; verify the `ImportError` message by running with `sys.modules['selenium'] = None`, and verify a failed login leaves an existing auth file byte-for-byte unchanged

## 5. Wire the strategies together

- [x] 5.1 Update `get_pickem_lines(fetch=True)` to try the HTTP attempt, then the fallback, then raise a clear "no Pickem page could be obtained" error if both fail; keep the script/style stripping, the save to `resources/pickem.html` and the parsing unchanged; verify the three live scenarios below
  - Valid auth file: run `python __main__.py --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark` and confirm no browser window opens and the page is saved
  - No auth file: delete it, rerun, confirm the browser opens, the run succeeds, and a new auth file exists
  - Corrupted session: edit a cookie value in the auth file, rerun, confirm the fallback runs and the file is refreshed
- [x] 5.2 Verify `--no-fetch-pickem` still reads `resources/pickem.html` after runs through each strategy and does not read or require the auth file (delete the auth file and run)
- [x] 5.3 Verify both strategies fail cleanly: with an invalid auth file and `sys.modules['selenium'] = None`, the run stops with the expired-session / fallback-unavailable message rather than an `AttributeError`

## 6. Documentation

- [x] 6.1 Update the README setup to use `pipenv install --dev` for local runs and say why; update the `--no-fetch-pickem` row ("CBS, via Selenium") and the Lambda note so they reflect the session-cookie-first behavior; verify each README statement against the final behavior, and add nothing beyond the affected lines

## 7. Integration check

- [x] 7.1 With a fresh `pipenv install --dev` environment, run the full pipeline (`python __main__.py`) twice back to back; verify the second run starts no browser, the CSV and HTML outputs are produced both times, and `python -m unittest discover tests` still passes
- [x] 7.2 In a non-dev environment (`pipenv install` without `--dev`), import `pickem_plug` and `lambda_function`; verify both import without `selenium` installed

## Workflow follow-up

- Archive the change after the review requirements are satisfied.
- Verify the archived result, including that `pickem-session-fetch` appears in `openspec/specs/`.
