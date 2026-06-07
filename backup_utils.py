#!/usr/bin/env python3
"""
Scooper CMS - Safe SQLite Backup Utilities
Uses SQLite's online backup API to create safe backups of active databases.
"""

import os
import sqlite3
import shutil
from datetime import datetime

# Path configuration (match server.py)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "db", "scooper.db")
BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups")


def ensure_backup_dir():
    """Ensure backup directory exists."""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_database(target_path=None):
    """
    Create a safe backup of the SQLite database using the online backup API.

    Args:
        target_path: Optional custom path for the backup file.
                    If None, creates timestamped backup in backups/ directory.

    Returns:
        Path to the created backup file, or None on failure.
    """
    ensure_backup_dir()

    if target_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"scooper_backup_{timestamp}.db"
        target_path = os.path.join(BACKUP_DIR, backup_filename)

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)

    try:
        # Open source database in read-only mode for backup
        source_conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

        # Create the backup connection
        backup_conn = sqlite3.connect(target_path)

        # Use SQLite's backup API through Python
        # This safely copies the database while it's in use
        source_conn.backup(backup_conn, pages=1, progress=None)

        backup_conn.close()
        source_conn.close()

        print(f"Backup created: {target_path}")
        return target_path

    except sqlite3.Error as e:
        print(f"Backup failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during backup: {e}")
        return None


def create_backup_with_timestamp():
    """Create a timestamped backup file."""
    return backup_database()


def get_latest_backup():
    """Get path to the most recent backup file."""
    ensure_backup_dir()
    backups = []
    if os.path.exists(BACKUP_DIR):
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("scooper_backup_") and filename.endswith(".db"):
                filepath = os.path.join(BACKUP_DIR, filename)
                backups.append((os.path.getmtime(filepath), filepath))
        if backups:
            backups.sort(reverse=True)
            return backups[0][1]
    return None


def restore_database(backup_path):
    """
    Restore database from a backup file.

    WARNING: This will overwrite the existing database.
    """
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path}")
        return False

    # Ensure target directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    try:
        # Use shutil.copy2 to preserve metadata
        shutil.copy2(backup_path, DB_PATH)
        print(f"Database restored from {backup_path}")
        return True
    except Exception as e:
        print(f"Restore failed: {e}")
        return False


if __name__ == "__main__":
    # Command-line usage
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) > 2:
            restore_database(sys.argv[2])
        else:
            latest = get_latest_backup()
            if latest:
                restore_database(latest)
            else:
                print("No backups found")
    else:
        create_backup_with_timestamp()
