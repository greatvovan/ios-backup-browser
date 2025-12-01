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
  [--restore-dates]
  [--restore-symlinks]
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

`--restore-symlinks` – restore symbolic links from backup. This has questionable
value, as links will point to non-existent locations on your system, but may be
useful for research purposes.

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
backup.export(content, 'path/to/exported_videos', restore_modified_dates=True)
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

## Progress bar

Export usually runs quite fast on SSD storage, but may take longer on HDDs.
To get a sense of progress, you can install [tqdm](https://github.com/tqdm/tqdm) module. If tqdm is found in the executing Python environment and if `total_count` is provided to `Backup.export()` (true for CLI use), it will be
used to produce a progress bar in the terminal interface.

## Relation to `unback()` iOS function

Unback function was broken by Apple at around version 10 of iOS, and hence
some functions of
[libimobiledevice](https://github.com/libimobiledevice/libimobiledevice)
project (such as `idevicebackup2 unback`)
[stopped working](https://github.com/libimobiledevice/libimobiledevice/issues/1439) on most backups.
While this module does not provide 100% equivalemnt of `unback()`'s output,
it does an honest export of entire backup content and will suit for cases
when you need to browse the content or simply extract photos, videos, or other
applications' files.

## Creating backups

### MacOS
- Connect device with a USB cable.
- If connecting first time, click "Allow" in the pop-up window, tap "Trust" on the device and enter your passcode.
- Open Finder and select your device on the side panel.
- Click "Back Up Now" on "General" tab.
- Click on the option to **not** encrypt the backup as the module does not support encrypted backups.

### Windows
- Download and install the Apple Devices app from the Microsoft Store.
- Connect your device to your PC with a USB or USB-C cable.
- If prompted, tap "Trust" on your device and enter your passcode.
- Open the Apple Devices app and select your device from the sidebar.
- Click "Backup" in the "Backups" section.
- Do not select the option for encryption as the module does not support encrypted backups.
- Click "Back Up Now".

### Linux/Unix/MacOS/*
- Install [libimobiledevice](https://libimobiledevice.org/) libraries according to the project's instructions.
- Connect the device with a USB cable.
- Run `idevicebackup2 backup --full /path/to/your/backup/folder`
- Tap "Trust" on the device and enter passcode when prompted.

* Libraries are cross-platform, although on MacOS and Windows there are more user-friendly options.
