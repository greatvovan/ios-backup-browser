from ios_backup import Backup


backup_path = 'tests/.data/backup_2/c577c025f51ed9e1db9b539dc23577e8861acc72'
backup = Backup(backup_path)
db = backup.db

# Export all videos.
query = """
    select * from Files
    where domain = 'CameraRollDomain' and relativePath like 'Media/DCIM/%.MOV'
"""

content = Backup.parse(db.buffered_query(query), parse_metadata=True)
backup.export(content, 'tests/.data/exported_videos', restore_modified_dates=True)
