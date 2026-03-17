"""
Siemens TIA Portal Openness API configuration utilities.

Detects installed TIA Portal versions from the Windows registry
so the driver can load the correct Openness API assemblies.
"""

from __future__ import annotations

import winreg
from collections.abc import Iterator
from typing import Optional

from tia_portal.version import TiaVersion

VERSION: TiaVersion = TiaVersion.V18


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_UNINSTALL_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load(*, default: TiaVersion = TiaVersion.V18) -> None:
    """Detect the installed TIA Portal version and set the module-level VERSION."""
    global VERSION

    detected = detect_tia_portal_version()
    VERSION = detected or default


def detect_tia_portal_version() -> Optional[TiaVersion]:
    """Return the highest supported TIA Portal version installed on this machine, or None if not found."""
    candidates = []

    for name, version in _iter_uninstall_entries():
        if "Totally Integrated Automation Portal" in name and version in TiaVersion.__members__:
            candidates.append(version)

    return TiaVersion[max(candidates)] if candidates else None


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _iter_uninstall_entries() -> Iterator[tuple[str, str]]:
    """Yield (DisplayName, DisplayVersion) pairs from the 'Uninstall' registry keys."""
    for key_path in _UNINSTALL_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as root:
                for i in _iter_subkeys(root):
                    entry = _read_display_entry(root, i)
                    if entry is not None:
                        yield entry
        except FileNotFoundError:
            continue


def _iter_subkeys(root: winreg.HKEYType) -> Iterator[str]:
    """Yield subkey names under *root*."""
    idx = 0
    while True:
        try:
            yield winreg.EnumKey(root, idx)
            idx += 1
        except OSError:
            break


def _read_display_entry(root: winreg.HKEYType, child: str) -> Optional[tuple[str, str]]:
    """Return (DisplayName, DisplayVersion) for *child*, or None if unavailable."""
    try:
        with winreg.OpenKey(root, child) as app_key:
            name = str(winreg.QueryValueEx(app_key, "DisplayName")[0])
            version = str(winreg.QueryValueEx(app_key, "DisplayVersion")[0])
            if name and version:
                return name, version
    except OSError:
        pass
    return None
