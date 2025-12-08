import os
import logging
import plistlib
import hashlib
from typing import Iterable, ClassVar
from datetime import datetime
from functools import cache, cached_property
from dataclasses import dataclass
from pathlib import Path
from .metadata import Info, Status, Manifest
from .db import BackupDB

_FLAG_MAP = {
    1: "file",
    2: "directory",
    4: "symlink",
    10: "hardlink",
}

@dataclass
class Record:
    file_id: str
    domain: str
    namespace: str | None
    relative_path: str
    type: str
    data: dict | bytes | None

    _obj_stub: ClassVar[list] = [None, {}]

    @property
    def content_path(self) -> str:
        """Get the content path in the backup for this record."""
        return Backup.get_src_path(self.file_id)
    
    @property
    def size(self) -> int | None:
        """Get the size of the file from metadata, if available."""
        if isinstance(self.data, dict):
            return self.data.get('$objects', self._obj_stub)[1].get("Size")
        return None

    @property
    def mtime(self) -> int | None:
        """Get the mtime of the file from metadata, if available."""
        if isinstance(self.data, dict):
            unix_ts = self.data.get('$objects', self._obj_stub)[1].get("LastModified")
            return unix_ts
        return None

    @property
    def ctime(self) -> int | None:
        """Get the ctime of the file from metadata, if available."""
        if isinstance(self.data, dict):
            unix_ts = self.data.get('$objects', self._obj_stub)[1].get("LastModified")
            return unix_ts
        return None

    @property
    def last_modified(self) -> datetime | None:
        """Get the modified time of the file from metadata, if available."""
        unix_ts = self.mtime
        if unix_ts:
            return datetime.fromtimestamp(unix_ts)
        return None
    
    @property
    def created(self) -> datetime | None:
        """Get the created time of the file from metadata, if available."""
        unix_ts = self.ctime
        if unix_ts:
            return datetime.fromtimestamp(unix_ts)
        return None

    @property
    def symlink_target(self) -> str | None:
        """Get the symlink target path, if this record is a symlink."""
        if isinstance(self.data, dict):
            objects = self.data.get('$objects')
            if isinstance(objects, list) and len(objects) > 1:
                index = objects[1].get('Target')
                if isinstance(index, plistlib.UID):
                    return objects[index.data]
        return None


class Backup:
    def __init__(self, backup_path: str):
        self.base_path = Path(backup_path)
        self._db: BackupDB | None = None
    
    @property
    def db(self) -> BackupDB:
        if self._db is None:
            self._db = BackupDB(f"{self.base_path}/Manifest.db")
        return self._db
    
    @cache
    def all_domains(self) -> list[str]:
        """Fetch all distinct domains from the backup."""
        return self.db.get_all_domains()
    
    def namespaces(self, domain: str) -> list[str]:
        """Fetch all distinct namespaces for a given domain."""
        return self.db.get_namespaces(domain)
    
    @staticmethod
    def parse(content: Iterable[tuple], parse_metadata: bool = False) -> Iterable[Record]:
        for id_, domain, path, flag, data in content:
            if "-" in domain:
                domain, sub = domain.split("-", 1)  # TODO: handle multiple "-"
            else:
                domain, sub = domain, ""

            if parse_metadata and data:
                try:
                    data = plistlib.loads(data, fmt=plistlib.FMT_BINARY)
                except Exception:
                    data = {}

            yield Record(id_, domain, sub, path, _FLAG_MAP[flag], data)

    def get_content(self, domain: str = "", namespace: str = "",
                    path: str = "", like_syntax: bool = False,
                    parse_metadata: bool = False) -> Iterable[Record]:
        """Fetch content records based on filters."""

        content = self.db.get_content(domain, namespace, path, like_syntax)
        return self.parse(content, parse_metadata)

    @cache
    def get_content_count(self, domain: str = "", namespace: str = "",
                          path: str = "", like_syntax: bool = False) -> int:
        """Count content records based on filters."""
        
        return self.db.get_content_count(domain, namespace, path, like_syntax)
    
    def export(self, content: Iterable[Record], path: str,
               ignore_missing: bool = False, restore_modified_dates: bool = False,
               restore_symlinks: bool = False,
               total_count: int | None = None) -> None:
        """Export the given content records to the specified path."""
        export_path = Path(path)
        export_path.mkdir(parents=True, exist_ok=True)

        if total_count:
            try:
                from tqdm import tqdm
                content = tqdm(content, total=total_count, desc="Exporting files")
            except ImportError:
                pass

        directories_created = []

        for record in content:
            dest_path = export_path / record.domain / record.namespace / record.relative_path

            if record.type == "directory":
                dest_path.mkdir(parents=True, exist_ok=True)

            elif record.type == "file":
                src_path = Path(self.base_path) / self.get_src_path(record.file_id)
                if not src_path.exists():
                    if ignore_missing:
                        continue
                    else:
                        raise FileNotFoundError(f"Source file not found: {src_path}")
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                src_path.copy(dest_path)
            
            elif record.type == "symlink" and restore_symlinks:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.symlink_to(record.symlink_target)
            
            if restore_modified_dates:
                try:
                    mtime = record.mtime
                    if record.type == "directory":
                        # Postpone setting directory mtime until all files are created.
                        directories_created.append((dest_path, mtime))
                    else:
                        os.utime(dest_path, (mtime, mtime), follow_symlinks=False)
                except Exception:
                    logging.warning(f"Failed to restore modified date for {dest_path}")
        
        try:
            if directories_created:
                directories_created = tqdm(directories_created, desc="Restoring directory dates")
        except NameError:
            pass

        # Resume restoring directory modified dates.
        for dir_path, mtime in directories_created:
            try:
                os.utime(dir_path, (mtime, mtime))
            except Exception:
                logging.warning(f"Failed to restore modified date for directory {dir_path}")
    
    @staticmethod
    def get_src_path(file_id: str) -> str:
        """Get the source path in the backup for the given file ID."""
        return f"{file_id[0:2]}/{file_id}"
    
    def _read_plist(self, sub_path) -> dict:
        """
        Read and return a plist file from the backup.
        The library auto-detects the format (XML or binary).
        """
        plist_path = self.base_path / sub_path
        with plist_path.open("rb") as f:
            return plistlib.load(f)
    
    @cached_property
    def info(self) -> Info:
        """Lazy load and return the Info metadata."""
        return Info(self.base_path)

    @cached_property
    def manifest(self) -> dict:
        """Lazy load and return the Manifest.plist content."""
        return Manifest(self.base_path)

    @cached_property
    def status(self) -> Status:
        """Lazy load and return the Status.plist content."""
        return Status(self.base_path)

    def close(self):
        """Close the database connection."""
        if self._db:
            self._db.close()

    def get_file_by_id(self, file_id: str) -> Path:
        """
        Get pathlib.Path object for a specific file in the backup by its file ID.
        This method bypasses the manifest database,
        hence will work with corrupted or incomplete backups.
        """
        source_path = self.base_path / self.get_src_path(file_id)

        if not source_path.exists():
            raise FileNotFoundError(f"File not found in backup: {file_id}")
        
        return source_path
    
    def get_file_by_path(self, domain: str, relative_path: str) -> Path:
        """
        Get pathlib.Path object for a specific file in the backup.
        Useful if you know exact domain and relative path.
        This method bypasses the manifest database,
        hence will work with corrupted or incomplete backups.
        """
        namespaced_path = f"{domain}-{relative_path}"
        file_id = hashlib.sha1(namespaced_path.encode()).hexdigest()

        return self.get_file_by_id(file_id)
