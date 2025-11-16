import os
import logging
import plistlib
import hashlib
from typing import Iterable
from functools import cache, cached_property
from dataclasses import dataclass
from pathlib import Path

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
    subdomain: str | None
    relative_path: str
    type: str
    data: dict | bytes | None

    @property
    def content_path(self) -> str:
        """Get the content path in the backup for this record."""
        return Backup.get_src_path(self.file_id)


class Backup:
    def __init__(self, backup_path: str):
        self.backup_path = Path(backup_path)
        self._db: BackupDB | None = None
    
    @property
    def db(self) -> BackupDB:
        if self._db is None:
            self._db = BackupDB(f"{self.backup_path}/Manifest.db")
        return self._db
    
    @cache
    def all_domains(self) -> list[str]:
        """Fetch all distinct domains from the backup."""
        return self.db.get_all_domains()
    
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

    def get_content(self, domain_prefix: str = "", namespace_prefix: str = "",
                    path_prefix: str = "", parse_metadata: bool = False) -> Iterable[Record]:
        """Fetch content records based on filters."""

        content = self.db.get_content(domain_prefix, namespace_prefix, path_prefix)
        return self.parse(content, parse_metadata)

    @cache
    def get_content_count(self, domain_prefix: str = "", namespace_prefix: str = "",
                          path_prefix: str = "") -> int:
        """Count content records based on filters."""
        
        return self.db.get_content_count(domain_prefix, namespace_prefix, path_prefix)
    
    def export(self, content: Iterable[Record], path: str,
               ignore_missing: bool = False, restore_modified_dates: bool = False,
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

        for record in content:
            dest_path = export_path / record.domain / record.subdomain / record.relative_path

            if self._is_to_skip(record):
                continue

            if record.type == "directory":
                dest_path.mkdir(parents=True, exist_ok=True)

            elif record.type in ("file", "symlink"):
                src_path = Path(self.backup_path) / self.get_src_path(record.file_id)
                if not src_path.exists():
                    if ignore_missing:
                        continue
                    else:
                        raise FileNotFoundError(f"Source file not found: {src_path}")
                
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                if record.type == "file":
                    src_path.copy(dest_path)
                elif record.type == "symlink":
                    link_target = src_path.read_text()
                    dest_path.symlink_to(link_target)
            
            if restore_modified_dates:
                try:
                    mtime = record.data["$objects"][1]["LastModified"]
                    os.utime(dest_path, (mtime, mtime))
                except Exception:
                    logging.warning(f"Failed to restore modified date for {dest_path}")
    
    @staticmethod
    def get_src_path(file_id: str) -> str:
        """Get the source path in the backup for the given file ID."""
        return f"{file_id[0:2]}/{file_id}"
    
    @staticmethod
    def _is_to_skip(record: Record) -> bool:
        """To skip some known misses."""
        if record.type == "symlink" and record.relative_path == "Library/WebKit/WebsiteData/IndexedDB/v0":
            return True
        if record.type == "symlink" and record.relative_path == "timezone/localtime" and record.domain == "DatabaseDomain":
            return True
        return False
    
    def _read_plist(self, sub_path) -> dict:
        """Read and return a plist file from the backup."""
        plist_path = self.backup_path / sub_path
        with plist_path.open("rb") as f:
            return plistlib.load(f)
    
    @cached_property
    def info(self) -> dict:
        """Lazy load and return the Info.plist content."""
        return self._read_plist("Info.plist")

    @cached_property
    def manifest(self) -> dict:
        """Lazy load and return the Manifest.plist content."""
        return self._read_plist("Manifest.plist")

    @cached_property
    def status(self) -> dict:
        """Lazy load and return the Status.plist content."""
        return self._read_plist("Status.plist")

    def close(self):
        """Close the database connection."""
        if self._db:
            self._db.close()

    def get_file(self, domain: str, relative_path: str) -> Path:
        """
        Get pathlib.Path object for a specific file in the backup.
        Useful if you know exact domain and relative path.
        This method bypasses the manifest database,
        hence will work with corrupted or incomplete backups.
        """
        namespaced_path = f"{domain}-{relative_path}"
        file_id = hashlib.sha1(namespaced_path.encode()).hexdigest()
        source_path = self.backup_path / self.get_src_path(file_id)

        if not source_path.exists():
            raise FileNotFoundError(f"File not found in backup: {domain}/{relative_path}")
        
        return source_path
