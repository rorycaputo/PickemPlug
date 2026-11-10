## Context

See proposal.md - Why. The only consumer of the credentials is the Selenium login fallback (`pickem.fetch_pickem_html_with_browser`), which only runs on a developer machine; Lambda has no Selenium and uses the saved session, so it never needs them. VS Code's `launch.json` already points `envFile` at `.env`.

## Goals / Non-Goals

**Goals:**
- No credentials in source or git going forward.
- Fail early and clearly when they are needed but absent.

**Non-Goals:**
- Any AWS secret storage (SSM/Secrets Manager) - nothing in AWS consumes these.
- Storing the session cookies in AWS - separate future change.
- Rewriting git history (the password was never committed).

## Decisions

- **Plain environment variables `PICKEM_EMAIL` / `PICKEM_PASSWORD`.** No mode/`ENV` switch: the code reads the environment wherever it runs. Alternatives: SSM SecureString (no consumer, adds IAM + boto3 code), OS keyring (extra dependency, not portable to other runners).
- **Resolve in `get_credentials()`, called inside `fetch_pickem_html_with_browser`**, after the selenium import check and before starting the browser. This keeps the lazy behavior and the existing "selenium not installed" error taking priority, and avoids launching Firefox just to fail on missing credentials.
- **No `python-dotenv`.** `.env` is loaded by VS Code (`envFile`); from a terminal, variables are set in the shell. Avoids a new dependency for a convenience.
- **Drop base64.** It gave a false sense of protection and added a failure mode (the "Did you enter it?" decode error). `selenium_pa.get_pickem_html` and unused `apis.pickem_login_post` take the plain password.

## Risks / Trade-offs

- [Email remains in git history (initial commit); the password was never committed] -> Accepted; no rotation or history rewrite needed.
- [Env vars in a terminal can leak via shell history] -> Prefer the gitignored `.env` via VS Code or a profile; document it.
- [Existing callers passing base64] -> Only `pickem.py` calls the Selenium login, and `pickem_login_post` has no callers, so nothing else breaks.

## Migration Plan

1. Set `PICKEM_EMAIL` / `PICKEM_PASSWORD` (e.g. in `.env`) with the plain (decoded) password.
2. Apply the code change; no AWS changes. Rollback is reverting the commit and restoring hardcoded values.
