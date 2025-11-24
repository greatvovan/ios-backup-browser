# iOS backup browser and exporter

This module allows you to esilly access non-encrypted iOS backups from your Python scripts or export the backup to your computer for easy browsing of its content. The module has command-line interface for basic use cases and API
for more advanced use cases. The module is pure Python and has no dependencies.

Backups are the only official way to obtain file system content as it is seen
by applications. While there are applications allowing "live" browsing of iOS
content, they use Apple's private API that can be discontinued at any point.

## Basic usage

### Installation

`% pip install ios-backup-browser`  
`% python -m ios_backup --version`  
`% python -m ios_backup --help`  

Syntax:

```bash
python -m ios_backup export \
  --backup-path <iosbackup/path> \
  --output-path <export/path> \
  [--domain <domain>] \
  [--namespace <namespace>] \
  [--path <device/path>] \
  [--restore-modified-dates]
  [--ignore-missing]
```


### Export entire backup

```bash
% python -m ios_backup export \
  --backup-path iosbackup/path \
  --output-path export/path \
  --restore-dates
```

### Filtering

Each file in an iOS backup has the following attributes:

- Domain: Apple's term to associate content with a certain category,
for example, `AppDomain`, `CameraRollDomain`.
- Namespace: a level of hierarchy under the domain. For example, content of
applications will live in `AppDomain` will have namespaces such as `com.mojang.minecraftpe` or `com.apple.iBooks`.
- Relative path: path in the application's directory.

When exporting the backup, these attributes form a directory tree with layers in the above order, for example, `AppDomain/com.mojang.minecraftpe/Documents/games/com.mojang/Screenshots`.

If you need to export only specific content, you can achive that with filtering keys:

`% ... --domain AppDomain --namespace com.mojang.minecraftpe --path Documents/games/com.mojang/minecraftWorlds`

All values are interpreted as prefixes, full match is not required.

### Other options
`--ignore-missing` – do not fail on missing files (those defined in the
database, but not present in the backup). Useful for incomplete or corrupted backups.

`--restore-dates` – restore dates and times of files as they were on
the original device. 

## Advanced usage

### Custom filtering logic

The below example shows how to use a custom query to process backup content.

Create Backup object and obtain the DB:

```python
from ios_backup import Backup

backup_path = 'path/to/backup/location'
backup = Backup(backup_path)
db = backup.db
```

Export content based on a specific query:

```python
# Export all videos.
query = """
    select * from Files
    where domain = 'CameraRollDomain' and relativePath like 'Media/DCIM/%.MOV'
"""

content = Backup.parse(db.buffered_query(query), parse_metadata=True)
backup.export(content, 'tests/.data/exported_videos', restore_modified_dates=True)
```

Process specific files based on query:

```python
# Process all iMessage attachments.
query = """
    select * from Files
    where domain = 'MediaDomain'
      and relativePath like 'Library/SMS/Attachments/%'
      and (relativePath like '%.jpg'
        or relativePath like '%.jpeg'
        or relativePath like '%.heic'
        or relativePath like '%.png'
        or relativePath like '%.gif'
        or relativePath like '%.tiff'
        or relativePath like '%.psd'
        or relativePath like '%.mov')
"""
rows = db.buffered_query(query)

for record in Backup.parse(rows):
    file = backup.base_path / record.content_path

    # Copy or process the file as needed.
    file.copy('destination/directory')

    with file.open('rb') as f:
        data = f.read()
        # Do something with the data.
```

## Relation to `unback()` iOS function

Unback function was broken by Apple at around version 10 of iOS, and hence
[libimobiledevice](https://github.com/libimobiledevice/libimobiledevice)
project (such as `idevicebackup2 unback`)
[stopped working](https://github.com/libimobiledevice/libimobiledevice/issues/1439) on most backups.
While this module does not provide 100% equivalemnt of `unback()`'s output,
it does honest export of entire backup content, and will work for cases
when you need to browse the content or simply extract photos, videos, or other
applications' files.
