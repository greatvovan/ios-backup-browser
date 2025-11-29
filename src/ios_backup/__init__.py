from .backup import Backup, Record
from .db import BackupDB

try:
    from ._version import __version__
except (ImportError, ModuleNotFoundError) as e:
    __version__ = "0.0.0_undefined"

__all__ = ["Backup", "Record", "BackupDB", "__version__"]
