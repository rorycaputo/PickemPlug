# Design

## Context

The app only reads `/pickemplug/pickem-auth` (see `pickem-session-fetch`, "never writes the session to SSM"); populating it is "done outside the system". The saved session is a ~1.6 KB JSON file, well under the 4 KB Standard-tier parameter limit. Locally the user runs Windows with Git Bash and AWS CLI v2. `.env` is gitignored and holds the CBS credentials, which must never reach AWS (AGENTS.md).

## Goals / Non-Goals

**Goals:**
- One command to publish or refresh the session, runnable from any runtime with a bash and the AWS CLI.
- A way to confirm AWS CLI and SSM access without writing anything.

**Non-Goals:**
- Lambda IAM role/policy, S3 bucket creation, or any other deployment infrastructure.
- Proving the session is accepted by CBS; only the saved `expires_at` is checked, never the live site.
- Refreshing the session itself; the script only points the user at the app's local run.
- Running the app on the user's behalf.

## Decisions

- **Plain bash script in `scripts/`, no Makefile.** A standalone script is the conventional lightweight form for a single operator task and works the same from Git Bash, WSL, macOS and Linux. A Makefile adds a `make` dependency (not present on stock Windows) for no benefit with one task; Python would duplicate the AWS CLI via boto3 and tie the tool to the project's Python env.
- **AWS CLI, not boto3.** The CLI is already the thing being verified, handles profiles/SSO/regions, and keeps the script runtime-agnostic.
- **Create-or-overwrite via a single `put-parameter --type SecureString --overwrite`.** This avoids a separate "create the registry" step: the first run creates the parameter, so the one-time setup is just `--check` followed by the first upload. Default AWS-managed `aws/ssm` KMS key; no custom key to manage.
- **Pass the value with `--value file://resources/pickem_auth.json`.** Keeps the credential out of the process list and shell history and avoids quoting problems. The script `cd`s to the repo root first so the relative path is valid on Git Bash for Windows.
- **Read only specific keys from `.env`.** Parse `AWS_DEFAULT_REGION` and `AWS_PROFILE` with a small grep/sed rather than `source`-ing the file, so the CBS password is never loaded into the script's environment. Existing environment values win.
- **Missing file: prompt, don't run.** Print `python __main__.py --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark`, wait on Enter (read from the terminal), re-check. The Pickem fetch stays on, which is what triggers the browser login and writes the file. Without a TTY, fail with the same instruction.
- **Expiry check uses the file's own `expires_at`.** The auth file already records the earliest cookie expiry as an ISO-8601 timestamp (see `pickem-session-fetch`, "Auth file contents"). Extract it with grep/sed (no `jq`) and compare to now with GNU `date -d` (available in Git Bash and Linux; on macOS fall back to skipping the check). The app's own browser fallback re-logs in when the saved session has expired, so the same three-fetcher-off command regenerates it.
- **One shared "regenerate" prompt for missing and expired.** Missing offers: regenerate-and-continue. Expired offers: `[r]egenerate / [u]pload anyway / [a]bort`, defaulting to abort on bare Enter so a stale upload is always deliberate. After regenerating, the file is re-read and re-checked, so a still-expired result re-prompts. Without a TTY, an expired file fails closed rather than uploading.
- **Preflight:** `aws --version`, then `aws sts get-caller-identity` (credentials), then `aws ssm describe-parameters --max-results 1` (SSM reachable/authorised), each with a distinct error message. `--check` stops after these and prints account and region.
- **Fail fast:** `set -euo pipefail`; the success message prints parameter name, region and returned version only.

## Risks / Trade-offs

- [Expired file uploaded on purpose or by habit] → Default answer is abort and non-interactive runs fail closed. The check trusts `expires_at`; a session CBS revoked early is not detected.
- [`date -d` unavailable (BSD/macOS)] → Skip the expiry check with a one-line notice rather than failing.
- [Git Bash path conversion mangling `/pickemplug/pickem-auth` into a Windows path] → Set `MSYS_NO_PATHCONV=1` for the AWS calls and verify on Git Bash during implementation.
- [IAM user lacks `ssm:PutParameter`] → The preflight only proves read-level SSM access; a write denial surfaces from `put-parameter` and the script prints that error unchanged.
- [Default `aws/ssm` key] → The Lambda role needs only `ssm:GetParameter`; revisit if a customer-managed key is adopted later.
