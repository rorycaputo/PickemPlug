#!/usr/bin/env bash
# Build and deploy the pickem Lambda. Local, operator-run only.
#
#   bash scripts/deploy-lambda.sh [--allow-dirty] [--skip-auth-upload] [--no-invoke]
#
# Stages: preflight -> test -> build -> auth upload -> deploy (code + config + publish version)
#         -> smoke invoke -> point the live alias at the new version.
#
#   --allow-dirty        deploy with uncommitted changes (recorded as <sha>-dirty)
#   --skip-auth-upload   don't run scripts/upload-pickem-auth.sh
#   --no-invoke          skip the smoke invoke; the live alias is then not moved
#
# The function's settings come from deploy/lambda.json (override with LAMBDA_CONFIG).
# Each run's zip, manifest and log are kept in build/<timestamp>-<sha>/; build/deploys.log
# gets one line per run.
set -euo pipefail

export MSYS_NO_PATHCONV=1
# pipenv would otherwise load .env (CBS credentials) into the processes it starts.
export PIPENV_DONT_LOAD_ENV=1

cd "$(dirname "${BASH_SOURCE[0]}")/.."

CONFIG=${LAMBDA_CONFIG:-deploy/lambda.json}
PYTHON=${PYTHON:-python}
HELPER=scripts/lambda_build.py
DEPLOY_LOG=build/deploys.log
ALIAS=live

die() { echo "Error: $*" >&2; exit 1; }

usage() { sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; }

ALLOW_DIRTY=0
SKIP_AUTH=0
NO_INVOKE=0
for arg in "$@"; do
  case "$arg" in
    --allow-dirty) ALLOW_DIRTY=1 ;;
    --skip-auth-upload) SKIP_AUTH=1 ;;
    --no-invoke) NO_INVOKE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $arg (see --help)" ;;
  esac
done

# Same reading of .env as upload-pickem-auth.sh: only the AWS settings, never sourced.
load_env_var() {
  local name=$1 value
  [ -n "${!name:-}" ] && return 0
  [ -f .env ] || return 0
  value=$(grep -E "^[[:space:]]*(export[[:space:]]+)?${name}=" .env | tail -n 1 \
    | sed -E "s/^[^=]*=//; s/\r$//; s/^[\"']//; s/[\"']$//") || true
  [ -n "$value" ] && export "$name=$value"
  return 0
}

GIT_SHA=$(git rev-parse --short HEAD)
[ -n "$(git status --porcelain)" ] && GIT_SHA="$GIT_SHA-dirty"
mkdir -p build
RUN_DIR="build/$(date -u +%Y%m%dT%H%M%SZ)-$GIT_SHA"
mkdir "$RUN_DIR"
exec > >(tee -a "$RUN_DIR/run.log") 2>&1

STAGE=config
VERSION=-
on_exit() {
  local status=$? result=ok
  [ "$status" -ne 0 ] && result="failed:$STAGE"
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$GIT_SHA" "$VERSION" "$result" >> "$DEPLOY_LOG"
  if [ "$status" -ne 0 ]; then
    echo "Deploy FAILED at stage '$STAGE'. Log: $RUN_DIR/run.log"
  else
    echo "Deploy OK: version $VERSION. Log: $RUN_DIR/run.log"
  fi
}
trap on_exit EXIT

stage() {
  STAGE=$1
  shift
  echo
  echo "==> $STAGE"
  "$@"
}

# Sets CFG_<key> for each line the helper prints; validation (including the secret deny list)
# happens here, before any AWS call.
load_config() {
  local out key value
  out=$("$PYTHON" "$HELPER" config "$CONFIG") || exit 1
  while IFS='=' read -r key value; do
    printf -v "CFG_$key" '%s' "$value"
  done <<< "$out"
  echo "Config $CONFIG: $CFG_function_name in $CFG_region ($CFG_runtime, $CFG_architecture)"
}

lambda() { aws lambda "$@" --region "$CFG_region"; }

preflight() {
  command -v aws >/dev/null 2>&1 || die "AWS CLI not found. Install AWS CLI v2 and re-run."

  local out
  out=$(aws sts get-caller-identity --query Account --output text 2>&1) \
    || die "AWS credentials check failed (sts get-caller-identity):
$out"
  echo "AWS account $out"

  out=$(lambda get-function --function-name "$CFG_function_name" \
    --query Configuration.FunctionArn --output text 2>&1) \
    || die "function $CFG_function_name not found or not readable in $CFG_region (lambda get-function):
$out"
  echo "Function $out"

  if [ -n "$(git status --porcelain)" ]; then
    [ "$ALLOW_DIRTY" -eq 1 ] || die "the git working tree has uncommitted changes; commit them or pass --allow-dirty"
    echo "Working tree is dirty (--allow-dirty); recording $GIT_SHA"
  fi

  if [ "$SKIP_AUTH" -eq 0 ]; then
    AWS_DEFAULT_REGION=$CFG_region bash scripts/upload-pickem-auth.sh --check
  fi
}

run_tests() {
  pipenv run python -m unittest discover tests
}

build() {
  LAMBDA_RUN_DIR=$RUN_DIR LAMBDA_CONFIG=$CONFIG bash scripts/build-lambda.sh
}

auth_upload() {
  if [ "$SKIP_AUTH" -eq 1 ]; then
    echo "Skipped (--skip-auth-upload)"
    return 0
  fi
  AWS_DEFAULT_REGION=$CFG_region bash scripts/upload-pickem-auth.sh
}

deploy() {
  local code_sha description
  code_sha=$("$PYTHON" "$HELPER" get "$RUN_DIR/manifest.json" code_sha256)

  echo "Updating code ($CFG_architecture)"
  lambda update-function-code --function-name "$CFG_function_name" \
    --zip-file "fileb://$RUN_DIR/package.zip" --architectures "$CFG_architecture" \
    --query LastUpdateStatus --output text
  lambda wait function-updated --function-name "$CFG_function_name"

  echo "Updating configuration"
  "$PYTHON" "$HELPER" env-json "$CONFIG" > "$RUN_DIR/environment.json"
  lambda update-function-configuration --function-name "$CFG_function_name" \
    --handler "$CFG_handler" --runtime "$CFG_runtime" --timeout "$CFG_timeout" \
    --memory-size "$CFG_memory_size" --environment "file://$RUN_DIR/environment.json" \
    --query LastUpdateStatus --output text
  lambda wait function-updated --function-name "$CFG_function_name"

  description="$GIT_SHA: $(git log -1 --format=%s)"
  # --code-sha256 makes publishing fail if $LATEST no longer holds the code uploaded above.
  VERSION=$(lambda publish-version --function-name "$CFG_function_name" \
    --code-sha256 "$code_sha" --description "${description:0:256}" \
    --query Version --output text)
  echo "Published version $VERSION"
}

smoke() {
  if [ "$NO_INVOKE" -eq 1 ]; then
    echo "Skipped (--no-invoke)"
    return 0
  fi
  local event="$RUN_DIR/smoke-event.json" response="$RUN_DIR/smoke-response.json" error
  printf '%s\n' '{"fetch_pickem": false, "fetch_draftkings": false, "fetch_espnbet": false, "fetch_oddshark": false}' > "$event"

  # The read timeout must outlast the function, or the CLI would retry and invoke it again.
  error=$(lambda invoke --function-name "$CFG_function_name" --qualifier "$VERSION" \
    --cli-binary-format raw-in-base64-out --payload "file://$event" \
    --cli-read-timeout "$((CFG_timeout + 30))" \
    --query FunctionError --output text "$response")
  if [ "$error" != "None" ]; then
    echo "Response:"
    cat "$response"
    echo
    die "smoke invoke of version $VERSION failed ($error)"
  fi
  echo "Smoke invoke passed: $(cat "$response")"
}

point_alias() {
  if [ "$NO_INVOKE" -eq 1 ]; then
    echo "$ALIAS not moved: version $VERSION was not smoke-tested (--no-invoke)"
    return 0
  fi
  local out
  if out=$(lambda get-alias --function-name "$CFG_function_name" --name "$ALIAS" \
      --query FunctionVersion --output text 2>&1); then
    lambda update-alias --function-name "$CFG_function_name" --name "$ALIAS" \
      --function-version "$VERSION" --query AliasArn --output text >/dev/null
    echo "$ALIAS: version $out -> $VERSION"
  elif [[ "$out" == *ResourceNotFoundException* ]]; then
    lambda create-alias --function-name "$CFG_function_name" --name "$ALIAS" \
      --function-version "$VERSION" --query AliasArn --output text >/dev/null
    echo "$ALIAS: created -> $VERSION"
  else
    die "could not read alias $ALIAS:
$out"
  fi
}

load_env_var AWS_PROFILE

stage config load_config
stage preflight preflight
stage test run_tests
stage build build
stage auth-upload auth_upload
stage deploy deploy
stage smoke smoke
stage alias point_alias
