from pathlib import Path
from unittest.mock import MagicMock

from ios_backup.__main__ import build_parser, handle_export, export


def test_cli_export(monkeypatch, tmp_path):
    """Ensure values parsed by build_parser() are passed to export().

    This test parses a realistic `export` command line then replaces the real
    `export` function with a fake that captures the arguments it receives.
    The test asserts the captured parameters match the CLI values.
    """

    captured = {}

    def mock_export(backup_path, output_path,
                    domain, namespace, path, like_syntax,
                    ignore_missing=True, restore_modified_dates=False, restore_symlinks=False):
        captured['backup_path'] = backup_path
        captured['output_path'] = output_path
        captured['domain'] = domain
        captured['namespace'] = namespace
        captured['path'] = path
        captured['like_syntax'] = like_syntax
        captured['ignore_missing'] = ignore_missing
        captured['restore_modified_dates'] = restore_modified_dates
        captured['restore_symlinks'] = restore_symlinks

    # Monkeypatch the export() function in the cli module so we can inspect the call.
    monkeypatch.setattr('ios_backup.__main__.export', mock_export)

    parser = build_parser()

    argv = [
        'export',
        str(tmp_path / 'some_backup'),
        str(tmp_path / 'out'),
        '--domain', 'AppDomain',
        '--namespace', 'com.example',
        '--path', 'docs',
        '--ignore-missing',
        '--restore-dates',
        '--restore-symlinks',
    ]

    args = parser.parse_args(argv)

    # Run the handler - this should call our fake_export and populate `captured`.
    # If the handler expects different attribute names, this will raise AttributeError
    # or result in wrong values in `captured` and the assertions below will fail.
    handle_export(args)

    # Verify all parsed values were passed into export() by the handler
    assert captured['backup_path'] == str(tmp_path / 'some_backup')
    assert captured['output_path'] == str(tmp_path / 'out')
    assert captured['domain'] == 'AppDomain'
    assert captured['namespace'] == 'com.example'
    assert captured['path'] == 'docs'
    assert captured['like_syntax'] is False
    assert captured['ignore_missing'] is True
    assert captured['restore_modified_dates'] is True
    assert captured['restore_symlinks'] is True


def test_cli_inspect_info(monkeypatch, tmp_path):
    """Test inspect info command passes correct backup path."""
    from ios_backup.__main__ import handle_inspect_info

    # Mock the dependencies
    mock_backup = MagicMock()
    mock_backup.info = MagicMock()
    mock_backup.status = MagicMock()
    mock_backup.manifest = MagicMock()
    mock_backup.close = MagicMock()

    mock_backup_class = MagicMock(return_value=mock_backup)

    mock_summary = {"Device Name": "Test Device"}
    mock_get_backup_summary = MagicMock(return_value=mock_summary)
    mock_print_summary = MagicMock()

    monkeypatch.setattr('ios_backup.__main__.Backup', mock_backup_class)
    monkeypatch.setattr('ios_backup.__main__.get_backup_summary', mock_get_backup_summary)
    monkeypatch.setattr('ios_backup.__main__.print_summary', mock_print_summary)

    parser = build_parser()
    path = str(tmp_path / 'backup')
    args = parser.parse_args(['inspect', 'info', path])

    handle_inspect_info(args)

    # Verify Backup was created with correct path
    mock_backup_class.assert_called_once_with(path)

    # Verify get_backup_summary was called with backup's info/status/manifest
    mock_get_backup_summary.assert_called_once_with(
        mock_backup.info, mock_backup.status, mock_backup.manifest
    )

    # Verify print_summary was called with the summary
    mock_print_summary.assert_called_once_with(mock_summary)

    # Verify backup was closed
    mock_backup.close.assert_called_once()


def test_cli_inspect_apps(monkeypatch, tmp_path):
    """Test inspect apps command passes correct backup path."""
    from ios_backup.__main__ import handle_inspect_apps

    # Mock the dependencies
    test_data = [{"bundle_id": "test.app"}]
    mock_backup = MagicMock()
    mock_backup.info.get_apps.return_value = test_data
    mock_backup.close = MagicMock()

    mock_backup_class = MagicMock(return_value=mock_backup)

    mock_print_apps_table = MagicMock()

    monkeypatch.setattr('ios_backup.__main__.Backup', mock_backup_class)
    monkeypatch.setattr('ios_backup.__main__.print_apps_table', mock_print_apps_table)

    parser = build_parser()
    path = str(tmp_path / 'backup')
    args = parser.parse_args(['inspect', 'apps', path])

    handle_inspect_apps(args)

    # Verify Backup was created with correct path
    mock_backup_class.assert_called_once_with(path)

    # Verify get_apps was called on backup.info
    mock_backup.info.get_apps.assert_called_once()

    # Verify print_apps_table was called with the apps list
    mock_print_apps_table.assert_called_once_with(test_data)

    # Verify backup was closed
    mock_backup.close.assert_called_once()


def test_cli_inspect_domains(monkeypatch, tmp_path):
    """Test inspect domains command passes correct backup path."""
    from ios_backup.__main__ import handle_inspect_domains
    from ios_backup.tables import print_list

    # Mock the dependencies
    test_data = ["AppDomain", "MediaDomain"]
    mock_backup = MagicMock()
    mock_backup.all_domains.return_value = test_data
    mock_backup.close = MagicMock()

    mock_backup_class = MagicMock(return_value=mock_backup)

    mock_print_list = MagicMock()

    monkeypatch.setattr('ios_backup.__main__.Backup', mock_backup_class)
    monkeypatch.setattr('ios_backup.__main__.print_list', mock_print_list)

    parser = build_parser()
    path = str(tmp_path / 'backup')
    args = parser.parse_args(['inspect', 'domains', path])

    handle_inspect_domains(args)

    # Verify Backup was created with correct path
    mock_backup_class.assert_called_once_with(path)

    # Verify all_domains was called
    mock_backup.all_domains.assert_called_once()

    # Verify print_list was called with the domains
    mock_print_list.assert_called_once_with(test_data)

    # Verify backup was closed
    mock_backup.close.assert_called_once()


def test_cli_inspect_namespaces(monkeypatch, tmp_path):
    """Test inspect namespaces command passes correct domain and backup path."""
    from ios_backup.__main__ import handle_inspect_namespaces

    # Mock the dependencies
    test_data_1 = 'AppDomain'
    test_data_2 = ["com.example.app", "com.test.app"]
    mock_backup = MagicMock()
    mock_backup.namespaces.return_value = test_data_2
    mock_backup.close = MagicMock()

    mock_backup_class = MagicMock(return_value=mock_backup)

    mock_print_list = MagicMock()

    monkeypatch.setattr('ios_backup.__main__.Backup', mock_backup_class)
    monkeypatch.setattr('ios_backup.__main__.print_list', mock_print_list)

    parser = build_parser()
    path = str(tmp_path / 'backup')
    args = parser.parse_args(['inspect', 'namespaces', test_data_1, path])

    handle_inspect_namespaces(args)

    # Verify Backup was created with correct path
    mock_backup_class.assert_called_once_with(path)

    # Verify namespaces was called with correct domain
    mock_backup.namespaces.assert_called_once_with(test_data_1)

    # Verify print_list was called with the namespaces
    mock_print_list.assert_called_once_with(test_data_2)

    # Verify backup was closed
    mock_backup.close.assert_called_once()


def test_cli_inspect_files(monkeypatch, tmp_path):
    """Test inspect files command passes correct parameters to inspect_files()."""
    from ios_backup.__main__ import handle_inspect_files

    # Mock inspect_files function to capture arguments
    captured = {}
    def mock_inspect_files(backup_path, domain, namespace, path, like_syntax):
        captured['backup_path'] = backup_path
        captured['domain'] = domain
        captured['namespace'] = namespace
        captured['path'] = path
        captured['like_syntax'] = like_syntax

    monkeypatch.setattr('ios_backup.__main__.inspect_files', mock_inspect_files)

    parser = build_parser()
    args = parser.parse_args([
        'inspect', 'files',
        '--domain', 'AppDomain',
        '--namespace', 'com.example',
        '--path', 'docs',
        str(tmp_path / 'backup')
    ])

    handle_inspect_files(args)

    # Verify inspect_files was called with correct parameters
    assert captured['backup_path'] == str(tmp_path / 'backup')
    assert captured['domain'] == 'AppDomain'
    assert captured['namespace'] == 'com.example'
    assert captured['path'] == 'docs'
    assert captured['like_syntax'] is False


def test_inspect_files(monkeypatch):
    """Test inspect_files function with mocked dependencies."""
    from ios_backup.__main__ import inspect_files

    # Mock the dependencies
    mock_backup = MagicMock()
    mock_backup.get_content_count.return_value = 5  # Less than 1000, no prompt
    mock_backup.get_content.return_value = [{"file": "test"}]
    mock_backup.close = MagicMock()

    mock_backup_class = MagicMock(return_value=mock_backup)
    mock_print_files = MagicMock()

    monkeypatch.setattr('ios_backup.__main__.Backup', mock_backup_class)
    monkeypatch.setattr('ios_backup.__main__.print_files', mock_print_files)

    # Call inspect_files with test parameters
    inspect_files(
        backup_path='test_backup_path',
        domain='AppDomain',
        namespace='com.example',
        path='docs',
        like_syntax=False
    )

    # Verify Backup was created with correct path
    mock_backup_class.assert_called_once_with('test_backup_path')

    # Verify get_content_count was called with correct filters
    mock_backup.get_content_count.assert_called_once_with('AppDomain', 'com.example', 'docs', False)

    # Verify get_content was called with correct parameters
    mock_backup.get_content.assert_called_once_with(
        'AppDomain', 'com.example', 'docs', False,
        parse_metadata=True, sorting=True
    )

    # Verify print_files was called with the content
    mock_print_files.assert_called_once_with([{"file": "test"}])

    # Verify backup was closed
    mock_backup.close.assert_called_once()


def test_cli_inspect_files_with_like_syntax(monkeypatch, tmp_path):
    """Test inspect files command with like-syntax option."""
    from ios_backup.__main__ import handle_inspect_files

    # Mock inspect_files function to capture arguments
    captured = {}
    def mock_inspect_files(backup_path, domain, namespace, path, like_syntax):
        captured['backup_path'] = backup_path
        captured['domain'] = domain
        captured['namespace'] = namespace
        captured['path'] = path
        captured['like_syntax'] = like_syntax

    monkeypatch.setattr('ios_backup.__main__.inspect_files', mock_inspect_files)

    parser = build_parser()
    args = parser.parse_args([
        'inspect', 'files',
        '--domain', 'App%',
        '--like-syntax',
        str(tmp_path / 'backup')
    ])

    handle_inspect_files(args)

    # Verify inspect_files was called with correct parameters
    assert captured['backup_path'] == str(tmp_path / 'backup')
    assert captured['domain'] == 'App%'
    assert captured['namespace'] == ''
    assert captured['path'] == ''
    assert captured['like_syntax'] is True


def test_export_real_backup(tmp_path):
    """Test export function with a real backup structure and plist files."""

    export_path = tmp_path / 'exported'

    export('tests/data/sample_backup', str(export_path),
           domain='', namespace='', path='', like_syntax=False,
           ignore_missing=False, restore_modified_dates=True, restore_symlinks=True)

    # Verify that expected entries were exported.
    expected_items = [
        {
            'type': 'directory',
            'dst': 'AppDomain/com.google.Translate',
            'mtime': 1631511118,
        },
        {
            'type': 'directory',
            'dst': 'AppDomain/com.google.Translate/Documents',
            'mtime': 1634003864,
        },
        {
            'type': 'directory',
            'dst': 'AppDomain/com.google.Translate/Library',
            'mtime': 1631511122,
        },
        {
            'type': 'directory',
            'dst': 'AppDomain/com.google.Translate/Library/Preferences',
            'mtime': 1682109153,
        },
        {
            'type': 'file',
            'src': 'tests/data/sample_backup/12/12e90d5b620bbdeaaa88de34607ebf880fa708f5',
            'dst': 'AppDomain/com.google.Translate/Library/Preferences/com.google.Translate.plist',
            'mtime': 1682109153,
        },
        {
            'type': 'symlink',
            'dst': 'DatabaseDomain/timezone/localtime',
            'target': '',
            'mtime': 1687838382,
        },
    ]

    for item in expected_items:
        if item['type'] == 'directory':
            dst = export_path / item['dst']
            assert dst.exists() and dst.is_dir(), f"Expected exported directory {dst} does not exist."  
            if item['mtime']:
                assert dst.stat().st_mtime == item['mtime'], f"Directory {dst} mtime mismatch."

        elif item['type'] == 'file':
            src = Path(item['src'])
            dst = export_path / item['dst']
            assert dst.exists() and dst.is_file(), f"Expected exported file {dst} does not exist."
            assert dst.read_bytes() == src.read_bytes(), f"Exported file {dst} content mismatch."
            if item['mtime']:
                assert dst.stat().st_mtime == item['mtime'], f"File {dst} mtime mismatch."

        elif item['type'] == 'symlink':
            dst = export_path / item['dst']
            assert dst.exists(follow_symlinks=False) and dst.is_symlink(), f"Expected exported symlink {dst} does not exist."
            if item['mtime']:
                assert dst.stat(follow_symlinks=False).st_mtime == item['mtime'], f"Symlink {dst} mtime mismatch."
