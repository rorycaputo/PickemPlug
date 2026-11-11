# Tasks

## 1. Script

- [x] 1.1 Create `scripts/upload-pickem-auth.sh` with strict mode, repo-root `cd`, `MSYS_NO_PATHCONV=1`, and `.env` parsing of only `AWS_DEFAULT_REGION` / `AWS_PROFILE` (environment wins). Verify: with a `.env` containing the region and a dummy `PICKEM_PASSWORD`, the script picks up the region and the password never appears in `bash -x` output or stdout.
- [x] 1.2 Add preflight checks (AWS CLI present, `sts get-caller-identity`, `ssm describe-parameters`) and the `--check` flag. Verify: `bash scripts/upload-pickem-auth.sh --check` prints account and region and exits 0; with `AWS_PROFILE=nonexistent` it exits non-zero naming the failed check.
- [ ] 1.3 Add the missing-file flow (print the three-fetcher-off command, wait for Enter, re-check, error if still missing, fail fast without a TTY). Verify: with `resources/pickem_auth.json` temporarily moved aside, running with stdin from `/dev/null` exits non-zero with the command; running interactively and restoring the file before pressing Enter continues.
- [ ] 1.4 Add the expiry check: read `expires_at`, and when it is past, warn and prompt `[r]egenerate / [u]pload anyway / [a]bort` (default abort), reusing the missing-file regenerate flow and re-checking after it; fail closed without a TTY. Verify: with a copy of the auth file whose `expires_at` is set to a past date, each of r, u and a behaves as specified (a and non-interactive exit non-zero without calling SSM); with the real file (expires 2026-12-10) no prompt appears.
- [x] 1.5 Add the upload via `put-parameter --type SecureString --overwrite --value file://...` and the success message (name, region, version, no values). Verify: the first run creates `/pickemplug/pickem-auth`; `aws ssm get-parameter --name /pickemplug/pickem-auth --with-decryption --query Parameter.Value --output text` matches the local file (compare hashes, do not print it); a second run bumps the version.

## 2. Documentation

- [x] 2.1 Update `README.md`: replace the "copy that file's contents into the parameter by hand" note with the script, and add the one-time setup (`--check`, then the first upload creates the parameter) and the refresh routine, including the expired-session prompt. Verify: the documented commands run as written.
- [x] 2.2 Add a `.env.example` note that `AWS_DEFAULT_REGION` / `AWS_PROFILE` are used by the upload script. Verify: the file still lists `PICKEM_EMAIL` / `PICKEM_PASSWORD` and the script's `.env` parsing handles it.
