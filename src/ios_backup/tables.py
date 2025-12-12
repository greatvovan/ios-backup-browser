# Printing and visualization.

from math import log
from datetime import datetime, timedelta
from typing import Iterable
from .backup import Record


def print_list(content: Iterable[str]) -> None:
    """Prints a simple list of strings."""
    for item in content:
        print(item)


def print_table(
        content: Iterable[dict],
        columns: dict[str, dict[str, str]],
        header: bool = True
    ) -> None:
    """Prints a formatted table of content based on specified columns."""

    # IDEA: introduce spacer columns and get rid of 90% of complexity and calculations.
    # {"_1": {"width": 2}} - key must be unique, but underscore will be the indicator.

    last_column = list(columns.keys())[-1]

    # Both headers and content are limited to width - 1.
    # Print header:
    if header:
        for col_name, spec in columns.items():
            width = spec["width"]
            if spec.get('justify') == 'r':
                rpad = spec.get('rpad', 0)
                if len(col_name) > width - rpad - 1:
                    col_name = col_name[-1 - (width - rpad - 1):]
                cell = f"{{key:>{width - rpad}}}{' ' * rpad}".format(key=col_name[-1 - width:])
            else:
                cell = f"{{key:<{width}}}".format(key=col_name[:width - 1])
            print(cell, end="")
        print()

    # Print rows:
    for item in content:
        for col_name, spec in columns.items():
            width = spec["width"]
            cell = str(item[spec["key"]])
            if spec.get('justify') == 'r':
                rpad = spec.get('rpad', 0)
                if len(cell) > width - rpad - 1:
                    cell = cell[-1 - (width - rpad - 1):]
                cell = f"{{cell:>{width - rpad}}}{' ' * rpad}".format(cell=cell)
            else:
                # Allow long content in the last column, if left-justified.
                if col_name != last_column:
                    cell = cell[:width - 1]
                cell = f"{{cell:<{width}}}".format(cell=cell)
            print(cell, end="")
        print()

def print_apps_table(content: Iterable[dict]) -> None:
    """Prints a formatted table of installed apps."""

    try:
        from rich.console import Console
        from rich.table import Table
        
        table = Table(box=None)
        table.add_column("Name", ratio=3)
        table.add_column("Title", ratio=1)
        table.add_column("Version", ratio=1)
        table.add_column("Type", ratio=1)
        table.add_column("Bundle ID", ratio=4, overflow="fold")

        for item in sorted(content, key=lambda x: x["name"]):
            table.add_row(
                item["name"],
                item["title"],
                item["version"],
                item["type"],
                item["bundle_id"],
            )
        
        console = Console()
        console.print(table)

        return
    
    except ImportError:
        # Fallback to simple print if rich is not available
        pass

    # Target 120 character width
    columns = {
        "NAME": {"key": "name", "width": 40},
        "TITLE": {"key": "title", "width": 20},
        "BUNDLE ID": {"key": "bundle_id", "width": 40},
    }

    print_table(content, columns)


def print_summary(summary: dict[str, str]) -> None:
    """Prints a summary as key-value pairs."""
    columns = {
        "PROPERTY": {"key": "property", "width": 25},
        "VALUE": {"key": "value", "width": 55},
    }
    content = [{"property": k, "value": v} for k, v in summary.items()]
    print_table(content, columns, header=False)


def transform_record_for_printing(content: Iterable[Record]) -> Iterable[dict]:
    type_map = {"directory": "D", 'file': "F", 'symlink': "S", "hardlink": "H"}
    for record in content:
        last_modified = record.last_modified
        created = record.created
        item = {
            "domain": record.domain,
            "namespace": record.namespace,
            "path": record.relative_path,
            "type": type_map.get(record.type, ""),
            "size": naturalsize(record.size) if record.type == "file" else "",
            "last_modified": ls_style_time(last_modified) if last_modified else "",
            "created": ls_style_time(created) if created else "",
        }
        yield item


def print_files(content: Iterable[Record]) -> None:
    """Prints a formatted table of files."""

    transformed = transform_record_for_printing(content)

    try:
        import xyz
        from rich.console import Console
        from rich.table import Table
        
        table = Table(box=None)
        table.add_column("T", ratio=1)
        table.add_column("Created", ratio=2, justify="right", overflow="fold")
        table.add_column("Modified", ratio=2, justify="right", overflow="fold")
        table.add_column("Size", ratio=1, justify="right", overflow="fold")
        table.add_column("Domain", ratio=1, overflow="fold")
        table.add_column("Namespace", ratio=4, overflow="fold")
        table.add_column("Path", ratio=4, overflow="fold")

        for item in transformed:
            table.add_row(
                item["type"],
                item["created"],
                item["last_modified"],
                item["size"],
                item["domain"],
                item["namespace"],
                item["path"],
            )
        
        console = Console()
        console.print(table)

        return
    
    except ImportError:
        # Fallback to simple print if rich is not available
        pass

    columns = {
        "T": {"key": "type", "width": 3},
        # "CREATED": {"key": "created", "width": 20},
        "MODIFIED": {"key": "last_modified", "width": 14},
        "SIZE": {"key": "size", "width": 6, 'justify': 'r', 'rpad': 1},
        "DOMAIN": {"key": "domain", "width": 15},
        "NAMESPACE": {"key": "namespace", "width": 30},
        "PATH": {"key": "path", "width": 5},
    }

    print_table(transformed, columns)


def ls_style_time(dt: datetime) -> str:
    now = datetime.now(dt.tzinfo)
    six_months = timedelta(days=183)

    if abs(now - dt) < six_months:
        # Recent timestamp → show time
        return dt.strftime("%b %d %H:%M")
    else:
        # Older timestamp → show year
        return dt.strftime("%b %d  %Y")


def naturalsize(
    value: float | str,
    format: str = "%.1f",
) -> str:
    """
    Format a number of bytes like a human-readable filesize (e.g. 10 kB).
    Credits to https://github.com/python-humanize/humanize/blob/main/src/humanize/filesize.py
    """
    suffixes = "KMGTPEZYRQ"

    base = 1024
    bytes_ = float(value)
    abs_bytes = abs(bytes_)

    if abs_bytes < base:
        return f"{int(bytes_)}B"

    # TODO: replace log(bytes, base) with division for better performance.
    exp = int(min(log(abs_bytes, base), len(suffixes)))
    ret: str = format % (bytes_ / (base**exp)) + suffixes[exp - 1]
    return ret
