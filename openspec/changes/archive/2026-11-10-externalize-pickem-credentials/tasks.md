# Tasks

## 1. Read credentials from the environment

- [x] 1.1 In `pickem.py`, remove the hardcoded `u` and `p`; add `get_credentials()` that reads `PICKEM_EMAIL` and `PICKEM_PASSWORD` and raises an error naming each missing/empty variable
- [x] 1.2 In `fetch_pickem_html_with_browser`, call `get_credentials()` after the selenium import check and before `selenium_pa.get_pickem_html`, passing the plain values

## 2. Drop base64

- [x] 2.1 In `selenium_pa.get_pickem_html`, send the password as given and remove the base64 decode and its error handling plus the unused `base64` import
- [x] 2.2 In `apis.pickem_login_post`, use the password as given instead of `base64.b64decode`; remove the `base64` import if unused

## 3. Ignore and document

- [x] 3.1 Add `.env` to `.gitignore`
- [x] 3.2 Update `README.md` where it describes the Pickem Selenium login: note that `PICKEM_EMAIL` and `PICKEM_PASSWORD` must be set (shell or `.env`) when the saved session has expired

## 4. Verification

- [x] 4.1 Set `PICKEM_EMAIL` and the decoded `PICKEM_PASSWORD` in `.env`, and confirm `git grep` finds no password literal in tracked files
- [x] 4.2 With the variables unset and no usable saved session, run a live Pickem fetch and confirm it stops with the missing-variable error before any browser starts
- [x] 4.3 With the variables set and the saved session removed or expired, run a live Pickem fetch and confirm the browser login succeeds and refreshes `resources/pickem_auth.json`
- [x] 4.4 With a valid saved session and no variables set, run a live Pickem fetch and confirm it succeeds
- [x] 4.5 Run `pipenv run python -m unittest discover tests` and confirm it passes
