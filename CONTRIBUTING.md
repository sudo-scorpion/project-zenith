# Contributing to Project Zenith

## Dev Setup

```bash
git clone https://github.com/project-zenith/project-zenith
cd project-zenith
pip install -e .
```

## Running Tests

```bash
bash tests/smoke/router.sh          # quick sanity check (~5s)
bash tests/integration/lifecycle.sh # full install/rollback/cleanup flow
bash tests/integration/package_install.sh
```

## Compile Check

```bash
python -m py_compile src/zenith/*.py bin/zen
```

## Architecture

See [CLAUDE.md](CLAUDE.md) for module roles, design constraints, and key conventions.

## Pull Requests

- Keep PRs focused — one concern per PR
- Tests are shell scripts in `tests/`, not pytest — add or update as needed
- No external Python dependencies — the zero-dep rule is intentional
- No hardcoded `sudo` in Python code — system package installs only happen when the user explicitly passes `--packages`
- Use `raise SystemExit(message)` for fatal errors, not `sys.exit()`
- Log via `logging_utils` (`info`, `ok`, `warn`, `fail`, `note`) — not `print()`

## Reporting Issues

Open a GitHub issue with:
- Your OS and distro version
- Output of `zen doctor`
- The exact command that failed and its full output
