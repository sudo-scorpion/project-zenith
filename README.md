# Project Zenith

Project Zenith is a modular terminal platform with a reliable `core` layer and an optional `surface` layer. The current release is Python-packaged, container-aware, manifest-backed, and safe to install into user-local XDG paths with rollback and uninstall support.

## Release status

Zenith now ships with:

- packaged CLI entrypoints via `pyproject.toml`
- bundled prompts and config assets for non-editable installs
- `core`, `surface`, `all`, `rollback`, `uninstall`, `doctor`, `status`, `config`, `workspace`, `orbit`, `sync`, `nav`, and `fix`
- bash and zsh shell integration
- container/runtime detection for Docker, Podman, Distrobox, and generic `container` markers
- package-manager automation for `dnf`, `pacman`, `apt`, `zypper`, `apk`, and `brew`, with graceful warnings when packages are unavailable
- smoke, integration, packaged-install verification, and CI coverage

## Quick start

```bash
python3 -m pip install -r requirements.txt
zen version
zen install core --yes
zen doctor --json
zen status --json
bash tests/smoke/router.sh
bash tests/integration/lifecycle.sh
bash tests/integration/package_install.sh
```

## Container support

Zenith is container-aware rather than container-dependent.

- `--mode auto` resolves to `container` when Docker, Podman, Distrobox, or generic `container` markers are present.
- `install all` installs core and skips the surface layer with a warning when host-only requirements are not met.
- mutable state stays under `~/.config/zenith` and `~/.local/share/zenith`
- `zen status` and `zen doctor` report container runtime, Distrobox detection, package-manager detection, shell integration, workspace status, and manifest timestamp

## Docs

- [Install notes](docs/install.md)
- [Command reference](docs/commands.md)
- [Container support](docs/container.md)
- [Profiles](docs/profiles.md)
- [Safety](docs/safety.md)
- [Rollback](docs/rollback.md)
- [Architecture](docs/architecture.md)
- [Testing](docs/testing.md)

## Operational notes

- `surface` still requires host mode plus a GUI session because it manages local terminal and shader assets
- `nav` and `fix` require `ollama` plus the configured local model for generation
- `fix` is best when the Zenith shell fragment is loaded, but it can also fall back to bash or zsh history
