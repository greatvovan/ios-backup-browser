import plistlib
from pathlib import Path
from datetime import datetime, timezone


def _read_plist(plist_path: Path) -> dict:
    """Read and return a plist file."""
    with plist_path.open("rb") as f:
        return plistlib.load(f)

class Info:
    def __init__(self, base_path: Path):
        self.data = _read_plist(base_path / "Info.plist")
    
    def get_apps(self) -> list[dict]:
        """Return a list of installed apps from the Info.plist."""
        result = []
        for bundle_id, app_info in self.data.get("Applications", {}).items():
            iTunesMetadata = app_info.get("iTunesMetadata", b'')
            if iTunesMetadata:
                try:
                    metadata = plistlib.loads(iTunesMetadata)
                    app_record = {
                        "bundle_id": bundle_id,
                        "name": metadata.get("itemName", ""),
                        "title": metadata.get("title", ""),
                        "type": metadata.get("genre", ""),
                        "version": metadata.get("bundleShortVersionString", ""),
                    }
                except Exception:
                    continue

            result.append(app_record)
        return result


class Status:
    def __init__(self, base_path: Path):
        self.data = _read_plist(base_path / "Status.plist")


class Manifest:
    def __init__(self, base_path: Path):
        self.data = _read_plist(base_path / "Manifest.plist")


def get_backup_summary(info: Info, status: Status, manifest: Manifest) -> dict[str, str]:
    """Generate a summary of the backup info."""
    _u = "Unknown"
    backup_date: datetime | None = info.data.get("Last Backup Date")
    summary = {
        "Device Name": info.data.get("Device Name", _u),
        "Device Type": info.data.get("Product Type", _u),
        "Model Name": info.data.get("Product Name", _u),
        "OS Version": info.data.get("Product Version", _u),
        "Serial Number": info.data.get("Serial Number", _u),
        "IMEI": info.data.get("IMEI", _u),
        "Device ID": info.data.get("Unique Identifier", _u),
        "Backup Date (UTC)": backup_date.strftime("%Y-%m-%d %H:%M:%S") if backup_date else _u,
        "Backup Date (local)": backup_date.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S") if backup_date else _u,
        "Encrypted": "Yes" if manifest.data.get("IsEncrypted") else "No",
    }
    return summary
