"""Helpers for scripts/build-lambda.sh and scripts/deploy-lambda.sh. Standard library only.

  python scripts/lambda_build.py config <config.json>       validate; print KEY=value lines
  python scripts/lambda_build.py env-json <config.json>     print the Environment argument for the AWS CLI
  python scripts/lambda_build.py package <run_dir> --git-sha SHA [--dirty]
                                                            zip <run_dir>/pkg, write manifest.json
  python scripts/lambda_build.py get <file.json> <key>      print one top-level value
  python scripts/lambda_build.py schedule <schedule.json> <config.json>
                                                            validate the trigger config; print function_name=, region=,
                                                            then name<TAB>expression<TAB>enabled per schedule
  python scripts/lambda_build.py event-json <schedule.json> <name>
                                                            print one schedule's event payload
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from importlib import metadata

PLATFORMS = {'x86_64': 'manylinux2014_x86_64', 'arm64': 'manylinux2014_aarch64'}
DENIED_ENV_KEYS = {'PICKEM_EMAIL', 'PICKEM_PASSWORD'}
DENIED_ENV_WORDS = ('AUTH', 'SESSION', 'PASSWORD', 'SECRET', 'TOKEN')
FIELDS = {
    'function_name': (str, r'[A-Za-z0-9_-]+'),
    'region': (str, r'[a-z]{2}(-[a-z]+)+-\d'),
    'runtime': (str, r'python3\.\d+'),
    'architecture': (str, None),
    'handler': (str, r'[A-Za-z0-9_.]+'),
    'timeout': (int, None),
    'memory_size': (int, None),
    'environment': (dict, None),
}
EVENT_KEYS = ('fetch_pickem', 'fetch_draftkings', 'fetch_espnbet', 'fetch_oddshark')
SCHEDULE_FIELDS = ('name', 'schedule', 'enabled', 'event')
KIND_NAMES = {str: 'a string', int: 'an integer', dict: 'an object'}


class ConfigError(Exception):
    pass


def load_config(path):
    """The validated deploy config. Raises ConfigError naming the offending key."""
    try:
        with open(path, encoding='utf-8') as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError) as err:
        raise ConfigError(f'cannot read {path}: {err}') from None
    if not isinstance(config, dict):
        raise ConfigError(f'{path} must hold a JSON object')

    unknown = sorted(set(config) - set(FIELDS))
    if unknown:
        raise ConfigError(f'unknown key(s): {", ".join(unknown)}')
    for key, (kind, pattern) in FIELDS.items():
        if key not in config:
            raise ConfigError(f'missing key: {key}')
        value = config[key]
        # bool is a subclass of int; reject it explicitly.
        if not isinstance(value, kind) or isinstance(value, bool):
            raise ConfigError(f'{key} must be {KIND_NAMES[kind]}')
        if pattern and not re.fullmatch(pattern, value):
            raise ConfigError(f'{key} has an invalid value: {value!r}')

    if config['architecture'] not in PLATFORMS:
        raise ConfigError(f'architecture must be one of {", ".join(PLATFORMS)}; got {config["architecture"]!r}')
    if not 1 <= config['timeout'] <= 900:
        raise ConfigError('timeout must be between 1 and 900 seconds')
    if not 128 <= config['memory_size'] <= 10240:
        raise ConfigError('memory_size must be between 128 and 10240 MB')

    for name, value in config['environment'].items():
        upper = name.upper()
        if upper in DENIED_ENV_KEYS or any(word in upper for word in DENIED_ENV_WORDS):
            raise ConfigError(f'environment variable {name} looks like a credential or session; '
                              'secrets must never be in the deploy config')
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            raise ConfigError(f'environment variable name is invalid: {name!r}')
        if not isinstance(value, str) or not value:
            raise ConfigError(f'environment variable {name} must be a non-empty string')
    return config


def load_schedule(path):
    """The validated list of trigger schedules. Raises ConfigError naming the offending schedule and key."""
    try:
        with open(path, encoding='utf-8') as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError) as err:
        raise ConfigError(f'cannot read {path}: {err}') from None
    if not isinstance(config, dict) or set(config) != {'schedules'}:
        raise ConfigError(f'{path} must be an object with a single "schedules" key')
    schedules = config['schedules']
    if not isinstance(schedules, list) or not schedules:
        raise ConfigError('schedules must be a non-empty list')

    seen = set()
    for index, entry in enumerate(schedules, 1):
        if not isinstance(entry, dict):
            raise ConfigError(f'schedule #{index} must be an object')
        label = entry.get('name', f'#{index}')
        unknown = sorted(set(entry) - set(SCHEDULE_FIELDS) - {'note'})
        if unknown:
            raise ConfigError(f'schedule {label}: unknown key(s): {", ".join(unknown)}')
        for key in SCHEDULE_FIELDS:
            if key not in entry:
                raise ConfigError(f'schedule {label}: missing key: {key}')

        name = entry['name']
        if not isinstance(name, str) or not re.fullmatch(r'pickem-[A-Za-z0-9._-]{1,57}', name):
            raise ConfigError(f'schedule {label}: name must be "pickem-" plus letters, digits, . _ -; got {name!r}')
        if name in seen:
            raise ConfigError(f'schedule {name}: duplicate name')
        seen.add(name)
        expression = entry['schedule']
        if not isinstance(expression, str) or not re.fullmatch(r'(cron|rate)\(.+\)', expression):
            raise ConfigError(f'schedule {name}: schedule must be a cron(...) or rate(...) expression; got {expression!r}')
        if not isinstance(entry['enabled'], bool):
            raise ConfigError(f'schedule {name}: enabled must be true or false')
        if 'note' in entry and not isinstance(entry['note'], str):
            raise ConfigError(f'schedule {name}: note must be a string')
        if not isinstance(entry['event'], dict):
            raise ConfigError(f'schedule {name}: event must be an object')
        for key, value in entry['event'].items():
            upper = key.upper()
            if upper in DENIED_ENV_KEYS or any(word in upper for word in DENIED_ENV_WORDS):
                raise ConfigError(f'schedule {name}: event key {key} looks like a credential or session; '
                                  'secrets must never be in the schedule config')
            if key not in EVENT_KEYS:
                raise ConfigError(f'schedule {name}: event key {key!r} is not one of {", ".join(EVENT_KEYS)}')
            if not isinstance(value, bool):
                raise ConfigError(f'schedule {name}: event key {key} must be true or false')
    return schedules


def derived(config):
    return {
        'platform': PLATFORMS[config['architecture']],
        'python_version': config['runtime'][len('python'):],
    }


def cmd_config(args):
    config = load_config(args.config)
    values = {k: v for k, v in config.items() if k != 'environment'}
    values.update(derived(config))
    for key, value in values.items():
        print(f'{key}={value}')


def cmd_schedule(args):
    """function_name= and region= lines, then one tab-separated line per schedule: name, expression, enabled."""
    deploy = load_config(args.config)
    print(f'function_name={deploy["function_name"]}')
    print(f'region={deploy["region"]}')
    for entry in load_schedule(args.schedule):
        print(f'{entry["name"]}	{entry["schedule"]}	{"true" if entry["enabled"] else "false"}')


def cmd_event_json(args):
    for entry in load_schedule(args.schedule):
        if entry['name'] == args.name:
            print(json.dumps(entry['event']))
            return
    raise ConfigError(f'no schedule named {args.name}')


def cmd_env_json(args):
    print(json.dumps({'Variables': load_config(args.config)['environment']}))


def package_files(pkg_dir):
    """Relative paths under pkg_dir in a stable order, skipping bytecode caches."""
    paths = []
    for root, dirs, files in os.walk(pkg_dir):
        dirs[:] = sorted(d for d in dirs if d != '__pycache__')
        for name in sorted(files):
            if not name.endswith('.pyc'):
                full = os.path.join(root, name)
                paths.append(os.path.relpath(full, pkg_dir).replace(os.sep, '/'))
    return paths


def cmd_package(args):
    pkg_dir = os.path.join(args.run_dir, 'pkg')
    zip_path = os.path.join(args.run_dir, 'package.zip')
    paths = package_files(pkg_dir)

    windows = [p for p in paths if p.lower().endswith('.pyd') or 'win_amd64' in p.lower()]
    if windows:
        raise SystemExit('Error: package contains Windows binaries, refusing to write it:\n  '
                         + '\n  '.join(windows))

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for rel in paths:
            archive.write(os.path.join(pkg_dir, rel), rel)

    with open(zip_path, 'rb') as file:
        digest = hashlib.sha256(file.read()).digest()
    packages = sorted(
        ({'name': dist.metadata['Name'], 'version': dist.version}
         for dist in metadata.distributions(path=[pkg_dir])),
        key=lambda item: item['name'].lower())
    manifest = {
        'git_sha': args.git_sha,
        'dirty': args.dirty,
        'built_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'zip_sha256': digest.hex(),
        # Lambda reports CodeSha256 as base64; publish-version --code-sha256 compares against it.
        'code_sha256': base64.b64encode(digest).decode('ascii'),
        'zip_bytes': os.path.getsize(zip_path),
        'files': len(paths),
        'packages': packages,
    }
    with open(os.path.join(args.run_dir, 'manifest.json'), 'w', encoding='utf-8') as file:
        json.dump(manifest, file, indent=2)
        file.write('\n')
    print(f'Wrote {zip_path} ({len(paths)} files, {manifest["zip_bytes"]} bytes, sha256 {digest.hex()})')


def cmd_get(args):
    with open(args.file, encoding='utf-8') as file:
        print(json.load(file)[args.key])


def main():
    # Bash reads this output; keep Windows from adding \r.
    sys.stdout.reconfigure(newline='\n')
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)

    config = commands.add_parser('config')
    config.add_argument('config')
    config.set_defaults(func=cmd_config)

    env_json = commands.add_parser('env-json')
    env_json.add_argument('config')
    env_json.set_defaults(func=cmd_env_json)

    package = commands.add_parser('package')
    package.add_argument('run_dir')
    package.add_argument('--git-sha', required=True)
    package.add_argument('--dirty', action='store_true')
    package.set_defaults(func=cmd_package)

    schedule = commands.add_parser('schedule')
    schedule.add_argument('schedule')
    schedule.add_argument('config')
    schedule.set_defaults(func=cmd_schedule)

    event_json = commands.add_parser('event-json')
    event_json.add_argument('schedule')
    event_json.add_argument('name')
    event_json.set_defaults(func=cmd_event_json)

    get = commands.add_parser('get')
    get.add_argument('file')
    get.add_argument('key')
    get.set_defaults(func=cmd_get)

    args = parser.parse_args()
    try:
        args.func(args)
    except ConfigError as err:
        raise SystemExit(f'Error: config: {err}') from None


if __name__ == '__main__':
    main()
