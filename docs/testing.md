# Testing

Zenith ships three verification layers and a CI workflow.

## Smoke

```bash
bash tests/smoke/router.sh
```

Smoke coverage verifies:

- command routing
- config validation
- JSON status and doctor output
- dry-run installs staying side-effect free
- `install all` skipping surface cleanly in container mode

## Integration

```bash
bash tests/integration/lifecycle.sh
```

Integration coverage verifies:

- personal profile alias overrides
- bash and zsh shell fragment installation paths
- manifest creation
- rollback restoring a pre-existing shell rc file
- uninstall removing Zenith-managed state when a shell rc file did not exist before install
- `fix` context file parsing
- zsh history fallback for `fix`
- `install all --mode container` leaving the surface layer uninstalled

## Packaged install

```bash
bash tests/integration/package_install.sh
```

Packaged-install coverage verifies:

- `pip install .` produces a working `zen` entrypoint
- bundled prompts and config assets are available outside editable mode
- core install, manifest creation, and rollback still work from a packaged install

## CI

GitHub Actions runs compile checks plus the smoke, integration, and packaged-install verification flows on every push and pull request.
