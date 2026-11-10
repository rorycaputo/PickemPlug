# Proposal

## Why

The CBS login email and a base64-"encoded" password are hardcoded in `pickem.py` and committed to git. Base64 is not protection, and keeping the values out of commits by hand is error-prone. They need to come from the environment instead.

## What Changes

- Add a `get_credentials()` helper that reads `PICKEM_EMAIL` and `PICKEM_PASSWORD` from environment variables.
- Read credentials lazily, only when the browser login fallback actually runs, so HTTP-only runs with a valid saved session need no credentials.
- Remove the hardcoded email/password from `pickem.py`.
- Store the password as plain text in the environment; drop base64 decoding in `selenium_pa.py` and `apis.py`.
- Fail with a clear message naming the missing variable(s) when the browser login is needed but credentials are not set.
- Add `.env` to `.gitignore` (VS Code's launch config already loads `.env`); document the variables in the README.

Out of scope: Lambda never runs the browser login, so it needs no credentials. Storing/uploading the saved session cookies in AWS (SSM, S3, etc.) is a separate future change. No `ENV` mode switch is needed.

## Capabilities

### New Capabilities

### Modified Capabilities
- `pickem-session-fetch`: the browser login fallback gains a requirement on where credentials come from (environment, never source) and what happens when they are missing.

## Impact

- Code: `pickem.py` (remove `u`/`p`, call `get_credentials()` in `fetch_pickem_html_with_browser`), `selenium_pa.py` (plain password), `apis.py` (`pickem_login_post`, currently unused, plain password).
- Config/docs: `.gitignore`, `README.md`.
- No new dependencies; no AWS changes.
- **Operational**: the password was never committed (only the email is in history, in the initial commit), so no rotation is required. Set the existing values in the environment.
