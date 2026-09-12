#!/usr/bin/env python3
"""Utility to manage cached HTML fixtures for offline testing.

Usage:
    uv run python test/rer-python/manage_cache.py latest
    uv run python test/rer-python/manage_cache.py list
    uv run python test/rer-python/manage_cache.py clean --older-than 7d
"""

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import re

CACHE_BASE = Path(__file__).parent.parent / "rer-html" / "snapshots"


def get_snapshot_dirs() -> list[Path]:
    """Get all snapshot directories sorted by timestamp (newest first)."""
    if not CACHE_BASE.exists():
        return []

    dirs = [
        d
        for d in CACHE_BASE.iterdir()
        if d.is_dir() and re.match(r"^\d{8}_\d{6}$", d.name)
    ]
    return sorted(dirs, reverse=True)


def cmd_list(args):
    """List all available snapshots."""
    snapshots = get_snapshot_dirs()

    if not snapshots:
        print("No snapshots found.")
        print(
            f"\nRun 'uv run python test/rer-html/fetch_all_snapshots.py' to create one."
        )
        return

    print(f"Available snapshots in {CACHE_BASE}:\n")

    latest = CACHE_BASE / "latest"
    latest_target = latest.resolve() if latest.is_symlink() or latest.exists() else None

    for i, snapshot in enumerate(snapshots):
        is_latest = snapshot.resolve() == latest_target
        marker = " → LATEST" if is_latest else ""

        # Count files
        html_files = list(snapshot.rglob("response.html"))

        print(f"  {i+1}. {snapshot.name}{marker} ({len(html_files)} endpoints)")
        print(
            f"     Created: {snapshot.stat().st_mtime_datetime.strftime('%Y-%m-%d %H:%M')}"
        )
        print(f"     Path: {snapshot}")
        print()


def cmd_latest(args):
    """Set the latest snapshot."""
    snapshots = get_snapshot_dirs()

    if not snapshots:
        print("❌ No snapshots found.")
        print(
            f"\nRun 'uv run python test/rer-html/fetch_all_snapshots.py' to create one."
        )
        return 1

    latest = CACHE_BASE / "latest"
    target = snapshots[0]

    # Remove existing symlink or directory
    if latest.is_symlink():
        latest.unlink()
    elif latest.exists():
        shutil.rmtree(latest)

    # Create symlink
    try:
        latest.symlink_to(target, target_is_directory=True)
        print(f"✅ Set latest → {target.name}")
        print(f"   {latest} → {target}")
        return 0
    except OSError as e:
        # On Windows, symlinks might not work - copy instead
        print(f"⚠️  Could not create symlink (Windows limitation): {e}")
        print(f"   Copying directory instead...")

        if latest.exists():
            shutil.rmtree(latest)

        shutil.copytree(target, latest)
        print(f"✅ Copied {target.name} to latest/")
        return 0


def cmd_clean(args):
    """Clean old snapshots."""
    snapshots = get_snapshot_dirs()

    if args.older_than:
        # Parse duration (e.g., "7d", "2w", "1m")
        match = re.match(r"^(\d+)([dwm])$", args.older_than)
        if not match:
            print(f"❌ Invalid duration format: {args.older_than}")
            print(f"   Use format like: 7d, 2w, 1m")
            return 1

        num, unit = int(match.group(1)), match.group(2)
        if unit == "d":
            delta = timedelta(days=num)
        elif unit == "w":
            delta = timedelta(weeks=num)
        elif unit == "m":
            delta = timedelta(days=num * 30)

        cutoff = datetime.now() - delta

        to_delete = []
        for snapshot in snapshots:
            mtime = datetime.fromtimestamp(snapshot.stat().st_mtime)
            if mtime < cutoff:
                to_delete.append(snapshot)

        if not to_delete:
            print(f"✅ No snapshots older than {args.older_than}")
            return 0

        print(f"Found {len(to_delete)} snapshots older than {args.older_than}:")
        for snapshot in to_delete:
            print(f"  - {snapshot.name}")

        if not args.force:
            response = input("\nDelete these snapshots? [y/N] ")
            if response.lower() != "y":
                print("Cancelled.")
                return 0

        for snapshot in to_delete:
            shutil.rmtree(snapshot)
            print(f"  Deleted {snapshot.name}")

        return 0

    print("❌ Use --older-than to specify which snapshots to clean")
    return 1


def cmd_status(args):
    """Show cache status."""
    snapshots = get_snapshot_dirs()
    latest = CACHE_BASE / "latest"

    print("Cache Status")
    print("=" * 60)
    print(f"Cache directory: {CACHE_BASE}")
    print(f"Total snapshots: {len(snapshots)}")

    if snapshots:
        print(f"Newest: {snapshots[0].name}")
        print(f"Oldest: {snapshots[-1].name}")

    if latest.exists():
        if latest.is_symlink():
            target = latest.resolve()
            print(f"Latest: {latest.name} → {target.name}")
        else:
            print(f"Latest: {latest.name} (copy)")

        # Count endpoints
        html_files = list(latest.rglob("response.html"))
        print(f"Endpoints cached: {len(html_files)}")
    else:
        print(f"Latest: ❌ Not set")
        print(
            f"\nRun 'uv run python {Path(__file__).relative_to(Path.cwd())} latest' to set latest snapshot"
        )

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Manage cached HTML fixtures for offline RER testing"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    p_list = subparsers.add_parser("list", help="List all snapshots")
    p_list.set_defaults(func=cmd_list)

    # latest command
    p_latest = subparsers.add_parser("latest", help="Set the latest snapshot")
    p_latest.set_defaults(func=cmd_latest)

    # clean command
    p_clean = subparsers.add_parser("clean", help="Clean old snapshots")
    p_clean.add_argument(
        "--older-than",
        required=True,
        help="Delete snapshots older than (e.g., 7d, 2w, 1m)",
    )
    p_clean.add_argument(
        "--force", "-f", action="store_true", help="Delete without asking"
    )
    p_clean.set_defaults(func=cmd_clean)

    # status command
    p_status = subparsers.add_parser("status", help="Show cache status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    exit(main())
