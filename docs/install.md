# Install Notes

## Supported install targets

Zenith supports three install targets:

- `zen install core`
- `zen install surface`
- `zen install all`

Core is the baseline. Surface is optional and host-only.

## Plain-English setup map

```bash
./bootstrap.sh host --terminal kitty        # recommended: everything on your host
./bootstrap.sh host --fresh --terminal kitty # clean reinstall on your host
./bootstrap.sh                               # hybrid: lightweight host + Podman container for AI
./bootstrap.sh --gpu nvidia                  # hybrid with NVIDIA GPU passthrough in container
./bootstrap.sh fresh                         # wipe hybrid setup and rebuild from scratch
./bootstrap.sh container                     # container side only
```

For a fuller scenario guide, read [Deployment guide](deployment.md). For tunables and records, read [Settings and visibility](settings.md).

## Package-manager behavior

Zenith has two modes for host package installs:

**Without `--packages`** (default for `zen install core`):
- skips system package manager on the host
- only bootstraps tools Zenith can manage in user space (zellij, yazi, starship, ollama from release archives)
- no `sudo`

**With `--packages`** (automatic when using `./bootstrap.sh host`):
- installs all core tools via the system package manager with `sudo`
- on Fedora: `sudo dnf install zsh zellij yazi eza bat starship zoxide fzf ripgrep btop fastfetch ollama`
- all installed packages are tracked in the Zenith manifest for clean uninstall

In container mode, the container package manager runs as root — no sudo needed.

## Shell support

Zenith installs shell integration for:

- `zsh` (default)
- `bash`

Use `--shell bash|zsh` during install, or let Zenith default to the current `SHELL` when it is supported.

## Core install

```bash
zen install core --yes                        # auto-detect shell, no system packages
zen install core --packages --yes             # also install system packages via sudo
zen install core --shell zsh --yes
```

Core install writes or manages:

- `~/.config/zenith/zenith.toml`
- `~/.config/zenith/zenith.zshrc` or `~/.config/zenith/zenith.bashrc`
- `~/.local/bin/zen` and `~/.local/bin/zenith`
- `~/.config/starship.toml`
- `~/.config/zellij/layouts/zenith.kdl` and `~/.config/zellij/config.kdl`
- `~/.local/share/zsh-plugins/zsh-autosuggestions`
- `~/.local/share/zsh-plugins/zsh-syntax-highlighting`
- `~/.local/lib/ollama/` — GPU backend libraries for Ollama (when bootstrapping from release)
- prompt overrides under `~/.config/zenith/prompts/`
- state capture files under `~/.config/zenith/state/`
- a manifest under `~/.local/share/zenith/manifests/`
- `ai` and `fix` shell function shortcuts (sourced via the shell fragment)

Existing managed files are backed up before Zenith rewrites them.

## Surface install

```bash
zen install surface --mode host --terminal kitty --yes
```

Surface requires resolved host mode.

Surface install is user-space only.

What Zenith does:
- records the chosen terminal name in Zenith config
- attempts a user-space install for that terminal when Zenith knows how
- writes Kitty config under `~/.config/kitty/kitty.conf` when `terminal = kitty`
- writes Ghostty config plus shader assets under `~/.config/ghostty` when `terminal = ghostty`

What Zenith does not do:
- use `sudo`
- install host packages
- pretend a terminal binary was installed when it was not

Current built-in user-space terminal bootstrap:
- `kitty` on Linux, using the official Kitty installer into `~/.local/kitty.app` with launchers in `~/.local/bin`
- `ghostty` on Linux, using the official Ghostty source-build path into `~/.local`

## Install all

```bash
zen install all --mode host --packages --yes
```

`install all` installs core first, then surface. The `--packages` flag enables system package manager installs. `./bootstrap.sh host` passes this automatically.

## Dry runs

```bash
zen install core --dry-run --yes
zen install all --mode host --packages --dry-run --yes
```

Dry runs print the plan and package commands without writing config or manifest state.

## Uninstall and rollback

- `zen rollback` reverts the latest manifest transaction
- `zen uninstall` reverts all manifest transactions and removes Zenith-owned config/share directories

## One-command cleanup

```bash
./teardown.sh host    # remove host Zenith
./teardown.sh         # remove full hybrid setup
```

`./teardown.sh host` removes:
- Zenith config, state, and data directories
- shell fragment hooks stripped from `.zshrc`, `.bashrc`, `.zprofile`, `.bash_profile`
- system packages installed by Zenith (via `sudo dnf remove`)
- user-space binaries in `~/.local/bin/`
- zsh plugins at `~/.local/share/zsh-plugins/`
- Ollama GPU libraries at `~/.local/lib/ollama/`
- caches: `~/.cache/starship`, `~/.cache/zoxide`, `~/.local/share/zoxide`
- zsh completion dumps: `~/.zcompdump*`

## One-command fresh reinstall

```bash
./bootstrap.sh host --fresh --terminal kitty
```
