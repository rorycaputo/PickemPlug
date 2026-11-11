# Proposal

## Why

In S3 mode the Lambda reads the Pickem session from the SSM SecureString `/pickemplug/pickem-auth` and never writes it (see `pickem-session-fetch`). Today that parameter is filled by hand-copying `resources/pickem_auth.json`, which is error-prone for a bearer credential and has to be repeated whenever CBS expires the session. The S3 wiring is done, so the upload is the next blocker to deploying.

## What Changes

- Add a local bash script, `scripts/upload-pickem-auth.sh`, that uploads `resources/pickem_auth.json` to the SSM SecureString `/pickemplug/pickem-auth`, creating the parameter on first run and overwriting it afterwards.
- If the auth file is missing, the script tells the user to generate it with a local run that skips the three sportsbook fetchers, waits for them, then continues the upload.
- If the auth file exists but its `expires_at` has passed, the script warns and offers the same regenerate flow, or uploading the stale file anyway, or aborting.
- The script reads optional AWS settings (region, profile) from the gitignored `.env`; it never reads or forwards `PICKEM_EMAIL` / `PICKEM_PASSWORD`.
- The script has a `--check` mode that only verifies the AWS CLI is installed, credentials work, and SSM is reachable, so the one-time "does my AWS CLI have SSM access" step is a command rather than ad hoc.
- Document the one-time AWS setup (verify the CLI, first upload creates the parameter) and the refresh routine in the README.

## Capabilities

### New Capabilities
- `session-upload`: A local, operator-run tool that publishes the saved Pickem session to the SSM parameter the Lambda reads, including prerequisite checks and generating the session when absent.

### Modified Capabilities
<!-- None. The app itself still never writes SSM; the script is a separate operator tool outside the app. -->

## Impact

- New file: `scripts/upload-pickem-auth.sh`.
- `README.md`: the AWS > Storage note about copying the session "by hand" is replaced by the script; add the one-time setup steps.
- No change to application code, Lambda config, or dependencies. Requires the AWS CLI v2 (already installed locally) and a bash (Git Bash on Windows).
- Out of scope: Lambda's IAM permissions to read the parameter, the bucket, deployment packaging, and automatic refresh of an expired session.
