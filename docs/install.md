# Install Notes

## Supported install targets

Zenith supports three install targets:

- `zen install core`
- `zen install surface`
- `zen install all`

Core is the safe baseline. Surface is optional and host-only.

## Package-manager behavior

Zenith now automates package installation plans for:

- Fedora-style `dnf`
- Arch-style `pacman`
- Debian and Ubuntu style `apt`
- openSUSE style `zypper`
- Alpine style `apk`
- Homebrew `brew`

Package installs are attempted one package at a time so Zenith can continue its local config work even when a distro repository is missing one of the optional tools.

## Shell support

Zenith installs shell integration for:

- `bash`
- `zsh`

Use `--shell bash|zsh` during install, or let Zenith default to the current `SHELL` when it is supported.

## Core install

```bash
zen install core --yes
zen install core --shell zsh --yes
```

Core install writes or manages:

- `~/.config/zenith/zenith.toml`
- `~/.config/zenith/zenith.bashrc` or `~/.config/zenith/zenith.zshrc`
- `~/.local/bin/zen`
- `~/.local/bin/zenith`
- prompt overrides under `~/.config/zenith/prompts/`
- state capture files under `~/.config/zenith/state/`
- Starship and Zellij assets
- a manifest under `~/.local/share/zenith/manifests/`

Existing managed files are backed up before Zenith rewrites them.

## Surface install

```bash
zen install surface --mode host --yes
```

Surface requires:

- resolved host mode
- a GUI session

It manages Ghostty config plus shader assets under `~/.config/ghostty`.

## Install all

```bash
zen install all --mode auto --yes
```

`install all` always installs core first. If surface requirements are not met, Zenith warns and skips the surface layer instead of failing the full install.

## Dry runs

```bash
zen install core --dry-run --yes
zen install all --mode container --dry-run --yes
```

Dry runs print the plan and package commands without writing config or manifest state.

When `./bootstrap.sh` prepares a container, it runs `zen install core` in strict mode. If required container features such as `zellij`, `yazi`, `starship`, `ollama`, or the configured Ollama model cannot be provisioned, bootstrap stops instead of reporting a fake success.

## Uninstall and rollback

- `zen rollback` reverts the latest manifest transaction
- `zen uninstall` reverts all manifest transactions and removes Zenith-owned config/share directories


## One-command cleanup

```bash
./teardown.sh
```

Cleanup modes:

- `./teardown.sh`: remove the recommended hybrid setup
- `./teardown.sh host`: remove host Zenith only
- `./teardown.sh container`: remove container artifacts only

`./teardown.sh` removes Zenith config/state, attempts package uninstall for the Python package, removes the persistent Podman container, drops the Zenith volumes, and removes the built Zenith image.
