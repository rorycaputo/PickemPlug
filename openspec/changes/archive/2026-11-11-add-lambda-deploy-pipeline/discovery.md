# Discovery: Lambda deploy pipeline

> Verbatim transcript of the explore session's design discussion (2026-11-11), saved for reference. It is the thinking behind `proposal.md`, not a spec.
>
> **Superseded since this was written:** the project is now on Python 3.14 (not 3.10, and `--python-version 3.10` below should read 3.14); the Lambda runtime is python3.14 in us-east-2; the build is folded into this change rather than being a separate prerequisite; and the config question at the end was answered "code + config".

I looked at the repo and ran a few read-only checks against your `pickem` Lambda. The Lambda turned up some things that affect the pipeline design, so I'll start there.

## What's deployed today

```
aws lambda get-function-configuration --function-name pickem

  Runtime   python3.10      Arch     x86_64
  Handler   lambda_function.main     <-- stale, code now exposes lambda_handler
  Memory    128 MB          Timeout  3 s     <-- Pickem fetch alone can take ~50 s
  Env vars  (none)                   <-- no PICKEM_STORAGE / PICKEM_BUCKET
  Versions  $LATEST only    Aliases  none
  CodeSize  5,082,574       ~= your Oct 7 package.zip (Windows lxml .pyd inside)
```

Even a perfect code upload would fail on the first invocation. It would hit the wrong handler, then the 3 s timeout, then local storage mode on a read-only filesystem. So the first design question is whether the pipeline only ships code, or also enforces the function's configuration. More on that below.

Other things the repo shows:
- `package.zip` is untracked and not gitignored. It also contains things the Lambda doesn't need, like `attr/`, `_distutils_hack` and an old 13 KB `__main__.py`, which suggests dev and venv packages got in.
- `lxml` and `brotli` are compiled packages. A zip built on Windows breaks on Lambda (issue #4 in LAMBDA_DISCOVERY), so the build has to fetch **Linux x86_64 wheels**.
- `boto3` is in dev packages, which is right because the Lambda runtime already provides it. The build should install only `[packages]`.
- **python3.10:** CPython 3.10 reached end of life in Oct 2026. Lambda deprecates runtimes on its own schedule, so check the current date for 3.10 before you build a pipeline around it. Moving to 3.12 or 3.13 would mean bumping `Pipfile [requires]` and the build's `--python-version` together.

## The pipeline

```
  deploy.sh  [--skip-auth-upload] [--skip-tests] [--no-invoke] ...
     |
     v
 +-----------+   +-----------+   +----------------+   +-----------+   +-----------+
 | preflight |-->|   test    |-->|     build      |-->| auth push |-->|  deploy   |
 | git clean?|   | unittest  |   | Linux wheels   |   | (optional)|   | code +    |
 | aws creds |   | discover  |   | + app *.py     |   | upload-   |   | publish   |
 | fn exists |   |           |   | -> build/<id>/ |   | pickem-   |   | version   |
 +-----------+   +-----------+   |    pickem.zip  |   | auth.sh   |   +-----+-----+
                                 +----------------+   +-----------+         |
                                                                            v
                                                                    +---------------+
                                                                    | smoke invoke  |
                                                                    | (optional)    |
                                                                    +---------------+
```

The build step can stay plain bash with no Docker:

```
pipenv requirements > build/requirements.txt          # [packages] only
pip install -r build/requirements.txt -t build/pkg \
    --platform manylinux2014_x86_64 --only-binary=:all: \
    --python-version 3.10 --implementation cp
cp *.py build/pkg/     # app modules only: no tests/, resources/, .env, selenium_pa?
```

`selenium_pa.py` can go in the zip safely because the import is lazy. Leaving it out would also prove that Lambda never needs it.

**The auth step:** the script you just wrote already works well in a pipeline. It prompts when it has a terminal and fails with a clear message when it doesn't. A `--skip-auth-upload` flag is enough for the disable option. I'd also consider running its `--check` in preflight, so a missing AWS permission fails before you spend time on tests and the build. One caveat: if the session has expired, the script stops and waits for you to run a browser login in another terminal. That's fine for a script you run by hand, and a problem for anything headless (including Jenkins).

## Tracking old builds: two layers

This splits cleanly, and the AWS side costs nothing:

```
  LOCAL  (what was built)                 AWS  (what was deployed)
  build/                                  Lambda versions (immutable)
    20261111-1802-34d9fc8/                  v1  "34d9fc8 Pickem auth..."
      pickem.zip                            v2  "a1b2c3d S3 storage..."
      manifest.json  (sha, sha256,          v3  "..."   <-- alias "live"
                      pip freeze, ts)
      pipeline.log   (tee of the run)     rollback = point "live" at v2
    20261112-0930-a1b2c3d/                  (one CLI call, no rebuild)
  deploys.log  (1 line per run:
                ts | sha | ver | ok/fail)
```

- `aws lambda publish-version --description "<sha> <subject>"` gives every deploy a permanent, numbered version that you can roll back to.
- An alias (say `live`) only matters if the scheduler targets the alias rather than `$LATEST`. I couldn't see your triggers because your IAM user lacks `events:` and `scheduler:` list permissions, which suggests the cron doesn't exist yet. If so, the scheduler can target `pickem:live` from the start.
- A **dirty-tree guard** (refuse to deploy uncommitted changes unless you pass `--allow-dirty`) makes the sha in each version description trustworthy. Without it, the build history isn't reliable.

## Tool options, from lightest to heaviest

| Option | Tracking | Fit for you |
|---|---|---|
| **bash script + `build/` dir + Lambda versions** | Files you own plus AWS versions | **My recommendation.** Matches your existing script style; nothing to install |
| `make` / `just` wrapping the same steps | Same | Nice for named targets (`just test`, `just deploy`). Mostly cosmetic for one pipeline |
| **AWS SAM** (`sam build --use-container`, `sam deploy`) | CloudFormation stack history | Handles the Linux build and config together, but needs Docker. It also wants to *own* the function, so you'd import or recreate `pickem` into a stack. It manages config well, but it's a bigger step |
| Local Jenkins (Docker) | Full UI, build history, artifacts | Familiar, but a server to keep running for a one-person, one-function project. The interactive auth step fits poorly |
| `act` / GitHub Actions | Actions UI (if pushed) | Only worth it if this repo goes to GitHub, and the credentials in git history need rotating before that |
| CodePipeline / CodeBuild | AWS console | Runs in the cloud, not locally; costs money; overkill here |

`aws lambda update-function-code` is the AWS-native upload. It's one CLI call, then `aws lambda wait function-updated`, then `publish-version`.

## The question that shapes the rest

**Should the pipeline enforce the Lambda's configuration (handler, timeout, memory, env vars), or only ship code?**

- **Code only:** you fix the handler, timeout and env vars once by hand. The pipeline stays small, and the config can drift without anyone noticing.
- **Code + config (I lean this way):** a small checked-in file, e.g. `deploy/lambda-config.json` with handler, timeout, memory, `PICKEM_STORAGE=s3` and `PICKEM_BUCKET`, applied with `update-function-configuration` on every deploy. It's idempotent, and the current broken state can't come back. This touches no S3 setup (only the bucket *name* as an env var) and no credentials, which keeps it within `AGENTS.md`.
- **Hand it all to SAM:** the most robust option, and the most new tooling.

A couple of smaller threads can wait until that's settled:
- Smoke invoke: with all `fetch_*: false` it reads only the S3 caches, so you get a cheap end-to-end check. Live fetches would also answer the open datacenter-IP question (#9).
- Retention: keep the last N `build/` dirs, and delete old Lambda versions or not.

Which way do you want to go on config?
