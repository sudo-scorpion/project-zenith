from __future__ import annotations

import os
import shutil
from pathlib import Path

from .models import EnvironmentInfo


DISTROBOX_MARKERS = (
    "DISTROBOX_ENTER_PATH",
    "DISTROBOX_HOST_HOME",
    "DISTROBOX_PATH",
)
PACKAGE_MANAGERS = (
    ("dnf", "dnf"),
    ("apt-get", "apt"),
    ("pacman", "pacman"),
    ("zypper", "zypper"),
    ("apk", "apk"),
    ("brew", "brew"),
)


def _read_os_release() -> tuple[str, str]:
    os_release = Path("/etc/os-release")
    distro = "unknown"
    version = "unknown"
    if os_release.exists():
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if line.startswith("ID="):
                distro = line.split("=", 1)[1].strip().strip('\"')
            if line.startswith("VERSION_ID="):
                version = line.split("=", 1)[1].strip().strip('\"')
    return distro, version


def _detect_container() -> tuple[bool, str, bool]:
    distrobox = any(os.environ.get(marker) for marker in DISTROBOX_MARKERS)
    runtime = "none"

    if Path("/run/.containerenv").exists():
        runtime = "podman"
    elif Path("/.dockerenv").exists():
        runtime = "docker"
    elif os.environ.get("container"):
        runtime = str(os.environ["container"])

    container = runtime != "none" or distrobox
    if distrobox and runtime == "none":
        runtime = "distrobox"
    return container, runtime, distrobox


def detect_environment(mode: str) -> EnvironmentInfo:
    distro, version = _read_os_release()
    package_manager = "unknown"
    for binary, label in PACKAGE_MANAGERS:
        if shutil.which(binary):
            package_manager = label
            break

    container, container_runtime, distrobox = _detect_container()
    gui = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    systemd = shutil.which("systemctl") is not None
    gpu_tools = (
        shutil.which("nvidia-smi") is not None
        or shutil.which("glxinfo") is not None
        or shutil.which("vulkaninfo") is not None
        or Path("/dev/nvidia0").exists()
        or Path("/dev/dri/card0").exists()
    )

    resolved_mode = mode
    if mode == "auto":
        resolved_mode = "container" if container else "host"

    return EnvironmentInfo(
        distro=distro,
        version=version,
        package_manager=package_manager,
        container=container,
        container_runtime=container_runtime,
        distrobox=distrobox,
        gui=gui,
        systemd=systemd,
        gpu_tools=gpu_tools,
        resolved_mode=resolved_mode,
    )
