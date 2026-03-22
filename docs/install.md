# Install Notes

## Supported install targets

Zenith supports three install targets:

- `zen install core`
- `zen install surface`
- `zen install all`

Core is the safe baseline. Surface is optional and host-only.

## Plain-English setup map

If you want the short human explanation:

- `./bootstrap.sh`: recommended hybrid mode, with lightweight host CLI and heavy runtime tools in the container
- `./bootstrap.sh --gpu nvidia`: same setup, but require NVIDIA GPU passthrough in the Podman container
- `./bootstrap.sh fresh`: wipe the recommended setup and rebuild it from scratch
- `./bootstrap.sh host`: put Zenith directly on the host in user space only
- `./bootstrap.sh container`: only prepare the container side

For a fuller scenario guide, read [Deployment guide](deployment.md). For tunables and records, read [Settings and visibility](settings.md).

## Package-manager behavior

Zenith now keeps a strict split:

- container mode may use the container package manager because that work stays inside the container
- host mode does not use `sudo` and does not make host package-manager changes
- host-side bootstraps only happen when Zenith can manage them in user space

That means host mode is intentionally honest: if a host-side binary is missing and Zenith does not have a local bootstrap for it, Zenith tells you plainly instead of trying to elevate privileges.

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
zen install surface --mode host --terminal kitty --yes
```

Surface requires:

- resolved host mode

Surface install is user-space only. If no GUI session is active, Zenith still installs or verifies the terminal binary and records the preference, but it skips GUI-facing surface assets.

What Zenith does:
- records the chosen terminal name in Zenith config
- attempts a user-space install for that terminal when Zenith knows how
- installs built-in terminal assets only when Zenith ships them for that terminal
- writes Kitty config under `~/.config/kitty/kitty.conf` when `terminal = kitty`
- writes Ghostty config plus shader assets under `~/.config/ghostty` when `terminal = ghostty`

What Zenith does not do:
- use `sudo`
- install host packages for you
- pretend a terminal binary was installed when it was not

Current built-in user-space terminal bootstrap:
- `kitty` on Linux, using the official Kitty installer into `~/.local/kitty.app` with launchers in `~/.local/bin`
- `ghostty` on Linux, using the official Ghostty source-build path into `~/.local`
- Zenith now bootstraps the required Zig version in user space automatically when it can
- the remaining host-side prerequisites are GTK4, libadwaita, pkg-config/pkgconf, and gettext

## Install all

```bash
zen install all --mode auto --yes
```

`install all` always installs core first. In non-host modes, Zenith warns and skips the surface layer. In host mode, Zenith attempts the requested terminal bootstrap and fails clearly if that host terminal cannot be installed or verified.

## Dry runs

```bash
zen install core --dry-run --yes
zen install all --mode container --dry-run --yes
```

Dry runs print the plan and package commands without writing config or manifest state.

When `./bootstrap.sh` prepares a container, it runs `zen install core` in strict mode. If required container features such as `zellij`, `yazi`, `starship`, `ollama`, or the configured Ollama model cannot be provisioned, bootstrap stops instead of reporting a fake success. The default hybrid path keeps those heavy dependencies in the container.

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
- `./teardown.sh clean`: alias for the default full cleanup

`./teardown.sh` removes Zenith config/state, attempts package uninstall for the Python package, removes the persistent Podman container, drops the Zenith volumes, and removes the built Zenith image.

## One-command fresh reinstall

```bash
./bootstrap.sh fresh
```

Fresh reset modes:

- `./bootstrap.sh fresh`: clean reinstall of the recommended hybrid setup
- `./bootstrap.sh host --fresh --terminal kitty`: clean reinstall of host Zenith only with an explicit surface terminal
- `./bootstrap.sh container --fresh`: clean reinstall of container Zenith only
