import logging
import argparse
from .backup import Backup


def build_parser():
    parser = argparse.ArgumentParser(description="iOS Backup Browser")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_export = subparsers.add_parser("export", help="Export files from iOS backup")
    parser_export.add_argument("--backup-path", type=str, help="Path to the iOS backup directory")
    parser_export.add_argument("--output-path", type=str, help="Path to export files to")
    parser_export.add_argument("--domain-prefix", type=str, help="Filter by domain prefix")
    parser_export.add_argument("--namespace-prefix", type=str, help="Filter by namespace")
    parser_export.add_argument("--path-prefix", type=str, help="Filter by path prefix")
    parser_export.add_argument("--ignore-missing", action="store_true", help="Ignore missing files during export")
    parser_export.add_argument("--restore-modified-dates", action="store_true", help="Restore modified dates")
    parser_export.set_defaults(func=export_handler)

    return parser


def export_handler(args):
    if not args.backup_path or not args.output_path:
        logging.error("Both --backup-path and --output-path are required for export command.")
        exit(1)
    
    export(
        args.backup_path,
        args.output_path,
        args.domain_prefix or "",
        args.namespace_prefix or "",
        args.path_prefix or "",
        args.ignore_missing,
        args.restore_modified_dates
    )
    
def export(
        backup_path: str,
        output_path: str,
        domain_prefix: str,
        namespace_prefix: str,
        path_prefix: str,
        ignore_missing: bool = True,
        restore_modified_dates: bool = True,
    ) -> None:
    backup = Backup(backup_path)
    content = backup.get_content(domain_prefix, namespace_prefix,
                                 path_prefix, parse_metadata=restore_modified_dates)
    content_count = backup.get_content_count(domain_prefix, namespace_prefix, path_prefix)
    backup.export(content, output_path, ignore_missing, restore_modified_dates, content_count)
    backup.close()
    logging.info(f"{content_count} entries processed")


def main():
    parser = build_parser()
    try:
        args = parser.parse_args()
    except Exception:
        parser.print_help()
        exit(1)
    
    args.func(args)
        

if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        main()
    except Exception as e:    
        logging.error(f"An error occurred: {e}", exc_info=True)
        exit(1)
