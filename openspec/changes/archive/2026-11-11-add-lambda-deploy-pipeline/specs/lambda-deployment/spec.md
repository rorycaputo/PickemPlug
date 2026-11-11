# Spec Delta

## Purpose

Defines the local, operator-run pipeline that builds the `pickem` Lambda package, enforces the function's configuration, publishes each deploy as an immutable version and verifies it before pointing the `live` alias at it.

## ADDED Requirements

### Requirement: Build a package for the Lambda runtime
The build SHALL produce a zip whose compiled dependencies are binary wheels for the Linux platform, architecture and Python version named in the deploy config file, whatever operating system the build runs on. The build SHALL fail, without writing a package, when any dependency has no matching binary wheel, rather than building it from source.

#### Scenario: Build on Windows
- **WHEN** the build runs on a Windows machine with the config set to runtime `python3.14` and architecture `x86_64`
- **THEN** the zip's compiled modules (such as `lxml` and `brotli`) are `cp314` Linux `x86_64` builds and contain no Windows `.pyd` files

#### Scenario: No matching wheel
- **WHEN** a locked dependency has no binary wheel for the configured platform and Python version
- **THEN** the build exits non-zero naming the dependency, and no package is produced

#### Scenario: Config changes the target
- **WHEN** the config file's architecture or runtime is changed
- **THEN** the next build targets the new architecture or Python version without any other edit

### Requirement: Package only runtime dependencies and app code
The package SHALL contain the locked runtime dependencies (the `[packages]` section, at the versions in `Pipfile.lock`) and the project's top-level `*.py` files, except `__main__.py`, `__init__.py` and `selenium_pa.py`. It SHALL NOT contain dev dependencies or any other project file or directory.

#### Scenario: Dev packages excluded
- **WHEN** a package is built
- **THEN** it contains neither `selenium` nor `boto3`

#### Scenario: Non-code files excluded
- **WHEN** a package is built
- **THEN** it contains nothing from `tests/`, `docs/`, `resources/`, `scripts/`, `openspec/`, `out/` or `build/`, and no `.env`

#### Scenario: New module picked up
- **WHEN** a new top-level `.py` module is added to the project
- **THEN** the next package includes it with no change to the build

#### Scenario: Locked versions
- **WHEN** a package is built
- **THEN** each runtime dependency in it is the version pinned in `Pipfile.lock`

### Requirement: Build can run without deploying
The build SHALL be runnable on its own, without AWS credentials and without changing anything in AWS, and SHALL report the path of the package it wrote.

#### Scenario: Build only
- **WHEN** the operator runs the build alone with no AWS credentials configured
- **THEN** a package and its manifest are written locally and no AWS call is made

### Requirement: Keep a record of every build and deploy
Each run SHALL write its own directory under `build/` named from its timestamp and git sha, holding the zip, a log of the run's output and a manifest with the git sha, the zip's sha256, the resolved dependency versions and the timestamp. Each deploy run SHALL also append one line to a deploy log recording its time, sha, published version and outcome. Earlier runs' records SHALL NOT be removed. `build/` and `package.zip` SHALL be gitignored.

#### Scenario: Two runs
- **WHEN** the pipeline runs twice
- **THEN** `build/` holds two separate run directories, each with its own zip, manifest and log, and the deploy log has two lines

#### Scenario: Failed run
- **WHEN** a deploy run fails at any stage
- **THEN** its run log and a deploy-log line recording the failed stage are still written

### Requirement: Preflight before any change
Before running tests, building or changing anything in AWS, the pipeline SHALL confirm that the AWS credentials are valid, that the target function exists in the configured region, that the git working tree is clean, and that the session-upload script's access check passes. It SHALL stop with a message naming the failed check otherwise. An explicit flag SHALL allow a dirty tree, and the run SHALL then be recorded as dirty.

#### Scenario: Function missing
- **WHEN** the configured function does not exist in the configured region
- **THEN** the pipeline exits non-zero naming that check, before tests or the build run

#### Scenario: Dirty tree
- **WHEN** the working tree has uncommitted changes and the allow-dirty flag is not given
- **THEN** the pipeline exits non-zero before tests or the build run

#### Scenario: Dirty tree allowed
- **WHEN** the working tree has uncommitted changes and the allow-dirty flag is given
- **THEN** the pipeline continues, and the manifest and the published version's description mark the sha as dirty

### Requirement: Tests gate the deploy
The pipeline SHALL run the project's unit tests after preflight and SHALL stop without building or changing anything in AWS when any test fails.

#### Scenario: Failing test
- **WHEN** a unit test fails
- **THEN** the pipeline exits non-zero and no package is uploaded and no AWS state changes

### Requirement: Upload the session as a pipeline step
The pipeline SHALL run the existing session-upload script, against the region in the deploy config, after the build and before deploying, and SHALL stop when that script fails. A flag SHALL skip this step. The pipeline SHALL NOT read or upload the session itself.

#### Scenario: Default run
- **WHEN** the pipeline runs without the skip flag
- **THEN** the session-upload script runs in the configured region before the function is changed

#### Scenario: Upload fails or is aborted
- **WHEN** the session-upload script exits non-zero (for example, an expired session with no interactive terminal)
- **THEN** the pipeline exits non-zero and the function is not changed

#### Scenario: Skipped
- **WHEN** the skip-auth-upload flag is given
- **THEN** the session-upload script is not run and SSM is not written

### Requirement: Enforce the function configuration from a checked-in file
On every deploy the pipeline SHALL set the function's handler, runtime, architecture, timeout, memory and environment variables to the values in the checked-in deploy config file, so that the live function matches the file after a successful deploy. Environment variables not in the file SHALL be removed. The pipeline SHALL NOT change the function's execution role.

#### Scenario: Drifted function
- **WHEN** the live function has handler `lambda_function.main`, a 3 s timeout and no environment variables, and a deploy succeeds
- **THEN** the function has the handler, timeout, memory, runtime, architecture and environment variables from the config file

#### Scenario: Extra variable
- **WHEN** the live function has an environment variable that the config file does not list
- **THEN** after the deploy that variable is gone

### Requirement: The deploy config never holds secrets
The pipeline SHALL refuse to deploy, before changing anything in AWS, when the deploy config's environment variables include `PICKEM_EMAIL`, `PICKEM_PASSWORD` or the saved session. The deploy config SHALL hold only non-secret settings.

#### Scenario: Credential in config
- **WHEN** the config file's environment includes `PICKEM_PASSWORD`
- **THEN** the pipeline exits non-zero naming the variable, and nothing in AWS is changed

### Requirement: Publish each deploy as a numbered version
After updating the code and configuration, the pipeline SHALL publish a new function version whose code is the package just built and whose description holds the git sha and commit subject, and SHALL report the version number.

#### Scenario: Successful deploy
- **WHEN** code and configuration updates succeed
- **THEN** a new version is published with the run's sha and subject as its description, and the version number appears in the output and the deploy log

#### Scenario: Code changed underneath
- **WHEN** the function's code no longer matches the package this run uploaded at the time of publishing
- **THEN** no version is published and the pipeline exits non-zero

### Requirement: Smoke-invoke the new version
By default the pipeline SHALL invoke the newly published version with every fetch option set to false and report whether the invocation succeeded, saving the response with the run's records. A flag SHALL skip the invocation. A failed invocation SHALL make the pipeline exit non-zero.

#### Scenario: Smoke passes
- **WHEN** the new version is invoked and returns without a function error
- **THEN** the pipeline reports success and saves the response in the run directory

#### Scenario: Smoke fails
- **WHEN** the invocation returns a function error or times out
- **THEN** the pipeline reports the failure with the error and exits non-zero

#### Scenario: Smoke skipped
- **WHEN** the no-invoke flag is given
- **THEN** the function is not invoked

### Requirement: The live alias only points at verified versions
After a passing smoke invocation the pipeline SHALL point the `live` alias at the new version, creating the alias if it does not exist. When the smoke invocation fails or is skipped, the alias SHALL stay where it was. Rolling back SHALL only require pointing `live` at an earlier version.

#### Scenario: First deploy
- **WHEN** no `live` alias exists and the smoke invocation passes
- **THEN** a `live` alias is created pointing at the new version

#### Scenario: Smoke fails after an earlier good deploy
- **WHEN** `live` points at version 4 and version 5's smoke invocation fails
- **THEN** `live` still points at version 4

#### Scenario: Smoke skipped
- **WHEN** a deploy runs with the no-invoke flag
- **THEN** the new version is published but `live` is not moved

### Requirement: Stop at the first failed stage
The pipeline SHALL run its stages in the order preflight, test, build, session upload, deploy, smoke invoke, alias, and SHALL exit non-zero at the first stage that fails, naming that stage, without running later stages.

#### Scenario: Build fails
- **WHEN** the build stage fails
- **THEN** the pipeline exits non-zero naming the build stage, and the session upload, deploy, invoke and alias stages do not run
