#!/usr/bin/env bash
# Build the Lambda package: Linux wheels for the runtime/architecture in deploy/lambda.json,
# [packages] only, plus the app modules from src/. Local only; makes no AWS calls.
#
#   bash scripts/build-lambda.sh
#
# Environment: LAMBDA_CONFIG (default deploy/lambda.json), PYTHON (default python),
# LAMBDA_RUN_DIR (set by deploy-lambda.sh to reuse its run directory).
set -euo pipefail

export MSYS_NO_PATHCONV=1
# pipenv would otherwise load .env (CBS credentials) into the processes it starts.
export PIPENV_DONT_LOAD_ENV=1

cd "$(dirname "${BASH_SOURCE[0]}")/.."

CONFIG=${LAMBDA_CONFIG:-deploy/lambda.json}
PYTHON=${PYTHON:-python}
HELPER=scripts/lambda_build.py
SRC_DIR=${SRC_DIR:-src}
# Modules left out of the package. src/tests is never copied: only src/*.py files are.
EXCLUDE=(__main__.py selenium_pa.py)

die() { echo "Error: $*" >&2; exit 1; }

case "${1:-}" in
  -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  '') ;;
  *) die "Unknown argument: $1 (see --help)" ;;
esac

# Sets CFG_<key> for each line the helper prints.
load_config() {
  local out key value
  out=$("$PYTHON" "$HELPER" config "$CONFIG") || exit 1
  while IFS='=' read -r key value; do
    printf -v "CFG_$key" '%s' "$value"
  done <<< "$out"
}

load_config

GIT_SHA=$(git rev-parse --short HEAD)
DIRTY_FLAG=()
if [ -n "$(git status --porcelain)" ]; then
  GIT_SHA="$GIT_SHA-dirty"
  DIRTY_FLAG=(--dirty)
fi

RUN_DIR=${LAMBDA_RUN_DIR:-}
if [ -z "$RUN_DIR" ]; then
  mkdir -p build
  RUN_DIR="build/$(date -u +%Y%m%dT%H%M%SZ)-$GIT_SHA"
  mkdir "$RUN_DIR"
  # When run by deploy-lambda.sh, its own run.log already captures this output.
  exec > >(tee -a "$RUN_DIR/run.log") 2>&1
fi
PKG_DIR="$RUN_DIR/pkg"
[ -e "$PKG_DIR" ] && die "$PKG_DIR already exists"

echo "Building for $CFG_runtime on $CFG_architecture ($CFG_platform) into $RUN_DIR"

pipenv requirements --hash > "$RUN_DIR/requirements.txt" \
  || die "pipenv requirements failed; is Pipfile.lock up to date?"

# --only-binary makes a missing Linux wheel a hard error instead of a source build.
"$PYTHON" -m pip install -r "$RUN_DIR/requirements.txt" --require-hashes --no-deps \
  --target "$PKG_DIR" --platform "$CFG_platform" --python-version "$CFG_python_version" \
  --implementation cp --only-binary=:all: --no-compile --disable-pip-version-check --quiet \
  || die "pip could not install the locked packages as $CFG_platform wheels for Python $CFG_python_version (see the package named above)"

[ -d "$SRC_DIR" ] || die "$SRC_DIR directory not found"
copied=0
for path in "$SRC_DIR"/*.py; do
  [ -e "$path" ] || continue
  file=$(basename "$path")
  skip=0
  for excluded in "${EXCLUDE[@]}"; do
    [ "$file" = "$excluded" ] && skip=1
  done
  if [ "$skip" -eq 0 ]; then
    cp "$path" "$PKG_DIR/"
    copied=$((copied + 1))
  fi
done
[ "$copied" -gt 0 ] || die "no app modules found in $SRC_DIR/"

"$PYTHON" "$HELPER" package "$RUN_DIR" --git-sha "$GIT_SHA" "${DIRTY_FLAG[@]}"

echo "$RUN_DIR"
