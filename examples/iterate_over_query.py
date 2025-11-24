from ios_backup import Backup


backup_path = 'path/to/backup/location'
backup = Backup(backup_path)
db = backup.db

# Process all iMessage attachments.
query = """
    select * from Files
    where domain = 'MediaDomain' and relativePath like 'Library/SMS/Attachments/%'
      and (relativePath like '%.jpg'
        or relativePath like '%.jpeg'
        or relativePath like '%.heic'
        or relativePath like '%.png'
        or relativePath like '%.gif'
        or relativePath like '%.tiff'
        or relativePath like '%.psd'
        or relativePath like '%.mov')
"""
db.simple_query('PRAGMA case_sensitive_like = false')
rows = db.buffered_query(query)

for record in Backup.parse(rows):
    file = backup.base_path / record.content_path

    # Copy or process the file as needed.
    file.copy('destination/directory')

    with file.open('rb') as f:
        data = f.read()
        # Do something with the data.
