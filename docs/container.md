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

## Development container

The included `Containerfile` builds a Fedora-based development image and installs the packaged project:

```bash
podman build -t zenith-dev .
podman run --rm -it zenith-dev status --json
```

This image is meant for local verification of the CLI and tests. It does not set up host-side Ollama integration automatically.
