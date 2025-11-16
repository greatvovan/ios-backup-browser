import hashlib
import os
import shutil
import plistlib
from pathlib import Path
from ios_backup.backup import Backup, Record


def create_src_file(backup_dir: Path, domain: str, relative_path: str, content: bytes = b"hello"):
    namespaced = f"{domain}-{relative_path}"
    file_id = hashlib.sha1(namespaced.encode()).hexdigest()
    src_rel = Backup.get_src_path(file_id)
    src_path = backup_dir / src_rel
    src_path.parent.mkdir(parents=True, exist_ok=True)
    src_path.write_bytes(content)
    return file_id, src_path


def test_get_src_path():
    assert Backup.get_src_path("abcdef1234") == "ab/abcdef1234"


def test_parse_with_metadata():
    # Prepare a binary plist as blob
    obj = {"Name": "example", "Value": 42}
    blob = plistlib.dumps(obj, fmt=plistlib.FMT_BINARY)

    content = [("id1", "AppDomain-com.example", "path/to/file", 1, blob)]
    records = list(Backup.parse(content, parse_metadata=True))

    assert len(records) == 1
    r = records[0]
    assert r.file_id == "id1"
    assert r.domain == "AppDomain"
    assert r.subdomain == "com.example"
    assert r.relative_path == "path/to/file"
    assert r.type == "file"
    assert isinstance(r.data, dict)
    assert r.data["Name"] == "example"
    assert r.data["Value"] == 42


def test__is_to_skip_true_and_false():
    # symlink case that should be skipped
    r1 = Record("id", "DatabaseDomain", None, "timezone/localtime", "symlink", None)
    assert Backup._is_to_skip(r1)

    # symlink but different path should not be skipped
    r2 = Record("id", "DatabaseDomain", None, "some/other/path", "symlink", None)
    assert not Backup._is_to_skip(r2)


def test_get_file_found_and_not_found(tmp_path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    domain = "MyDomain"
    rel_path = "folder/config.plist"

    file_id_, src_path_ = create_src_file(backup_dir, domain, rel_path, b"data")

    b = Backup(str(backup_dir))

    try:
        found = b.get_file(domain, rel_path)
        assert found.exists()
        assert found.read_bytes() == b"data"

        # non-existent file should raise
        missing_backup = Backup(str(tmp_path / "empty_backup"))
        (tmp_path / "empty_backup").mkdir()

        import pytest
        with pytest.raises(FileNotFoundError):
            missing_backup.get_file(domain, rel_path)
    finally:
        missing_backup.close()

    b.close()


def test__read_plist_and_cached_properties(tmp_path):
    backup_dir = tmp_path / "backup_plists"
    backup_dir.mkdir()

    info = {"DeviceName": "iPhone"}
    manifest = {"Version": 1}
    status = {"Status": "ok"}

    with (backup_dir / "Info.plist").open("wb") as f:
        plistlib.dump(info, f)
    with (backup_dir / "Manifest.plist").open("wb") as f:
        plistlib.dump(manifest, f)
    with (backup_dir / "Status.plist").open("wb") as f:
        plistlib.dump(status, f)

    b = Backup(str(backup_dir))

    # Access properties and ensure values are loaded
    assert b.info["DeviceName"] == "iPhone"
    assert b.manifest["Version"] == 1
    assert b.status["Status"] == "ok"

    # Cached properties: change file on disk and ensure property doesn't change
    with (backup_dir / "Info.plist").open("wb") as f:
        plistlib.dump({"DeviceName": "Changed"}, f)
    assert b.info["DeviceName"] == "iPhone"

    b.close()


def test_export_file_copy_and_ignore_missing(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backup_export"
    backup_dir.mkdir()

    out_dir = tmp_path / "out"

    domain = "ExportDomain"
    subdomain = "sub"
    rel_path = "docs/readme.txt"

    file_id, src_path = create_src_file(backup_dir, domain, rel_path, b"exported")

    # Ensure Path.copy exists by monkeypatching it to use shutil.copy
    from pathlib import Path as _Path

    def _copy(self, dest):
        shutil.copy(self, dest)

    monkeypatch.setattr(_Path, "copy", _copy, raising=False)

    # Build Record and run export
    record = Record(file_id, domain, subdomain, rel_path, "file", None)
    b = Backup(str(backup_dir))

    b.export([record], str(out_dir), ignore_missing=False)

    dest = out_dir / domain / subdomain / rel_path
    assert dest.exists()
    assert dest.read_bytes() == b"exported"

    # Now test behavior when file is missing and ignore_missing=True
    missing_id = hashlib.sha1(f"{domain}-missing.txt".encode()).hexdigest()
    missing_record = Record(missing_id, domain, subdomain, "missing.txt", "file", None)

    # Should not raise when ignore_missing=True
    b.export([missing_record], str(out_dir), ignore_missing=True)

    b.close()
