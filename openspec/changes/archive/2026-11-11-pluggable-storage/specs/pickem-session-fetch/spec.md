# Spec Delta

## ADDED Requirements

### Requirement: Saved session source follows the storage mode
In local storage mode the saved session SHALL be the auth file `resources/pickem_auth.json`. In S3 storage mode it SHALL be the SecureString SSM parameter `/pickemplug/pickem-auth`, read with decryption and holding the same JSON document as the auth file. A missing parameter SHALL be treated like a missing auth file.

#### Scenario: S3 mode with a valid session in SSM
- **WHEN** a live Pickem fetch runs in S3 mode and the parameter holds a session CBS still accepts
- **THEN** the spreads are read from the page returned by the HTTP request and no local auth file is read

#### Scenario: S3 mode with no parameter
- **WHEN** a live Pickem fetch runs in S3 mode and the parameter does not exist
- **THEN** the system treats the session as missing and moves on to the browser login fallback

### Requirement: The system never writes the session to SSM
The system SHALL only read the SSM parameter. Populating or refreshing it is done outside the system.

#### Scenario: Browser login succeeds in S3 mode
- **WHEN** the browser login succeeds during a run in S3 mode
- **THEN** its page is used for the spreads, the SSM parameter is not written, and the run prints that the new session was not saved

## MODIFIED Requirements

### Requirement: Successful browser login refreshes the auth file
After a successful browser login in local storage mode, the system SHALL write the session cookies needed for later HTTP requests to the auth file, replacing its previous contents.

#### Scenario: Auth file created
- **WHEN** the browser login succeeds and no auth file existed
- **THEN** an auth file is created and the next live fetch uses the HTTP attempt first

#### Scenario: Auth file replaced
- **WHEN** the browser login succeeds because the saved session had expired
- **THEN** the auth file holds the new session's cookies

#### Scenario: Browser login fails
- **WHEN** the browser login does not succeed
- **THEN** the existing auth file is left unchanged

### Requirement: Auth file contents
The saved session (the local auth file, or the SSM parameter in S3 mode) SHALL be a JSON document containing a format version, the time it was saved, the time the earliest-expiring cookie expires, and a list of cookies each with at least a name, value, domain, path and expiry when one exists. The system SHALL store only the cookies needed to authenticate the HTTP request. The local auth file SHALL live in `resources/` and SHALL NOT be committed to version control.

#### Scenario: Auth file shape
- **WHEN** the browser login writes the auth file
- **THEN** the file is valid JSON with a version, a saved-at time, an expires-at time and a non-empty cookie list

#### Scenario: Auth file excluded from git
- **WHEN** the auth file exists in the working tree
- **THEN** version control ignores it

#### Scenario: Unreadable auth file
- **WHEN** the auth file exists but is not valid JSON or has an unknown version
- **THEN** it is treated as missing and the browser login runs

#### Scenario: Unreadable SSM value
- **WHEN** the SSM parameter in S3 mode is not valid JSON or has an unknown version
- **THEN** it is treated as missing, the same as an unreadable auth file
