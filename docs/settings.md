# Settings And Visibility

This page explains what Zenith records, where to look after setup, and what you can tweak.

## Visibility commands

Use these commands to understand what Zenith did and what is active now.

### Host-side visibility

```bash
./probe.sh
```

`probe.sh` checks for Zenith-owned artifacts such as:
- config and data directories
- shims in `~/.local/bin`
- fallback binaries such as `ollama`, `kitty`, `kitten`, `zellij`, `yazi`, `ya`, `starship`, and sometimes `zig` for Ghostty builds
- managed Kitty, Ghostty, Zellij, and Starship assets
- Podman container, image, and volume artifacts

### Runtime visibility

```bash
zen status --json
zen doctor
zen config show
zen config path
```

These commands show:
- resolved mode
- shell integration
- workspace state
- AI provider and model
- AI runtime state such as GPU or CPU
- chosen surface terminal
- installed surface version
- recommended surface version
- upgrade status and startup-upgrade policy
- config location
- manifest location

## Config locations

### Host mode

Host Zenith config normally lives at:

```bash
~/.config/zenith/zenith.toml
```

### Hybrid and container modes

When you use the container runtime, the active config is the container config:

```bash
/root/.config/zenith/zenith.toml
```

To inspect it from the host:

```bash
podman exec -it zenith-shell zen config path
podman exec -it zenith-shell zen config show
```

## Main settings you can tweak

### Top-level settings

- `profile`: `safe` or `personal`
- `mode`: `auto`, `host`, or `container`
- `shell`: `bash` or `zsh`

### `[ai]`

These control AI behavior.

- `provider`: currently `ollama`
- `host`: Ollama endpoint, for example `http://127.0.0.1:11434`
- `model`: default model. Zenith now ships with a single-model default of `qwen3.5:4b`
- `ask_model`: optional faster model just for `zen ask`
- `fix_model`: optional stronger model just for `zen fix`
- `keep_alive`: how long Ollama keeps the model warm
- `timeout_seconds`: request timeout
- `temperature`: lower is more deterministic
- `num_ctx`: context size
- `num_predict`: generation limit
- `top_k`
- `top_p`
- `repeat_penalty`
- `structured_output`: ask Ollama for structured JSON command output
- `auto_execute_safe`: whether safe commands may be executed automatically
- `log_generated_commands`: whether generated commands are written to Zenith audit logs

### `[workspace]`

These control workspace behavior.

- `default_session`: default `zellij` session name
- `auto_resume`: whether Zenith should prefer resuming the workspace session

### `[surface]`

These matter only for host-native surface behavior.

- `terminal`: preferred host terminal name
- `orbit_profile`
- `auto_sync`

Zenith records the terminal name and, for supported terminals, tries to install that terminal in user space. On the host, surface changes stay in user space only.

### `[updates]`

These control whether Zenith checks for or applies surface upgrades on shell startup.

- `check_on_startup`: whether Zenith should check for a newer supported surface version during shell startup
- `recommend_on_startup`: whether Zenith should print a recommendation when an install or upgrade is available
- `auto_upgrade_on_startup`: whether Zenith should apply the supported surface upgrade automatically during shell startup
- `startup_interval_hours`: minimum interval between startup checks
- `kitty_version`: optional pinned Kitty version when you want deterministic installs or upgrades
- `ghostty_version`: optional pinned Ghostty version when you want deterministic installs or upgrades

Practical use:

- run `zen upgrade surface --check` when you want an explicit recommendation now
- set `check_on_startup = true` and `recommend_on_startup = true` if you want a startup reminder
- set `auto_upgrade_on_startup = true` only if you want Zenith to actually replace the managed surface terminal automatically

### `[features]`

These describe which parts of Zenith are enabled.

- `core`
- `surface`
- `ai_nav`
- `ai_fix`
- `workspace`
- `orbit`
- `alias_overrides`

## Records Zenith keeps

Zenith keeps lightweight records so you can inspect what happened later.

- config under `~/.config/zenith/`
- state under `~/.config/zenith/state/`
- startup upgrade state under `~/.config/zenith/state/upgrade_state.json`
- logs under `~/.config/zenith/logs/`
- manifests under `~/.local/share/zenith/manifests/`
- backups under `~/.local/share/zenith/backups/`

In container mode, these paths are inside the container home and usually backed by Podman volumes.

## Practical tuning advice

If AI is too slow:
- check `zen doctor` or `zen status --json` first
- confirm whether Ollama is using GPU or CPU
- use a smaller `ask_model`
- keep `temperature = 0.0`
- keep `num_predict` small for command generation
- increase `keep_alive` so the model stays warm
