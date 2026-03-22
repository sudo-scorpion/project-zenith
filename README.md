# Project Zenith

Project Zenith has one setup command, one cleanup command, one fresh-reset command, and one daily-use command.

## What Users Should Remember

Setup:

```bash
./bootstrap.sh
```

Cleanup:

```bash
./teardown.sh
```

Fresh reset:

```bash
./bootstrap.sh fresh
```

Daily use after setup:

```bash
zen
```

That is the intended user experience.

`./bootstrap.sh` now fails fast during container setup if it cannot provision the required core tools and Ollama model, so it will not pretend the setup finished when the container is still incomplete. The default hybrid path keeps heavy AI and terminal dependencies in the container instead of installing them on the host.

## Recommended setup

```bash
./bootstrap.sh host --terminal kitty
```

Installs everything on your machine: all shell tools, Kitty terminal, zsh config, starship prompt, `ai` and `fix` shortcuts. Uses `sudo` for system packages.

## Modes

Setup:

- `./bootstrap.sh host --terminal kitty`: **recommended** — all tools on your host, Kitty terminal
- `./bootstrap.sh host --fresh --terminal kitty`: clean reinstall of host Zenith
- `./bootstrap.sh`: hybrid setup — lightweight host CLI plus Podman container for AI/Ollama
- `./bootstrap.sh --gpu nvidia`: hybrid with required NVIDIA GPU passthrough in the container
- `./bootstrap.sh --terminal kitty`: hybrid plus a host Kitty install
- `./bootstrap.sh container`: container-only setup
- `./bootstrap.sh fresh`: clean reinstall of the hybrid setup

Daily shortcuts (available after install):

- `ai "<request>"`: turn a plain-English request into a shell command
- `fix`: analyze the last failed command and suggest a fix
- `zen workspace`: open a focused Zellij session

Cleanup:

- `./teardown.sh host`: remove host Zenith — undoes everything including system packages
- `./teardown.sh`: remove the full hybrid setup including container
- `./teardown.sh container`: remove container artifacts only

## Plain-English Picture

**Host mode (recommended), plain English:**

- host: all shell tools, AI (Ollama + model), Kitty terminal, shell config, `ai` and `fix` shortcuts — everything lives on your machine
- host-only by design: `surface`, terminal config, shaders, and GUI integration

**Hybrid mode, plain English:**

- host: lightweight `zen` launcher, config, and other user-owned Zenith files only
- container: heavy runtime tools like `ollama`, `zellij`, `yazi`, `starship`, and model files, with optional NVIDIA GPU passthrough
- host-only by design: `surface`, terminal config, shaders, GUI integration, and any explicit host terminal bootstrap you request

Use these commands when you want transparency:

- `./probe.sh`: see what Zenith owns on the host
- `zen status --json`: see the active runtime state, including the selected surface terminal, installed surface version, recommended version, and startup upgrade policy
- `zen doctor`: see whether major dependencies, AI runtime, and surface upgrade state are healthy
- `zen upgrade surface --check`: see whether Zenith recommends installing or upgrading the configured surface terminal
- `zen config show`: see the active config values

For the full scenario guide, read [Deployment guide](docs/deployment.md). For tunables and records, read [Settings and visibility](docs/settings.md).

## Surface Upgrade Management

Use these when you want Zenith to manage the host-side terminal surface over time:

- `zen upgrade surface --check`: tell me what Zenith recommends right now
- `zen upgrade surface`: install or upgrade the configured supported surface terminal in user space
- `zen config edit`: turn startup checks or auto-upgrades on or off in the `[updates]` section

The startup controls live in `[updates]`:

- `check_on_startup = true`: perform periodic upgrade checks during shell startup
- `recommend_on_startup = true`: print a recommendation if Zenith sees an available install or upgrade
- `auto_upgrade_on_startup = true`: actually apply the supported surface upgrade during startup
- `startup_interval_hours = 24`: minimum time between startup checks

## No-Sudo Host Rule

The `zen` CLI does not use `sudo` unless you explicitly opt in with `--packages`.

What that means:

- `zen install core` (without `--packages`) stays in user space — no package-manager changes, no sudo
- `./bootstrap.sh host` passes `--packages` automatically, which installs system packages via your distro's package manager with sudo — this is intentional for the recommended daily-driver setup
- hybrid mode keeps the host light and puts the heavy runtime in Podman — no sudo, no host package-manager changes
- surface install is always user space only, regardless of mode, including Kitty by default and Zig for Ghostty builds
- if a host-side binary is not available and Zenith does not ship a local bootstrap for it, Zenith tells you that plainly instead of trying to elevate privileges

## Uninstall And Cleanup

For most users, uninstalling Zenith means:

```bash
./teardown.sh
```

That removes the full recommended setup by default, including:

- host Zenith config and state under `~/.config/zenith`
- host Zenith data under `~/.local/share/zenith`
- local shims such as `~/.local/bin/zen` and `~/.local/bin/zenith`
- the installed Python package when present
- the persistent Podman container, Zenith volumes, and built Zenith image

If you only want one side removed:

- `./teardown.sh host`
- `./teardown.sh container`

Advanced direct CLI cleanup still exists through `zen uninstall`, but normal users should use `./teardown.sh`.

If you want a true from-scratch reinstall, use:

```bash
./bootstrap.sh fresh
```

## What Users Can Ignore

These are not normal user setup commands:

- `zenith.sh`: repo-local developer runner
- `bin/zen`: packaged/internal CLI entrypoint
- `tests/*.sh`: project verification scripts

## What Zenith Includes

- `core`: shell tooling, workspace support, AI helpers, status, rollback
- `surface`: host-native terminal UX settings, Kitty config, optional Ghostty assets, and GUI integration hooks
- container-aware runtime detection and install behavior
- bundled config assets and packaged Python entrypoints

## Container Support

Zenith is container-aware rather than container-dependent.

- `core` works on host or in containers
- `surface` is host-only
- `./bootstrap.sh` defaults to hybrid setup (use `./bootstrap.sh host` for the recommended daily-driver)
- `./bootstrap.sh --gpu auto|nvidia|none` controls Podman container GPU passthrough
- `./teardown.sh` removes the same hybrid setup by default

For NVIDIA GPUs, Zenith can now request container GPU passthrough directly during bootstrap. Zenith still does not install the host NVIDIA container toolkit for you, so that host prerequisite must already exist.

## Contributing

```bash
git clone https://github.com/project-zenith/project-zenith
cd project-zenith
pip install -e .
bash tests/smoke/router.sh
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CLAUDE.md](CLAUDE.md) for development guidance.

## Docs

- [Install notes](docs/install.md)
- [Deployment guide](docs/deployment.md)
- [Settings and visibility](docs/settings.md)
- [Command reference](docs/commands.md)
- [Container support](docs/container.md)
- [Profiles](docs/profiles.md)
- [Safety](docs/safety.md)
- [Rollback](docs/rollback.md)
- [Architecture diagrams](docs/architecture.md)
- [Testing](docs/testing.md)
