#!/usr/bin/env bash
# Invoke the pickem Lambda from a local machine and print its log tail and response.
#
#   bash scripts/invoke-lambda.sh [--qualifier Q] [--no-fetch-pickem] [--no-fetch-draftkings]
#                                 [--no-fetch-espnbet] [--no-fetch-oddshark]
#
#   --qualifier Q        alias or version to invoke (default: live)
#   --no-fetch-<source>  send fetch_<source>: false in the event; every fetch defaults to on
#
# Waits for the run to finish, prints the last 4 KB of its log, then the function's response.
# Exits non-zero if the function returned an error. Function name, region and timeout come from
# deploy/lambda.json (override with LAMBDA_CONFIG). Nothing is written to the working directory.
set -euo pipefail

export MSYS_NO_PATHCONV=1

cd "$(dirname "${BASH_SOURCE[0]}")/.."

CONFIG=${LAMBDA_CONFIG:-deploy/lambda.json}
PYTHON=${PYTHON:-python}
HELPER=scripts/lambda_build.py
QUALIFIER=live

die() { echo "Error: $*" >&2; exit 1; }

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; }

FLAGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --qualifier) [ $# -ge 2 ] || die "--qualifier needs a value"; QUALIFIER=$2; shift ;;
    --no-fetch-pickem|--no-fetch-draftkings|--no-fetch-espnbet|--no-fetch-oddshark)
      FLAGS+=("\"fetch_${1#--no-fetch-}\": false") ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $1 (see --help)" ;;
  esac
  shift
done

# Same reading of .env as the other scripts: only the AWS settings, never sourced.
load_env_var() {
  local name=$1 value
  [ -n "${!name:-}" ] && return 0
  [ -f .env ] || return 0
  value=$(grep -E "^[[:space:]]*(export[[:space:]]+)?${name}=" .env | tail -n 1 \
    | sed -E "s/^[^=]*=//; s/\r$//; s/^[\"']//; s/[\"']$//") || true
  [ -n "$value" ] && export "$name=$value"
  return 0
}
load_env_var AWS_PROFILE

command -v aws >/dev/null 2>&1 || die "AWS CLI not found. Install AWS CLI v2 and re-run."

config=$("$PYTHON" "$HELPER" config "$CONFIG") || exit 1
while IFS= read -r line; do
  line=${line%$'\r'}
  case "$line" in
    function_name=*) CFG_function_name=${line#*=} ;;
    region=*) CFG_region=${line#*=} ;;
    timeout=*) CFG_timeout=${line#*=} ;;
  esac
done <<< "$config"

payload="{$(IFS=,; echo "${FLAGS[*]:-}")}"

# The CLI requires an output file; use a temp one and always remove it.
response=$(mktemp)
trap 'rm -f "$response"' EXIT
# Path conversion is off, so hand the Windows AWS CLI a Windows path to the temp file.
response_arg=$response
command -v cygpath >/dev/null 2>&1 && response_arg=$(cygpath -w "$response")

echo "Invoking $CFG_function_name:$QUALIFIER ($CFG_region) with $payload"

# The read timeout must outlast the function, or the CLI would retry and invoke it again.
# The Windows AWS CLI ends text output with CRLF; strip the CR before splitting and decoding.
result=$(aws lambda invoke --function-name "$CFG_function_name" --qualifier "$QUALIFIER" \
  --region "$CFG_region" \
  --cli-binary-format raw-in-base64-out --payload "$payload" \
  --cli-read-timeout "$((CFG_timeout + 30))" \
  --log-type Tail --query '[FunctionError, LogResult]' --output text \
  "$response_arg" | tr -d '\r')
IFS=$'\t' read -r function_error log_result <<< "$result"

echo "--- log ---"
printf '%s' "$log_result" | base64 -d
echo "--- response ---"
cat "$response"
echo

[ "$function_error" = "None" ] || die "function returned an error ($function_error)"
