#!/usr/bin/env python3
"""Show project changes in projects.csv grouped by project ID."""

import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "projects.csv"


def read_csv(source):
    reader = csv.DictReader(source)
    if not reader.fieldnames or "id" not in reader.fieldnames:
        raise ValueError("projects.csv must contain an id column")
    return reader.fieldnames, {row["id"]: row for row in reader}


def read_revision(revision):
    result = subprocess.run(
        ["git", "show", f"{revision}:projects.csv"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return read_csv(io.StringIO(result.stdout))


def display(value):
    return value if value else "<blank>"


def sort_key(project_id):
    return (0, int(project_id)) if project_id.isdigit() else (1, project_id)


def color(text, code, enabled):
    return f"\033[{code}m{text}\033[0m" if enabled else text


def print_project(title, project_id, color_code, use_color):
    print(color(f"{title} (ID {project_id})", color_code, use_color))


def main():
    parser = argparse.ArgumentParser(
        description="Compare projects.csv with the version in a Git revision."
    )
    parser.add_argument(
        "revision", nargs="?", default="HEAD", help="Git revision to compare against"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    args = parser.parse_args()
    use_color = sys.stdout.isatty() and not args.no_color

    try:
        old_fields, old_projects = read_revision(args.revision)
        with CSV_PATH.open(newline="", encoding="utf-8") as source:
            new_fields, new_projects = read_csv(source)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Unable to compare projects.csv: {error}", file=sys.stderr)
        return 1

    fields = list(dict.fromkeys(old_fields + new_fields))
    project_ids = sorted(set(old_projects) | set(new_projects), key=sort_key)
    change_count = 0

    for project_id in project_ids:
        old = old_projects.get(project_id)
        new = new_projects.get(project_id)
        if old == new:
            continue

        change_count += 1
        if old is None:
            print_project(
                f"Added: {new.get('name') or '<unnamed>'}",
                project_id,
                "32",
                use_color,
            )
            for field in fields:
                if field != "id" and new.get(field):
                    print(f"  {field}: {new[field]}")
        elif new is None:
            print_project(
                f"Removed: {old.get('name') or '<unnamed>'}",
                project_id,
                "31",
                use_color,
            )
        else:
            print_project(
                new.get("name") or old.get("name") or "<unnamed>",
                project_id,
                "33",
                use_color,
            )
            for field in fields:
                before = old.get(field, "")
                after = new.get(field, "")
                if before != after:
                    print(f"  {field}: {display(before)} -> {display(after)}")
        print()

    if not change_count:
        print(f"No project changes compared with {args.revision}.")
    else:
        label = "project" if change_count == 1 else "projects"
        print(f"{change_count} changed {label} compared with {args.revision}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
