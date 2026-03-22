# Zenith Architecture

Zenith works best when you think about it as two products that share one CLI:

- `core`: portable shell/runtime features
- `surface`: host-native terminal UX

GitHub and VS Code both render the Mermaid diagrams below, so this file is the visual architecture reference.

## 1. Product split

```mermaid
flowchart TD
    U[User] --> Z[zen CLI]
    Z --> C[Zenith Core]
    Z --> S[Zenith Surface]

    C --> C1[Shell integration]
    C --> C2[Workspace via Zellij]
    C --> C3[AI helpers via Ollama]
    C --> C4[Status / doctor / rollback]
    C --> C5[Local XDG state]

    S --> S1[Ghostty config]
    S --> S2[Shaders / orbit themes]
    S --> S3[Fonts]
    S --> S4[GUI session integration]

    H[Host machine] --> S
    H --> C
    P[Podman / Docker container] --> C

    P -. no GUI surface .-> S
```

## 2. Mental model

```mermaid
flowchart LR
    subgraph Host
        H1[GUI session]
        H2[Ghostty]
        H3[Fonts / shaders]
        H4[~/.config/zenith]
        H5[~/.local/share/zenith]
    end

    subgraph Container
        C1[zen install core]
        C2[Zellij / yazi / starship]
        C3[Ollama + model]
        C4[Project workspace]
        C5[Mounted Zenith state]
    end

    H2 --> C4
    H4 <--> C5
    H5 <--> C5

    H1 --> H2
    H2 --> H3
    C1 --> C2
    C1 --> C3
    C1 --> C4
```

This is the intended split:

- Host: visual terminal experience
- Container: isolated tool/runtime experience
- Shared state: Zenith config, manifests, backups, prompts

## 3. Runtime flow

```mermaid
flowchart TD
    U[User command] --> E[zen / zenith entrypoint]
    E --> R[CLI router in src/zenith/cli.py]

    R --> I[install.py]
    R --> D[detect.py]
    R --> T[doctor.py / status.py]
    R --> W[workspace.py]
    R --> A[ai.py]
    R --> L[rollback.py + manifest.py]

    I --> AS[Bundled assets in src/zenith/assets]
    I --> CFG[zenith.toml + shell fragments]
    I --> PKG[Package manager or fallback bootstrap]

    A --> PROMPTS[prompts]
    A --> OLLAMA[Ollama runtime]
    A --> AUDIT[audit logs]

    L --> MANIFESTS[install manifests]
    L --> BACKUPS[file backups]

    T --> STATE[shell state capture]
    W --> ZELLIJ[Zellij session]
```

## 4. Install paths

```mermaid
flowchart TD
    START[Choose setup] --> Q1{Need native GUI terminal polish?}
    Q1 -- Yes --> HOST[Host install]
    Q1 -- No --> COREONLY[Container core install]

    HOST --> H1[zen install all --mode host --yes]
    H1 --> H2[Core + Surface]
    H2 --> H3[Ghostty + shell tooling + AI]

    COREONLY --> C1[zen install core --mode container --yes]
    C1 --> C2[Shell tooling + workspace + AI]
    C2 --> C3[No Ghostty surface]

    HOST --> HYBRID{Also want isolated dev env?}
    HYBRID -- Yes --> BEST[Best overall setup]
    BEST --> B1[Host runs Surface]
    BEST --> B2[Container runs Core]
```

## 5. Files by responsibility

### User-facing entrypoints
- `zenith.sh`: local repo bootstrap wrapper
- `bin/zen`: CLI script entrypoint
- `src/zenith/cli.py`: command router

### Install and lifecycle
- `src/zenith/install.py`: installs `core` and `surface`
- `src/zenith/manifest.py`: transaction history
- `src/zenith/rollback.py`: rollback and uninstall
- `src/zenith/backup.py`: file backup helpers

### Environment and health
- `src/zenith/detect.py`: host/container/runtime detection
- `src/zenith/status.py`: user-facing status output
- `src/zenith/doctor.py`: health checks
- `src/zenith/paths.py`: XDG and state paths

### Runtime features
- `src/zenith/workspace.py`: Zellij session handling
- `src/zenith/ai.py`: `nav` and `fix`
- `src/zenith/surface.py`: orbit/surface behavior
- `src/zenith/shells.py`: bash/zsh integration points

### Assets and config
- `src/zenith/assets/`: packaged prompts and shell/config assets
- `configs/`: source config assets in the repo
- `prompts/`: editable prompt source files

## 6. State layout

```mermaid
flowchart LR
    CFG[~/.config/zenith] --> CFG1[zenith.toml]
    CFG --> CFG2[zenith.bashrc / zenith.zshrc]
    CFG --> CFG3[state/]
    CFG --> CFG4[prompts/]
    CFG --> CFG5[logs/]

    DATA[~/.local/share/zenith] --> D1[manifests/]
    DATA --> D2[backups/]
    DATA --> D3[audit/]
    DATA --> D4[sessions/]
```

## 7. Recommended usage

If you only remember one picture, remember this:

```mermaid
flowchart LR
    subgraph Best Experience
        HOST2[Host Surface]
        CONT2[Container Core]
    end

    HOST2 --> UX[Native terminal UX]
    CONT2 --> ISO[Clean isolated toolchain]

    UX --> USER[User]
    ISO --> USER
```

Best practical choices:

- Want the nicest terminal UX: use host `surface`
- Want isolation and resettable tooling: use container `core`
- Want the strongest overall setup: host `surface` plus container `core`
