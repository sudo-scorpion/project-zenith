# Container Support

Zenith is container-aware, not container-dependent.

## Detection

`zen status` and `zen doctor` report container details from:

- Docker markers such as `/.dockerenv`
- Podman markers such as `/run/.containerenv`
- generic `container` environment values
- Distrobox environment markers

With `--mode auto`, Zenith resolves to `container` when those markers are present.

## Behavior in container mode

- core workflows remain available
- `surface` installation is blocked
- `install all` installs core and warns that surface was skipped
- state remains under user-local XDG paths inside the container user's home
- `status` reports `container_runtime`, `distrobox`, `workspace_status`, `shell_integration`, and `latest_manifest_timestamp`
- package-manager automation still runs when a supported package tool is present in the container
- when distro packages are missing, `zen install core` now falls back to package-manager helpers plus release-download bootstrap paths for `zellij`, `yazi`, and `ollama`, and a local install path for `starship`
- `./bootstrap.sh` runs container core install in strict mode and stops if those required tools or the configured Ollama model cannot be provisioned
- in container mode, `zen install core` will also try to start Ollama and pull the configured default model so `zen nav` and `zen fix` can become usable without extra manual setup
- the image itself only bakes in the Python runtime plus Zenith; optional terminal tools are still provisioned by `zen install core`

## Container image

The included `Containerfile` builds a Fedora-based Zenith image that is suitable for normal container use:

```bash
podman build -t zenith .
podman run --rm -it zenith bash
```

Then inside the container:

```bash
zen install core --mode container --yes
zen doctor --json
zen status --json
```

This image is meant for CLI and core workflows inside Podman or Docker. It does not set up the host-only GUI `surface` layer or host-side Ollama integration automatically.
