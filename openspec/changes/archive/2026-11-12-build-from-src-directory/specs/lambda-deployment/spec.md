## MODIFIED Requirements

### Requirement: Package only runtime dependencies and app code
The package SHALL contain the locked runtime dependencies (the `[packages]` section, at the versions in `Pipfile.lock`) and the Python files in the project's `src/` directory, placed at the package root, except `__main__.py`, `selenium_pa.py` and the `src/tests` directory. It SHALL NOT contain dev dependencies or any other project file or directory.

#### Scenario: Dev packages excluded
- **WHEN** a package is built
- **THEN** it contains neither `selenium` nor `boto3`

#### Scenario: Non-code files excluded
- **WHEN** a package is built
- **THEN** it contains nothing from `src/tests/`, `docs/`, `resources/`, `scripts/`, `openspec/`, `out/` or `build/`, and no `.env`

#### Scenario: App modules at the package root
- **WHEN** a package is built
- **THEN** `lambda_function.py` and the other `src/` modules sit at the root of the zip, with no `src/` directory inside it, so the handler remains `lambda_function.lambda_handler`

#### Scenario: Excluded modules
- **WHEN** a package is built
- **THEN** it contains neither `__main__.py` nor `selenium_pa.py`

#### Scenario: New module picked up
- **WHEN** a new `.py` module is added to `src/`
- **THEN** the next package includes it with no change to the build

#### Scenario: Locked versions
- **WHEN** a package is built
- **THEN** each runtime dependency in it is the version pinned in `Pipfile.lock`

### Requirement: Tests gate the deploy
The pipeline SHALL run the project's unit tests, located in `src/tests`, after preflight and SHALL stop without building or changing anything in AWS when any test fails. The tests SHALL be able to import the app modules as the Lambda package does, by their bare names.

#### Scenario: Failing test
- **WHEN** a unit test fails
- **THEN** the pipeline exits non-zero and no package is uploaded and no AWS state changes

#### Scenario: Tests found in their new location
- **WHEN** the pipeline runs its test stage
- **THEN** the tests in `src/tests` are discovered and run, and a run that finds none does not count as passing
