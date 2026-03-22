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

## Modes

Setup:

- `./bootstrap.sh`: recommended full setup
- `./bootstrap.sh host`: host-only setup
- `./bootstrap.sh container`: container-only setup

Cleanup:

- `./teardown.sh`: remove the recommended full setup
- `./teardown.sh host`: remove host Zenith only
- `./teardown.sh container`: remove container artifacts only

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
