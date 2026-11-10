## ADDED Requirements

### Requirement: Login credentials come from the environment
The browser login SHALL take the CBS email and password from the `PICKEM_EMAIL` and `PICKEM_PASSWORD` environment variables, with the password supplied as plain text. The system SHALL NOT contain credentials in source code or version-controlled files, and SHALL read them only when the browser login runs.

#### Scenario: Credentials set
- **WHEN** the browser login runs and both variables are set
- **THEN** the login uses those values for the email and password

#### Scenario: Valid saved session needs no credentials
- **WHEN** a live Pickem fetch succeeds through the saved session and neither variable is set
- **THEN** the fetch succeeds without error

#### Scenario: Credentials missing at login time
- **WHEN** the browser login is needed and `PICKEM_EMAIL` or `PICKEM_PASSWORD` is unset or empty
- **THEN** the run stops before starting the browser with an error naming each missing variable

#### Scenario: Local env file excluded from git
- **WHEN** a `.env` file holding the variables exists in the working tree
- **THEN** version control ignores it
