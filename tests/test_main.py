from pathlib import Path

from ios_backup.__main__ import build_parser, export_handler, export


def test_cli_arguments(monkeypatch, tmp_path):
    """Ensure values parsed by build_parser() are passed to export().

    This test parses a realistic `export` command line then replaces the real
    `export` function with a fake that captures the arguments it receives.
    The test asserts the captured parameters match the CLI values.
    """

    captured = {}

    def mock_export(backup_path, output_path,
                    domain_prefix, namespace_prefix, path_prefix,
                    ignore_missing=True, restore_modified_dates=False, restore_symlinks=False):
        captured['backup_path'] = backup_path
        captured['output_path'] = output_path
        captured['domain_prefix'] = domain_prefix
        captured['namespace_prefix'] = namespace_prefix
        captured['path_prefix'] = path_prefix
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
    export_handler(args)

    # Verify all parsed values were passed into export() by the handler
    assert captured['backup_path'] == str(tmp_path / 'some_backup')
    assert captured['output_path'] == str(tmp_path / 'out')
    assert captured['domain_prefix'] == 'AppDomain'
    assert captured['namespace_prefix'] == 'com.example'
    assert captured['path_prefix'] == 'docs'
    assert captured['ignore_missing'] is True
    assert captured['restore_modified_dates'] is True
    assert captured['restore_symlinks'] is True


def test_export_real_backup(tmp_path):
    """Test export function with a real backup structure and plist files."""

    export_path = tmp_path / 'exported'

    export('tests/data/sample_backup', str(export_path),
           domain_prefix='', namespace_prefix='', path_prefix='',
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
            'mtime': 1761700864,
        },
    ]

    for item in expected_items:
        if item['type'] == 'directory':
            dst = export_path / item['dst']
            assert dst.exists() and dst.is_dir(), f"Expected exported directory {dst} does not exist."  
            if item['mtime']:
                assert dst.stat().st_mtime == item['mtime']

        elif item['type'] == 'file':
            src = Path(item['src'])
            dst = export_path / item['dst']
            assert dst.exists() and dst.is_file(), f"Expected exported file {dst} does not exist."
            assert dst.read_bytes() == src.read_bytes(), f"Exported file {dst} content mismatch."
            if item['mtime']:
                assert dst.stat().st_mtime == item['mtime']

        elif item['type'] == 'symlink':
            dst = export_path / item['dst']
            assert dst.exists(follow_symlinks=False) and dst.is_symlink(), f"Expected exported symlink {dst} does not exist."
            if item['mtime']:
                assert dst.stat().st_mtime == item['mtime']
