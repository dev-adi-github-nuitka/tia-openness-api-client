"""
Siemens TIA Portal Openness API whitelisting utilities.

Detects installed TIA Portal versions from the Windows registry and
registers executables in the Siemens Openness whitelist so that
TIA Portal permits programmatic access from those binaries.
"""

from __future__ import annotations

import base64
import hashlib
import winreg
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from tia_portal.version import TiaVersion

VERSION: TiaVersion = TiaVersion.V18


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_UNINSTALL_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]

# Path to the Python executable that TIA Portal's Openness firewall must trust.
# This must match the exact binary the Agent uses to run this driver.
#
# TODO: Replace with the production path used on the Agent machine, e.g.:
#   C:\ProgramData\Verve Industrial Protection\Agent\AdiDrivers\
#       AdiDriverInstallations\<driver name>\Scripts\python.exe
#
# The current value is a development-only default for local testing.
_EXE_PATH = r"C:\Users\Administrator\AppData\Roaming\uv\python\cpython-3.11.14-windows-x86_64-none\python.exe"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load(*, default: TiaVersion = TiaVersion.V18) -> None:
    """Set up the module by detecting the TIA Portal version and adding the Python executable to the whitelist."""
    global VERSION

    detected = detect_tia_portal_version()
    VERSION = detected or default

    add_to_whitelist(_EXE_PATH, VERSION)


def detect_tia_portal_version() -> TiaVersion | None:
    """Return the highest supported TIA Portal version installed on this machine, or None if not found."""
    candidates = []

    for name, version in _iter_uninstall_entries():
        if "Totally Integrated Automation Portal" in name and version in TiaVersion.__members__:
            candidates.append(version)

    return TiaVersion[max(candidates)] if candidates else None


def add_to_whitelist(exe_path: str, tia_version: TiaVersion) -> None:
    """
    Register *exe_path* in the Siemens Openness whitelist for the given TIA version.

    Values written:
        - Path         (REG_SZ)
        - DateModified (REG_SZ) -> UTC, "yyyy/MM/dd HH:mm:ss.fff"
        - FileHash     (REG_SZ) -> Base64-encoded SHA-256 of the EXE bytes
    """
    path = Path(exe_path)
    if not path.is_file():
        raise Exception(f"Executable not found: {exe_path}. Cannot add to Siemens Openness whitelist.")

    file_hash, date_modified = _compute_hash_and_date(path)

    # TIA expects a decimal in the version folder (e.g., V18.0, V21.0)
    reg_path = rf"SOFTWARE\Siemens\Automation\Openness\{tia_version.value}.0\Whitelist\{path.name}\Entry"

    try:
        with (
            winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as hklm,
            winreg.CreateKeyEx(hklm, reg_path, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as entry,
        ):
            winreg.SetValueEx(entry, "Path", 0, winreg.REG_SZ, str(exe_path))
            winreg.SetValueEx(entry, "DateModified", 0, winreg.REG_SZ, date_modified)
            winreg.SetValueEx(entry, "FileHash", 0, winreg.REG_SZ, file_hash)
    except PermissionError as e:
        raise Exception(
            "Administrator permissions are required to modify the Siemens Openness whitelist in the Windows registry. "
            "Re-run in an elevated (Administrator) terminal."
        ) from e


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


def _read_display_entry(root: winreg.HKEYType, child: str) -> tuple[str, str] | None:
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


def _compute_hash_and_date(path: Path) -> tuple[str, str]:
    """Return (base64_sha256, utc_mtime_formatted) for *path*."""
    digest = hashlib.sha256(path.read_bytes()).digest()
    file_hash = base64.b64encode(digest).decode("ascii")

    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    date_mod = ts.strftime("%Y/%m/%d %H:%M:%S.") + f"{ts.microsecond // 1000:03d}"

    return file_hash, date_mod
