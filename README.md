# Project Zenith

Project Zenith has one setup command, one cleanup command, and one daily-use command.

## What Users Should Remember

Setup:

```bash
./bootstrap.sh
```

Cleanup:

```bash
./teardown.sh
```

Daily use after setup:

```bash
zen
```

That is the intended user experience.

`./bootstrap.sh` now fails fast during container setup if it cannot provision the required core tools and Ollama model, so it will not pretend the setup finished when the container is still incomplete.

## Modes

Setup:

- `./bootstrap.sh`: recommended full setup
- `./bootstrap.sh host`: host-only setup
- `./bootstrap.sh container`: container-only setup

Cleanup:

- `./teardown.sh`: remove the recommended full setup
- `./teardown.sh host`: remove host Zenith only
- `./teardown.sh container`: remove container artifacts only

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


## What Users Can Ignore

These are not normal user setup commands:

- `zenith.sh`: repo-local developer runner
- `bin/zen`: packaged/internal CLI entrypoint
- `tests/*.sh`: project verification scripts

## What Zenith Includes

- `core`: shell tooling, workspace support, AI helpers, status, rollback
- `surface`: host-native terminal UX, Ghostty config, shaders, fonts, GUI integration
- container-aware runtime detection and install behavior
- bundled config assets and packaged Python entrypoints

## Container Support

Zenith is container-aware rather than container-dependent.

- `core` works on host or in containers
- `surface` is host-only
- `./bootstrap.sh` defaults to the recommended hybrid setup
- `./teardown.sh` removes the same hybrid setup by default

## Docs

- [Install notes](docs/install.md)
- [Command reference](docs/commands.md)
- [Container support](docs/container.md)
- [Profiles](docs/profiles.md)
- [Safety](docs/safety.md)
- [Rollback](docs/rollback.md)
- [Architecture diagrams](docs/architecture.md)
- [Testing](docs/testing.md)
