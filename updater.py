"""
Auto-updater for Reality.
Pulls from git and restarts the service when code changes.
"""

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# Files that trigger a restart when changed
CODE_FILES = ["**/*.py"]

# Files that can be hot-reloaded (no restart needed)
HOT_RELOAD_FILES = ["config/*.json", "data/backstory.json"]


def get_file_hash(path: Path) -> str:
    """Get MD5 hash of a file."""
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def get_code_snapshot(root: Path) -> dict:
    """Get hashes of all Python files."""
    snapshot = {}
    for pattern in CODE_FILES:
        for path in root.glob(pattern):
            if "venv" in str(path) or "__pycache__" in str(path):
                continue
            snapshot[str(path)] = get_file_hash(path)
    return snapshot


def git_pull(root: Path) -> tuple[bool, str]:
    """Pull latest changes from git."""
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            changed = "Already up to date" not in output
            return changed, output
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def restart_service():
    """Restart the Reality service."""
    print("[Updater] Restarting Reality...")

    # Try systemd first (Linux)
    result = subprocess.run(
        ["systemctl", "--user", "restart", "reality"],
        capture_output=True
    )
    if result.returncode == 0:
        return True

    # Try launchctl (macOS)
    home = os.path.expanduser("~")
    result = subprocess.run(
        ["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.reality"],
        capture_output=True
    )
    if result.returncode == 0:
        return True

    # Try Windows service
    result = subprocess.run(
        ["net", "stop", "reality"],
        capture_output=True,
        shell=True
    )
    subprocess.run(
        ["net", "start", "reality"],
        capture_output=True,
        shell=True
    )

    return False


def run_updater(
    root: Path,
    check_interval: int = 300,  # 5 minutes
    auto_restart: bool = True
):
    """
    Run the auto-updater loop.

    Args:
        root: Path to the Reality repo
        check_interval: Seconds between update checks
        auto_restart: Whether to auto-restart on code changes
    """
    print(f"[Updater] Starting auto-updater (checking every {check_interval}s)")
    print(f"[Updater] Repo: {root}")

    # Get initial snapshot
    code_snapshot = get_code_snapshot(root)

    while True:
        time.sleep(check_interval)

        # Pull latest
        changed, output = git_pull(root)

        if changed:
            print(f"[Updater] Git pull: {output}")

            # Check what changed
            new_snapshot = get_code_snapshot(root)

            code_changed = new_snapshot != code_snapshot

            if code_changed and auto_restart:
                print("[Updater] Code changed, restarting...")
                restart_service()
                # Exit - the service manager will restart us
                sys.exit(0)
            elif code_changed:
                print("[Updater] Code changed (restart disabled)")
            else:
                print("[Updater] Config/data changed (no restart needed)")

            code_snapshot = new_snapshot
        else:
            print(f"[Updater] No updates")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reality auto-updater")
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Check interval in seconds (default: 300)"
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Don't auto-restart on code changes"
    )

    args = parser.parse_args()

    root = Path(__file__).parent
    run_updater(
        root=root,
        check_interval=args.interval,
        auto_restart=not args.no_restart
    )
