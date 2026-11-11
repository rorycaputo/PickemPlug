# AGENTS.md

## Runtime environments

This app runs in two places, and they have different capabilities:

- **Local (developer machine)** -- `python __main__.py`. Has Selenium/Firefox
  (`pipenv install --dev`) and the CBS credentials.
- **AWS Lambda** -- `lambda_function.lambda_handler`. HTTP only: no Selenium,
  no browser, and no CBS credentials.

## Pickem login and credentials

- The Selenium browser login (`pickem.fetch_pickem_html_with_browser`) is a
  **local-only** fallback. Its job is to produce a fresh CBS session when the
  saved one has expired. Lambda never runs it; there, an expired session is a
  clear error, by design.
- `PICKEM_EMAIL` / `PICKEM_PASSWORD` are read from the environment only when
  the browser login runs, and only on a local machine. **Never** add them to
  Lambda configuration, SSM, Secrets Manager, or any other AWS store, and never
  put them in source or committed files. Locally they live in the gitignored `.env`.
- Keep `selenium` an optional, lazy import (`[dev-packages]` in the Pipfile).
  Importing `pickem` or the Lambda handler must never load it.
- The saved session (auth file) is a bearer credential. Never commit it.
- In S3 storage mode (`PICKEM_STORAGE=s3`, i.e. Lambda) the saved session is
  read from the SSM SecureString `/pickemplug/pickem-auth`. The app only ever
  reads it and must never write it; it is refreshed by hand from the local
  `resources/pickem_auth.json` after a local browser login.