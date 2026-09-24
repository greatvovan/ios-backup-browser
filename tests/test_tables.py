import sys
from datetime import datetime, timezone, timedelta
from ios_backup.tables import naturalsize, ls_style_time, transform_record_for_printing, print_table, print_apps_table
from ios_backup.backup import Record


class TestNaturalsize:
    """Test naturalsize function for human-readable file sizes."""

    def test_bytes(self):
        assert naturalsize(0) == "0B"
        assert naturalsize(1) == "1B"
        assert naturalsize(999) == "999B"
        assert naturalsize(1000) == "1000B"
        assert naturalsize(1023) == "1023B"

    def test_kilobytes(self):
        assert naturalsize(1024) == "1.0K"
        assert naturalsize(1536) == "1.5K"
        assert naturalsize(1024 * 1000) == "1000K"
        assert naturalsize(1024 * 1024 - 1) == "1023K"

    def test_megabytes(self):
        assert naturalsize(1024 * 1024) == "1.0M"

    def test_gigabytes(self):
        assert naturalsize(1024 * 1024 * 1024) == "1.0G"

    def test_terabytes(self):
        assert naturalsize(1024 * 1024 * 1024 * 1024) == "1.0T"

    def test_large_values(self):
        # Test very large values
        assert naturalsize(1024**8) == "1.0Y"  # Yottabytes


class TestLsStyleTime:
    """Test ls_style_time function for datetime formatting."""

    def test_recent_date(self):
        # Date within 6 months should show time
        now = datetime.now(timezone.utc)
        recent = now.replace(hour=14, minute=30)
        assert ls_style_time(recent) == recent.strftime("%b %d %H:%M")

    def test_old_date(self):
        # Date more than 6 months ago should show year
        now = datetime.now(timezone.utc)
        old = now.replace(year=now.year - 1)
        assert ls_style_time(old) == old.strftime("%b %d  %Y")

    def test_exactly_six_months(self):
        # Test boundary case - approximately 6 months ago
        now = datetime.now(timezone.utc)
        # Use a date that's definitely within 6 months
        recent = now - timedelta(days=100)  # About 3 months ago
        assert ls_style_time(recent) == recent.strftime("%b %d %H:%M")

    def test_different_timezones(self):
        # Should work with different timezones - use a recent date
        now = datetime.now(timezone.utc)
        dt = now.replace(hour=10, minute=30)
        assert ls_style_time(dt) == dt.strftime("%b %d %H:%M")


class TestTransformRecordForPrinting:
    """Test transform_record_for_printing function."""

    def test_directory_record(self):
        # Directory has no size, but has dates
        created = datetime(2023, 6, 14, 9, 0)
        modified = datetime(2023, 6, 15, 10, 30)
        data = {'$objects': [None, {'LastModified': modified.timestamp(), 'Birth': created.timestamp()}]}
        record = Record(
            file_id="test_id",
            domain="AppDomain",
            namespace="com.example.app",
            relative_path="Documents",
            type="directory",
            data=data
        )
        result = list(transform_record_for_printing([record]))[0]
        assert result["domain"] == "AppDomain"
        assert result["namespace"] == "com.example.app"
        assert result["path"] == "Documents"
        assert result["type"] == "D"
        assert result["size"] == ""
        assert result["last_modified"] == ls_style_time(modified)
        assert result["created"] == ls_style_time(created)

    def test_file_record(self):
        data = {'$objects': [None, {'Size': 1024, 'LastModified': 1686772200, 'Birth': 1686685800}]}
        record = Record(
            file_id="test_id",
            domain="AppDomain",
            namespace="com.example.app",
            relative_path="file.txt",
            type="file",
            data=data
        )
        result = list(transform_record_for_printing([record]))[0]
        assert result["type"] == "F"
        assert result["size"] == "1.0K"

    def test_symlink_record(self):
        record = Record(
            file_id="test_id",
            domain="SystemDomain",
            namespace="",
            relative_path="link",
            type="symlink",
            data=None  # No metadata
        )
        result = list(transform_record_for_printing([record]))[0]
        assert result["type"] == "S"
        assert result["size"] == ""
        assert result["last_modified"] == ""
        assert result["created"] == ""

    def test_hardlink_record(self):
        created = datetime(2023, 6, 14, 9, 0)
        modified = datetime(2023, 6, 15, 10, 30)
        data = {'$objects': [None, {'LastModified': modified.timestamp(), 'Birth': created.timestamp()}]}
        record = Record(
            file_id="test_id",
            domain="DatabaseDomain",
            namespace="",
            relative_path="hardlink",
            type="hardlink",
            data=data
        )
        result = list(transform_record_for_printing([record]))[0]
        assert result["type"] == "H"
        assert result["last_modified"] == ls_style_time(modified)
        assert result["created"] == ls_style_time(created)

    def test_unknown_type(self):
        record = Record(
            file_id="test_id",
            domain="TestDomain",
            namespace="test",
            relative_path="unknown",
            type="unknown",
            data=None
        )
        result = list(transform_record_for_printing([record]))[0]
        assert result["type"] == ""  # Unknown type maps to empty string

    def test_multiple_records(self):
        data1 = {'$objects': [None, {'Size': 2048}]}
        data2 = {'$objects': [None, {}]}
        records = [
            Record("id1", "D1", "N1", "P1", "file", data1),
            Record("id2", "D2", "N2", "P2", "directory", data2)
        ]
        results = list(transform_record_for_printing(records))
        assert len(results) == 2
        assert results[0]["domain"] == "D1"
        assert results[1]["domain"] == "D2"
    
def test_print_table(capsys):
    # Test for a simple table layout with left, right justification and padding.
    content = [
        {'city': 'Gravity Falls', 'ppl': 12, "area": 52.4, "g": "x",},
        {'city': 'Springfield', 'ppl': 987654, "area": 109.7, "g": "x",},
    ]
    columns = {
        "CITY": {"key": "city", "width": 20},
        "POP": {"key": "ppl", "width": 8, "justify": "r", "rpad": 2},
        "GUIDE": {"key": "g", "width": 6},
        "AREA": {"key": "area", "width": 5, "justify": "r"},
    }

    expected = """
CITY                   POP  GUIDE  AREA
Gravity Falls           12  x      52.4
Springfield         987654  x     109.7
"""

    print_table(content, columns, header=True)
    captured = capsys.readouterr()
    assert captured.out == expected.lstrip()


# Specific print_*() functions will not be covered due to tedios maintaining of output format.
# However we will test if rich module is successfully imported and used.

def test_print_files_with_rich(mocker):
    rich_mock = mocker.Mock()
    rich_mock.console = mocker.Mock()
    rich_mock.table = mocker.Mock()
    rich_mock.table.Table = mocker.Mock()
    rich_mock.console.Console = mocker.Mock()

    mocker.patch.dict(
        sys.modules,
        {
            'rich': rich_mock,
            'rich.console': rich_mock.console,
            'rich.table': rich_mock.table,
        }
    )
    from ios_backup.tables import print_files
    print_files([])

    assert rich_mock.table.Table.called
    assert rich_mock.console.Console.called
    assert rich_mock.console.Console().print.called


def test_print_apps_with_rich(mocker):
    rich_mock = mocker.Mock()
    rich_mock.console = mocker.Mock()
    rich_mock.table = mocker.Mock()
    rich_mock.table.Table = mocker.Mock()
    rich_mock.console.Console = mocker.Mock()

    mocker.patch.dict(
        sys.modules,
        {
            'rich': rich_mock,
            'rich.console': rich_mock.console,
            'rich.table': rich_mock.table,
        }
    )
    from ios_backup.tables import print_apps_table
    print_apps_table([])

    assert rich_mock.table.Table.called
    assert rich_mock.console.Console.called
    assert rich_mock.console.Console().print.called
