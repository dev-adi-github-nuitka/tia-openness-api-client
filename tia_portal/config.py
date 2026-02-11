import winreg
from collections.abc import Iterator
from typing import Optional

from tia_portal.version import TiaVersion

VERSION: TiaVersion = TiaVersion.V18

_UNINSTALL_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]


def load(*, default: TiaVersion = TiaVersion.V18) -> None:
    """
    Detect the installed TIA Portal version and set the module-global VERSION variable.
    """
    global VERSION

    detected = detect_tia_portal_version()
    VERSION = detected or default


def detect_tia_portal_version() -> Optional[TiaVersion]:
    """
    Detect the highest supported TIA Portal version installed on the system.
    """
    versions: list[str] = []

    for name, version in iter_uninstall_entries():
        if ("Totally Integrated Automation Portal" in name) and (version in TiaVersion.__members__):
            versions.append(version)

    return TiaVersion[max(versions)] if versions else None


def iter_uninstall_entries() -> Iterator[tuple[str, str]]:
    """
    Yield (DisplayName, DisplayVersion) pairs from the Apps & Features registry.
    """
    for key in _UNINSTALL_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as root:
                i = 0
                while True:
                    try:
                        child = winreg.EnumKey(root, i)
                        i += 1
                    except OSError:
                        break
                    try:
                        with winreg.OpenKey(root, child) as app_key:
                            name = str(winreg.QueryValueEx(app_key, "DisplayName")[0])
                            version = str(winreg.QueryValueEx(app_key, "DisplayVersion")[0])

                            if name and version:
                                yield (name, version)
                    except OSError:
                        continue
        except FileNotFoundError:
            continue
