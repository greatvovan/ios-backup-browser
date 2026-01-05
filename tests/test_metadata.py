import pytest
import plistlib
from pathlib import Path
from datetime import datetime, timezone

from ios_backup.metadata import Info, Status, Manifest, get_backup_summary


@pytest.fixture
def backup_dir(tmp_path):
    """Create a temporary directory with Info.plist, Status.plist, and Manifest.plist."""
    backup = tmp_path / "backup"
    backup.mkdir()
    return backup


@pytest.fixture
def info_plist_with_apps(backup_dir):
    """Create Info.plist with sample app data."""
    backup_date = datetime(2025, 12, 7, 14, 30, 0, tzinfo=timezone.utc)
    
    info_data = {
        "Device Name": "Test iPhone",
        "Product Type": "iPhone15,2",
        "Product Name": "iPhone 15 Pro",
        "Product Version": "18.1",
        "Serial Number": "ABC123XYZ",
        "IMEI": "123456789012345",
        "Unique Identifier": "device-id-12345",
        "Last Backup Date": backup_date,
        "Applications": {
            "com.apple.mobilesafari": {
                "iTunesMetadata": plistlib.dumps({
                    "itemName": "Safari Bundle Name",
                    "title": "Safari",
                    "genre": "Utilities",
                    "bundleShortVersionString": "1.0",
                }),
            },
            "com.example.testapp": {
                "iTunesMetadata": plistlib.dumps({
                    "itemName": "Test App Bundle Name",
                    "title": "Test Application",
                    "genre": "Games",
                    "bundleShortVersionString": "2.5.1",
                }),
            },
            "com.broken.app": {
                "iTunesMetadata": b"invalid plist data",
            },
        },
    }
    
    with (backup_dir / "Info.plist").open("wb") as f:
        plistlib.dump(info_data, f)
    
    return backup_dir, backup_date


@pytest.fixture
def status_and_manifest_plists(backup_dir):
    """Create Status.plist and Manifest.plist."""
    status_data = {"Status": "Success"}
    manifest_data = {"IsEncrypted": False, "Version": 1}
    
    with (backup_dir / "Status.plist").open("wb") as f:
        plistlib.dump(status_data, f)
    
    with (backup_dir / "Manifest.plist").open("wb") as f:
        plistlib.dump(manifest_data, f)
    
    return backup_dir


class TestInfo:
    def test_init_reads_info_plist(self, info_plist_with_apps):
        """Test Info initialization reads Info.plist."""
        backup_dir, _ = info_plist_with_apps
        info = Info(backup_dir)
        
        assert info.data is not None
        assert info.data["Device Name"] == "Test iPhone"
        assert info.data["Product Type"] == "iPhone15,2"

    def test_get_apps_returns_valid_apps(self, info_plist_with_apps):
        """Test get_apps returns list of apps with parsed metadata."""
        backup_dir, _ = info_plist_with_apps
        info = Info(backup_dir)
        
        apps = info.get_apps()
        assert len(apps) >= 2  # At least Safari and Test App
        
        # Check Safari app
        safari = next((app for app in apps if app["bundle_id"] == "com.apple.mobilesafari"), None)
        assert safari is not None
        assert safari["name"] == "Safari Bundle Name"
        assert safari["title"] == "Safari"
        assert safari["type"] == "Utilities"
        assert safari["version"] == "1.0"

    def test_get_apps_returns_all_valid_app_data(self, info_plist_with_apps):
        """Test get_apps returns correct metadata for all valid apps."""
        backup_dir, _ = info_plist_with_apps
        info = Info(backup_dir)
        
        apps = info.get_apps()
        
        # Check Test App
        test_app = next((app for app in apps if app["bundle_id"] == "com.example.testapp"), None)
        assert test_app is not None
        assert test_app["name"] == "Test App Bundle Name"
        assert test_app["title"] == "Test Application"
        assert test_app["type"] == "Games"
        assert test_app["version"] == "2.5.1"

    def test_get_apps_skips_invalid_metadata(self, info_plist_with_apps):
        """Test get_apps skips apps with invalid iTunesMetadata."""
        backup_dir, _ = info_plist_with_apps
        info = Info(backup_dir)
        
        apps = info.get_apps()
        
        # Broken app should not be in results
        broken_app = next((app for app in apps if app["bundle_id"] == "com.broken.app"), None)
        assert broken_app is None

    def test_get_apps_handles_missing_fields(self, backup_dir):
        """Test get_apps handles apps with missing optional fields gracefully."""
        info_data = {
            "Applications": {
                "com.test.minimal": {
                    "iTunesMetadata": plistlib.dumps({
                        "itemName": "Minimal App",
                        # Other fields omitted
                    }),
                },
            },
        }
        
        with (backup_dir / "Info.plist").open("wb") as f:
            plistlib.dump(info_data, f)
        
        info = Info(backup_dir)
        apps = info.get_apps()
        
        assert len(apps) == 1
        assert apps[0]["bundle_id"] == "com.test.minimal"
        assert apps[0]["name"] == "Minimal App"
        assert apps[0]["title"] == ""  # Default empty string
        assert apps[0]["type"] == ""
        assert apps[0]["version"] == ""

    def test_get_apps_empty_applications(self, backup_dir):
        """Test get_apps returns empty list when Applications dict is empty."""
        info_data = {"Applications": {}}
        
        with (backup_dir / "Info.plist").open("wb") as f:
            plistlib.dump(info_data, f)
        
        info = Info(backup_dir)
        apps = info.get_apps()
        
        assert apps == []

    def test_get_apps_missing_applications_key(self, backup_dir):
        """Test get_apps returns empty list when Applications key is missing."""
        info_data = {"Device Name": "Test"}
        
        with (backup_dir / "Info.plist").open("wb") as f:
            plistlib.dump(info_data, f)
        
        info = Info(backup_dir)
        apps = info.get_apps()
        
        assert apps == []


class TestBackupSummary:
    def test_get_backup_summary_returns_all_fields(self, info_plist_with_apps, status_and_manifest_plists):
        """Test get_backup_summary returns a dict with all expected fields."""
        backup_dir, _ = info_plist_with_apps
        
        info = Info(backup_dir)
        status = Status(backup_dir)
        manifest = Manifest(backup_dir)
        
        summary = get_backup_summary(info, status, manifest)
        
        # Verify all expected keys are present
        expected_keys = {
            "Device Name",
            "Device Type",
            "Model Name",
            "OS Version",
            "Serial Number",
            "IMEI",
            "Device ID",
            "Backup Date (UTC)",
            "Backup Date (local)",
            "Encrypted",
        }
        assert set(summary.keys()) == expected_keys

    def test_get_backup_summary_correct_device_info(self, info_plist_with_apps, status_and_manifest_plists):
        """Test get_backup_summary populates device info correctly."""
        backup_dir, backup_date = info_plist_with_apps
        
        info = Info(backup_dir)
        status = Status(backup_dir)
        manifest = Manifest(backup_dir)
        
        summary = get_backup_summary(info, status, manifest)
        
        assert summary["Device Name"] == "Test iPhone"
        assert summary["Device Type"] == "iPhone15,2"
        assert summary["Model Name"] == "iPhone 15 Pro"
        assert summary["OS Version"] == "18.1"
        assert summary["Serial Number"] == "ABC123XYZ"
        assert summary["IMEI"] == "123456789012345"
        assert summary["Device ID"] == "device-id-12345"
        assert summary["Backup Date (UTC)"] == "2025-12-07 14:30:00"
        assert summary["Backup Date (local)"] == backup_date.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        assert summary["Encrypted"] == "No"

    def test_get_backup_summary_missing_fields_use_unknown(self, backup_dir):
        """Test get_backup_summary uses 'Unknown' for missing optional fields."""
        info_data = {}
        status_data = {}
        manifest_data = {}
        
        with (backup_dir / "Info.plist").open("wb") as f:
            plistlib.dump(info_data, f)
        with (backup_dir / "Status.plist").open("wb") as f:
            plistlib.dump(status_data, f)
        with (backup_dir / "Manifest.plist").open("wb") as f:
            plistlib.dump(manifest_data, f)
        
        info = Info(backup_dir)
        status = Status(backup_dir)
        manifest = Manifest(backup_dir)
        
        summary = get_backup_summary(info, status, manifest)
        
        assert summary["Device Name"] == "Unknown"
        assert summary["Device Type"] == "Unknown"
        assert summary["Model Name"] == "Unknown"
        assert summary["OS Version"] == "Unknown"
        assert summary["Serial Number"] == "Unknown"
        assert summary["IMEI"] == "Unknown"
        assert summary["Device ID"] == "Unknown"
        assert summary["Backup Date (UTC)"] == "Unknown"
        assert summary["Backup Date (local)"] == "Unknown"

    def test_get_backup_summary_missing_backup_date(self, backup_dir):
        """Test get_backup_summary handles missing backup date gracefully."""
        info_data = {
            "Device Name": "Test Device",
            # No Last Backup Date
        }
        status_data = {}
        manifest_data = {}
        
        with (backup_dir / "Info.plist").open("wb") as f:
            plistlib.dump(info_data, f)
        with (backup_dir / "Status.plist").open("wb") as f:
            plistlib.dump(status_data, f)
        with (backup_dir / "Manifest.plist").open("wb") as f:
            plistlib.dump(manifest_data, f)
        
        info = Info(backup_dir)
        status = Status(backup_dir)
        manifest = Manifest(backup_dir)
        
        summary = get_backup_summary(info, status, manifest)
        
        assert summary["Backup Date (UTC)"] == "Unknown"
        assert summary["Backup Date (local)"] == "Unknown"
