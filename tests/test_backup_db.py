import os
import pytest
import sqlite3
from ios_backup.db import BackupDB

# Test data setup
SAMPLE_DATA = [
    ('file1', 'AppDomain-com.example.app', 'docs/file1.txt', 1, b'data1'),
    ('file2', 'AppDomain-com.example.app', 'docs/file2.txt', 1, b'data2'),
    ('file3', 'MediaDomain', 'photos/photo1.jpg', 1, b'data3'),
    ('file4', 'HomeDomain-settings', 'config.plist', 1, b'data4'),
]

@pytest.fixture
def sample_db(tmp_path):
    """Create a temporary SQLite database with sample data."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create Files table with schema matching iOS backup DB
    cursor.execute("""
        CREATE TABLE Files (
            fileID TEXT,
            domain TEXT,
            relativePath TEXT,
            flags INTEGER,
            file BLOB
        )
    """)
    
    # Insert sample data
    cursor.executemany(
        "INSERT INTO Files (fileID, domain, relativePath, flags, file) VALUES (?, ?, ?, ?, ?)",
        SAMPLE_DATA
    )
    conn.commit()
    conn.close()
    return db_path

class TestBackupDB:
    def test_init_with_valid_path(self, sample_db):
        """Test BackupDB initialization with valid database path."""
        db = BackupDB(sample_db)
        assert isinstance(db.conn, sqlite3.Connection)
        db.close()

    def test_init_with_invalid_path(self):
        """Test BackupDB initialization with invalid database path."""
        with pytest.raises(FileNotFoundError):
            BackupDB("nonexistent.db")

    def test_simple_query(self, sample_db):
        """Test simple query execution."""
        db = BackupDB(sample_db)
        results = db.simple_query("SELECT * FROM Files ORDER BY fileID")
        assert isinstance(results, list)
        assert len(results) == len(SAMPLE_DATA)
        assert results[0][0] == 'file1'  # Check first record
        assert results[-1][0] == 'file4'  # Check last record
        db.close()

    def test_buffered_query(self, sample_db):
        """Test buffered query execution with small buffer size."""
        db = BackupDB(sample_db)
        query = "SELECT * FROM Files ORDER BY fileID"
        results = list(db.buffered_query(query, buffer_size=2))
        assert len(results) == len(SAMPLE_DATA)
        assert results[0][0] == 'file1'  # Check first record
        assert results[-1][0] == 'file4'  # Check last record
        db.close()

    def test_get_content_no_filters(self, sample_db):
        """Test get_content with no filters returns all records."""
        db = BackupDB(sample_db)
        results = list(db.get_content())
        assert len(results) == len(SAMPLE_DATA)
        db.close()

    def test_get_content_with_domain(self, sample_db):
        """Test get_content with domain filter."""
        db = BackupDB(sample_db)
        results = list(db.get_content(domain='AppDomain'))
        assert len(results) == 2  # Should return 2 AppDomain records
        assert all('AppDomain' in row[1] for row in results)  # Check domain field
        db.close()

    def test_get_content_with_namespace(self, sample_db):
        """Test get_content with namespace filter."""
        db = BackupDB(sample_db)
        results = list(db.get_content(domain='AppDomain', namespace='com.example'))
        assert len(results) == 2
        assert all('com.example' in row[1] for row in results)
        db.close()

    def test_get_content_with_path(self, sample_db):
        """Test get_content with path filter."""
        db = BackupDB(sample_db)
        results = list(db.get_content(path='docs/'))
        assert len(results) == 2
        assert all(row[2].startswith('docs/') for row in results)
        db.close()

    def test_get_content_count(self, sample_db):
        """Test get_content_count with various filters."""
        db = BackupDB(sample_db)
        
        # Test total count
        assert db.get_content_count() == len(SAMPLE_DATA)
        
        # Test count with domain filter
        assert db.get_content_count(domain='AppDomain') == 2
        
        # Test count with domain and path filters
        assert db.get_content_count(domain='AppDomain', path='docs/') == 2
        
        db.close()

    def test_get_all_domains(self, sample_db):
        """Test get_all_domains returns distinct domains."""
        db = BackupDB(sample_db)
        domains = db.get_all_domains()
        
        # Expected unique domains (without namespace part)
        expected_domains = {'AppDomain', 'MediaDomain', 'HomeDomain'}
        assert set(domains) == expected_domains
        db.close()

    def test_close_connection(self, sample_db):
        """Test database connection is properly closed."""
        db = BackupDB(sample_db)
        db.close()
        # Verify connection is closed by attempting a query
        with pytest.raises(sqlite3.ProgrammingError):
            db.conn.execute("SELECT 1")

    def test_context_isolation(self, sample_db):
        """Test that queries are isolated and don't affect other connections."""
        db1 = BackupDB(sample_db)
        db2 = BackupDB(sample_db)
        
        # Perform query with db1
        list(db1.get_content(domain='AppDomain'))
        
        # Verify db2 can still perform queries
        results = list(db2.get_content())
        assert len(results) == len(SAMPLE_DATA)
        
        db1.close()
        db2.close()

    def test_get_namespaces_returns_distinct_only(self, sample_db):
        """Test get_namespaces returns only distinct namespaces for a given domain."""
        db = BackupDB(sample_db)
        
        # Get namespaces for AppDomain (which has 'com.example.app' namespace in sample data)
        namespaces = db.get_namespaces('AppDomain')
        assert len(namespaces) == 1
        assert 'com.example.app' in namespaces
        
        # Get namespaces for HomeDomain (which has 'settings' namespace)
        namespaces = db.get_namespaces('HomeDomain')
        assert len(namespaces) == 1
        assert 'settings' in namespaces
        
        db.close()

    def test_get_namespaces_with_duplicate_entries(self, sample_db, tmp_path):
        """Test get_namespaces returns distinct namespaces even with duplicate entries."""
        # Create a database with duplicate namespace entries
        db_path = str(tmp_path / "test_duplicates.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE Files (
                fileID TEXT,
                domain TEXT,
                relativePath TEXT,
                flags INTEGER,
                file BLOB
            )
        """)
        
        # Insert multiple records with same domain-namespace but different paths
        cursor.executemany(
            "INSERT INTO Files (fileID, domain, relativePath, flags, file) VALUES (?, ?, ?, ?, ?)",
            [
                ('file1', 'TestDomain-namespace1', 'path1', 1, b'data1'),
                ('file2', 'TestDomain-namespace1', 'path2', 1, b'data2'),
                ('file3', 'TestDomain-namespace1', 'path3', 1, b'data3'),
                ('file4', 'TestDomain-namespace2', 'path4', 1, b'data4'),
                ('file5', 'TestDomain-namespace2', 'path5', 1, b'data5'),
            ]
        )
        conn.commit()
        conn.close()
        
        db = BackupDB(db_path)
        namespaces = db.get_namespaces('TestDomain')
        
        # Should return only 2 distinct namespaces despite multiple files per namespace
        assert len(namespaces) == 2
        assert set(namespaces) == {'namespace1', 'namespace2'}
        
        db.close()

    def test_get_namespaces_empty_result(self, sample_db):
        """Test get_namespaces returns empty list for domain with no namespaces."""
        db = BackupDB(sample_db)
        
        # MediaDomain has no namespace (no '-' in domain)
        namespaces = db.get_namespaces('MediaDomain')
        assert len(namespaces) == 0
        
        db.close()
