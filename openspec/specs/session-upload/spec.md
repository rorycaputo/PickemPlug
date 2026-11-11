# session-upload Specification

## Purpose

Defines the local operator script that publishes the saved Pickem session to the SSM parameter the Lambda reads, so the session in AWS can be created and refreshed without hand-copying a credential.

## Requirements

### Requirement: Upload the saved session to SSM
The script SHALL store the exact contents of `resources/pickem_auth.json` as the SecureString parameter `/pickemplug/pickem-auth`. It SHALL create the parameter when absent and overwrite it when present.

#### Scenario: First upload
- **WHEN** the auth file exists and the parameter does not
- **THEN** the parameter is created as a SecureString holding the file's contents

#### Scenario: Refresh
- **WHEN** the auth file exists and the parameter already exists
- **THEN** the parameter's value is replaced with the file's contents

### Requirement: Generate the session when the auth file is missing
When `resources/pickem_auth.json` does not exist, the script SHALL tell the user to run the app locally with the DraftKings, ESPN Bet and Odds Shark fetchers switched off, wait for the user to confirm, and re-check for the file. It SHALL continue with the upload once the file exists and stop with an error if it still does not. When there is no interactive terminal, it SHALL stop with that same instruction instead of waiting.

#### Scenario: File missing, user generates it
- **WHEN** the auth file is missing and the user generates it and confirms
- **THEN** the script continues and uploads it

#### Scenario: File still missing after confirmation
- **WHEN** the user confirms but the auth file still does not exist
- **THEN** the script exits non-zero without calling SSM

#### Scenario: Non-interactive run
- **WHEN** the auth file is missing and the script has no interactive terminal
- **THEN** it exits non-zero, printing the command to generate the file

### Requirement: Warn when the saved session has expired
When `resources/pickem_auth.json` exists and its `expires_at` time is in the past, the script SHALL warn that the session has expired and offer three choices: regenerate it, upload it anyway, or abort. Regenerating SHALL follow the same flow as a missing file and then continue with the new file.

#### Scenario: Expired, user regenerates
- **WHEN** the auth file is expired and the user chooses to regenerate, runs the app, and confirms
- **THEN** the script re-reads the file and uploads the new session

#### Scenario: Expired, user uploads anyway
- **WHEN** the auth file is expired and the user chooses to upload it anyway
- **THEN** the script uploads the file as is

#### Scenario: Expired, user aborts
- **WHEN** the auth file is expired and the user chooses to abort
- **THEN** the script exits without calling SSM

#### Scenario: Regenerated file still expired
- **WHEN** the user regenerates but the file is still expired afterwards
- **THEN** the script warns again and offers the same three choices

#### Scenario: Valid session
- **WHEN** the auth file's `expires_at` is in the future
- **THEN** the script uploads without any expiry prompt

### Requirement: Expiry check fails closed
When there is no interactive terminal, the script SHALL NOT upload an expired session. A file whose `expires_at` is absent or unreadable SHALL be uploaded without the expiry check.

#### Scenario: Expired, non-interactive run
- **WHEN** the auth file is expired and the script has no interactive terminal
- **THEN** it exits non-zero without uploading, printing the warning and the command to regenerate

#### Scenario: No readable expiry
- **WHEN** the auth file has no readable `expires_at`
- **THEN** the script uploads it without an expiry prompt

### Requirement: Verify AWS access before uploading
Before writing, the script SHALL confirm the AWS CLI is installed and that the current credentials are valid and can reach SSM, and SHALL stop with a message naming the failed check otherwise. A `--check` option SHALL run only these checks and perform no write.

#### Scenario: CLI missing or credentials invalid
- **WHEN** the AWS CLI is not installed or the credentials are rejected
- **THEN** the script exits non-zero with a message saying which check failed, and nothing is written

#### Scenario: Check-only mode
- **WHEN** the script is run with `--check` and access works
- **THEN** it reports the AWS account and region in use and exits zero without writing the parameter or requiring the auth file

### Requirement: AWS settings come from the environment and .env
The script SHALL read `AWS_DEFAULT_REGION` and `AWS_PROFILE` from the environment, falling back to the project's `.env`, and SHALL NOT read, print or forward `PICKEM_EMAIL` or `PICKEM_PASSWORD`. Values already set in the environment SHALL take precedence over `.env`.

#### Scenario: Region from .env
- **WHEN** `AWS_DEFAULT_REGION` is unset in the environment but set in `.env`
- **THEN** the script uses the `.env` value

### Requirement: The session value is never exposed
The script SHALL pass the session to AWS from the file rather than as a command-line argument, and SHALL NOT print its contents.

#### Scenario: Successful upload output
- **WHEN** an upload succeeds
- **THEN** the output names the parameter, region and version, and contains none of the session's cookie values
