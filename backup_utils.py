#!/usr/bin/env python3
"""
Scooper CMS - Safe SQLite Backup Utilities
Uses SQLite's online backup API to create safe backups of active databases.
Includes offsite backup support for media assets using rclone or local copy.
"""

import json
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime

# Path configuration (match server.py)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "db", "scooper.db")
BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups")
UPLOADS_DIR = os.path.join(SCRIPT_DIR, "static", "uploads")

# Configuration file path
CONFIG_FILE = os.path.join(SCRIPT_DIR, "backup_config.json")


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


def get_backup_config():
    """
    Load backup configuration from JSON file.
    Returns a dict with default values if config file doesn't exist.
    """
    defaults = {
        "remote_enabled": False,
        "remote_type": "rclone",  # or "local"
        "rclone_remote": "",
        "rclone_path": "",
        "local_backup_path": "",
        "backup_media": True,
        "backup_database": True,
        "retention_days": 30,
        "compress_backups": True,
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Merge defaults with loaded config
                defaults.update(config)
                return defaults
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
            return defaults

    return defaults


def save_backup_config(config):
    """Save backup configuration to JSON file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def ensure_uploads_dir():
    """Ensure uploads directory exists."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def create_media_backup_archive():
    """
    Create a timestamped tar.gz archive of the uploads directory.

    Returns:
        Path to the created archive file, or None on failure.
    """
    ensure_uploads_dir()
    ensure_backup_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_filename = f"media_backup_{timestamp}.tar.gz"
    archive_path = os.path.join(BACKUP_DIR, archive_filename)

    try:
        # Create tarball of uploads directory
        import tarfile

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(UPLOADS_DIR, arcname=os.path.basename(UPLOADS_DIR))

        print(f"Media backup archive created: {archive_path}")
        return archive_path
    except Exception as e:
        print(f"Media backup failed: {e}")
        return None


def backup_media_to_remote(archive_path=None):
    """
    Backup media assets to remote storage using rclone or local copy.

    Args:
        archive_path: Optional path to a specific archive. If None, creates a new one.

    Returns:
        True on success, False on failure.
    """
    config = get_backup_config()

    if not config["remote_enabled"]:
        print("Remote backup is disabled in configuration.")
        return False

    # Create archive if not provided
    if archive_path is None:
        archive_path = create_media_backup_archive()

    if archive_path is None:
        print("Failed to create media backup archive.")
        return False

    try:
        if config["remote_type"] == "rclone":
            # Use rclone to copy to remote storage
            remote_path = config.get("rclone_path", "scooper_backups")
            remote_name = config.get("rclone_remote", "")

            if not remote_name:
                print("Error: rclone_remote not configured")
                return False

            # Build rclone command
            rclone_cmd = [
                "rclone",
                "copy",
                archive_path,
                f"{remote_name}:{remote_path}",
                "-v",
            ]

            result = subprocess.run(rclone_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Media backup uploaded to remote: {remote_name}:{remote_path}")
                return True
            else:
                print(f"rclone error: {result.stderr}")
                return False

        elif config["remote_type"] == "local":
            # Copy to local backup path
            local_path = config.get("local_backup_path", "")
            if not local_path:
                print("Error: local_backup_path not configured")
                return False

            # Ensure local backup directory exists
            os.makedirs(local_path, exist_ok=True)

            # Copy archive to local path
            dest_path = os.path.join(local_path, os.path.basename(archive_path))
            shutil.copy2(archive_path, dest_path)
            print(f"Media backup copied to local: {dest_path}")
            return True
        else:
            print(f"Unknown remote type: {config['remote_type']}")
            return False

    except Exception as e:
        print(f"Remote backup failed: {e}")
        return False


def backup_media_local():
    """
    Create a local backup of media assets (without remote upload).

    Returns:
        Path to the created archive file, or None on failure.
    """
    return create_media_backup_archive()


def get_latest_media_backup():
    """Get path to the most recent media backup file."""
    ensure_backup_dir()
    backups = []
    if os.path.exists(BACKUP_DIR):
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("media_backup_") and filename.endswith(".tar.gz"):
                filepath = os.path.join(BACKUP_DIR, filename)
                backups.append((os.path.getmtime(filepath), filepath))
        if backups:
            backups.sort(reverse=True)
            return backups[0][1]
    return None


def restore_media_backup(backup_path):
    """
    Restore media assets from a backup archive.

    WARNING: This will overwrite existing files in the uploads directory.

    Args:
        backup_path: Path to the backup archive file.

    Returns:
        True on success, False on failure.
    """
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path}")
        return False

    ensure_uploads_dir()

    try:
        import tarfile

        # Clear existing uploads directory
        if os.path.exists(UPLOADS_DIR):
            shutil.rmtree(UPLOADS_DIR)
        os.makedirs(UPLOADS_DIR, exist_ok=True)

        # Extract archive
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(path=os.path.dirname(UPLOADS_DIR))

        print(f"Media restored from {backup_path}")
        return True
    except Exception as e:
        print(f"Media restore failed: {e}")
        return False


def cleanup_old_backups():
    """
    Clean up old backup files based on retention policy.

    Returns:
        Number of files cleaned up.
    """
    config = get_backup_config()
    retention_days = config.get("retention_days", 30)

    ensure_backup_dir()

    if not os.path.exists(BACKUP_DIR):
        return 0

    cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
    cleaned_up = 0

    for filename in os.listdir(BACKUP_DIR):
        # Check both database and media backups
        if (filename.startswith("scooper_backup_") and filename.endswith(".db")) or (
            filename.startswith("media_backup_") and filename.endswith(".tar.gz")
        ):
            filepath = os.path.join(BACKUP_DIR, filename)
            try:
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    cleaned_up += 1
                    print(f"Removed old backup: {filename}")
            except Exception as e:
                print(f"Error removing {filename}: {e}")

    return cleaned_up


def perform_full_backup():
    """
    Perform a complete backup: database + media assets + remote upload.

    Returns:
        Tuple of (db_backup_path, media_backup_path, success)
    """
    config = get_backup_config()

    db_path = None
    media_path = None
    success = True

    # Backup database if enabled
    if config.get("backup_database", True):
        db_path = create_backup_with_timestamp()
        if db_path is None:
            print("Warning: Database backup failed")
            success = False

    # Backup media if enabled
    if config.get("backup_media", True):
        media_path = backup_media_local()
        if media_path is None:
            print("Warning: Media backup failed")
            success = False

    # Upload to remote if enabled
    if config.get("remote_enabled", False):
        # Upload database backup
        if db_path and config.get("backup_database", True):
            db_remote_success = backup_database_to_remote(db_path)
            if not db_remote_success:
                print("Warning: Database remote backup failed")
                success = False

        # Upload media backup
        if media_path and config.get("backup_media", True):
            media_remote_success = backup_media_to_remote(media_path)
            if not media_remote_success:
                print("Warning: Media remote backup failed")
                success = False

    # Cleanup old backups
    if config.get("retention_days", 30) > 0:
        cleaned = cleanup_old_backups()
        if cleaned > 0:
            print(f"Cleaned up {cleaned} old backup files")

    return (db_path, media_path, success)


def backup_database_to_remote(db_path=None):
    """
    Backup database file to remote storage.

    Args:
        db_path: Optional path to a specific database backup. If None, uses latest.

    Returns:
        True on success, False on failure.
    """
    config = get_backup_config()

    if not config["remote_enabled"]:
        print("Remote backup is disabled in configuration.")
        return False

    # Use latest backup if not provided
    if db_path is None:
        db_path = get_latest_backup()

    if db_path is None:
        print("No database backup found.")
        return False

    try:
        if config["remote_type"] == "rclone":
            remote_path = config.get("rclone_path", "scooper_backups")
            remote_name = config.get("rclone_remote", "")

            if not remote_name:
                print("Error: rclone_remote not configured")
                return False

            # Build rclone command
            rclone_cmd = [
                "rclone",
                "copy",
                db_path,
                f"{remote_name}:{remote_path}",
                "-v",
            ]

            result = subprocess.run(rclone_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(
                    f"Database backup uploaded to remote: {remote_name}:{remote_path}"
                )
                return True
            else:
                print(f"rclone error: {result.stderr}")
                return False

        elif config["remote_type"] == "local":
            local_path = config.get("local_backup_path", "")
            if not local_path:
                print("Error: local_backup_path not configured")
                return False

            os.makedirs(local_path, exist_ok=True)
            dest_path = os.path.join(local_path, os.path.basename(db_path))
            shutil.copy2(db_path, dest_path)
            print(f"Database backup copied to local: {dest_path}")
            return True
        else:
            print(f"Unknown remote type: {config['remote_type']}")
            return False

    except Exception as e:
        print(f"Remote database backup failed: {e}")
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
