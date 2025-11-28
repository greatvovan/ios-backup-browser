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
