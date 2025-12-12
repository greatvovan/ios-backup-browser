import sys
import logging
import argparse
from .backup import Backup
from . import __version__
from .tables import print_apps_table, print_summary, print_files, print_list
from .metadata import get_backup_summary


def build_parser():
    parser = argparse.ArgumentParser(description="iOS Backup Browser")
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"ios_backup {__version__}",
        help="Show the version number and exit"
    )

    commands = parser.add_subparsers(dest="command", required=True)

    parser_export = commands.add_parser("export", help="Export files from iOS backup")
    parser_export.add_argument("backup_path", type=str, help="Path to the iOS backup directory")
    parser_export.add_argument("output_path", type=str, help="Path to export files")
    parser_export.add_argument("--domain", type=str, help="Filter by domain", metavar="string")
    parser_export.add_argument("--namespace", type=str, help="Filter by namespace", metavar="string")
    parser_export.add_argument("--path", type=str, help="Filter by device path", metavar="string")
    parser_export.add_argument("--like-syntax", action="store_true", help="Interpret filters as Sqlite LIKE expressions instead of prefixes")
    parser_export.add_argument("--ignore-missing", action="store_true", help="Ignore missing files during export")
    parser_export.add_argument("--restore-dates", action="store_true", help="Restore modified dates")
    parser_export.add_argument("--restore-symlinks", action="store_true", help="Restore symlbolic links")
    parser_export.set_defaults(func=handle_export)

    parser_inspect = commands.add_parser("inspect", help="Inspect iOS backup")
    # parser_inspect.set_defaults(func=handle_inspect)

    inspect_commands = parser_inspect.add_subparsers(dest="target", required=True)

    inspect_apps = inspect_commands.add_parser("info", help="Show backup info")
    inspect_apps.add_argument("backup_path", type=str, help="Path to the iOS backup directory")
    inspect_apps.set_defaults(func=handle_inspect_info)

    inspect_apps = inspect_commands.add_parser("apps", help="List installed apps")
    inspect_apps.add_argument("backup_path", type=str, help="Path to the iOS backup directory")
    inspect_apps.set_defaults(func=handle_inspect_apps)

    inspect_domains = inspect_commands.add_parser("domains", help="List backup domains")
    inspect_domains.add_argument("backup_path", type=str, help="Path to the iOS backup directory")
    inspect_domains.set_defaults(func=handle_inspect_domains)

    inspect_namespaces = inspect_commands.add_parser("namespaces", help="List namespaces of a domain")
    inspect_namespaces.add_argument("domain", type=str, help="Domain (string). One of returned by 'domains' command.")
    inspect_namespaces.add_argument("backup_path", type=str, help="Path to the iOS backup directory")
    inspect_namespaces.set_defaults(func=handle_inspect_namespaces)

    inspect_files = inspect_commands.add_parser("files", help="List backup files")
    inspect_files.add_argument("--domain", type=str, help="Filter by domain", metavar="string")
    inspect_files.add_argument("--namespace", type=str, help="Filter by namespace", metavar="string")
    inspect_files.add_argument("--path", type=str, help="Filter by device path", metavar="string")
    inspect_files.add_argument("--like-syntax", action="store_true", help="Interpret filters as Sqlite LIKE expressions instead of prefixes")
    inspect_files.add_argument("backup_path", type=str, help="Path to the iOS backup directory")
    inspect_files.set_defaults(func=handle_inspect_files)


    return parser


def handle_export(args):
    if not args.backup_path or not args.output_path:
        logging.error("Both backup_path and output_path are required for export command.")
        exit(1)
    
    if args.like_syntax and args.namespace:
        logging.error("The --like-syntax option cannot be used with --namespace."
                      "Use --domain with namespace pattern included instead.")
        exit(1)

    export(
        args.backup_path,
        args.output_path,
        args.domain or "",
        args.namespace or "",
        args.path or "",
        args.like_syntax,
        args.ignore_missing,
        args.restore_dates,
        args.restore_symlinks,
    )


def export(
        backup_path: str,
        output_path: str,
        domain: str,
        namespace: str,
        path: str,
        like_syntax: bool = False,
        ignore_missing: bool = True,
        restore_modified_dates: bool = False,
        restore_symlinks: bool = False,
    ) -> None:
    backup = Backup(backup_path)
    content = backup.get_content(domain, namespace,
                                 path, like_syntax,
                                 parse_metadata=restore_modified_dates)
    content_count = backup.get_content_count(domain, namespace, path, like_syntax)
    backup.export(content, output_path, ignore_missing, restore_modified_dates, restore_symlinks, content_count)
    backup.close()
    logging.info(f"{content_count} entries processed")


def handle_inspect_info(args):
    backup = Backup(args.backup_path)
    info = backup.info
    status = backup.status
    manifest = backup.manifest
    summary = get_backup_summary(info, status, manifest)
    print_summary(summary)
    backup.close()


def handle_inspect_apps(args):
    backup = Backup(args.backup_path)
    print_apps_table(backup.info.get_apps())
    backup.close()


def handle_inspect_domains(args):
    backup = Backup(args.backup_path)
    print_list(backup.all_domains())
    backup.close()


def handle_inspect_namespaces(args):
    backup = Backup(args.backup_path)
    print_list(backup.namespaces(args.domain))
    backup.close()


def handle_inspect_files(args):
    if args.like_syntax and args.namespace:
        logging.error("The --like-syntax option cannot be used with --namespace."
                      "Use --domain with namespace pattern included instead.")
        exit(1)

    backup = Backup(args.backup_path)
    content_count = backup.get_content_count(args.domain, args.namespace, args.path, args.like_syntax)

    if content_count > 1000 and sys.stdin.isatty():
        print(f"Warning: this query will return {content_count} records.")
        answer = input("Are you sure you want to print them [Y/n]? ").strip().lower()

        if answer not in ("", "y", "yes"):
            return
        
    content = backup.get_content(
        args.domain, args.namespace, args.path,
        args.like_syntax, parse_metadata=True, sorting=True,
    )
    print_files(content)
    backup.close()

    logging.info(f"{content_count} entries found")


def handle_cli():
    parser = build_parser()
    try:
        args = parser.parse_args()
    except Exception:
        parser.print_help()
        exit(1)
    
    args.func(args)


def main():
    try:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        handle_cli()
    except Exception as e:    
        logging.error(f"An error occurred: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
