#!/usr/bin/env python3
"""
Scooper CMS - Media Assets Backup Script
Command-line interface for media asset backup and restore operations.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backup_utils import (
    backup_media_local,
    backup_media_to_remote,
    create_media_backup_archive,
    get_backup_config,
    get_latest_media_backup,
    perform_full_backup,
    restore_media_backup,
    save_backup_config,
)


def print_usage():
    """Print usage instructions."""
    print("Usage:")
    print("  python backup_media.py backup            - Create a new media backup")
    print(
        "  python backup_media.py backup-remote     - Create media backup and upload to remote"
    )
    print(
        "  python backup_media.py restore           - Restore from latest media backup"
    )
    print("  python backup_media.py restore <path>    - Restore from specific backup")
    print(
        "  python backup_media.py full              - Perform full backup (database + media)"
    )
    print("  python backup_media.py config            - Show current configuration")
    print("  python backup_media.py config-set <key> <value> - Set configuration value")


def show_config():
    """Display current backup configuration."""
    config = get_backup_config()
    print("\nCurrent Backup Configuration:")
    print("-" * 40)
    for key, value in config.items():
        print(f"  {key}: {value}")
    print("-" * 40)
    print("\nConfiguration file:", os.path.abspath("backup_config.json"))


def set_config_key(key, value):
    """Set a configuration key to a value."""
    config = get_backup_config()

    # Convert value type
    if value.lower() in ("true", "yes", "1"):
        value = True
    elif value.lower() in ("false", "no", "0"):
        value = False
    elif value.isdigit():
        value = int(value)
    else:
        value = value  # Keep as string

    if key in config:
        config[key] = value
        if save_backup_config(config):
            print(f"Configuration updated: {key} = {value}")
        else:
            print(f"Failed to save configuration")
    else:
        print(f"Unknown configuration key: {key}")
        print("Valid keys:", ", ".join(config.keys()))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "backup":
        # Create local media backup
        backup_path = backup_media_local()
        if backup_path:
            print(f"Success: {backup_path}")
            sys.exit(0)
        else:
            print("Media backup failed")
            sys.exit(1)

    elif command == "backup-remote":
        # Create media backup and upload to remote
        success = backup_media_to_remote()
        if success:
            print("Media backup and remote upload completed successfully")
            sys.exit(0)
        else:
            print("Media backup or remote upload failed")
            sys.exit(1)

    elif command == "restore":
        if len(sys.argv) > 2:
            success = restore_media_backup(sys.argv[2])
        else:
            latest = get_latest_media_backup()
            if latest:
                success = restore_media_backup(latest)
            else:
                print("No media backups found in backups/ directory")
                success = False
        sys.exit(0 if success else 1)

    elif command == "full":
        # Perform full backup (database + media + remote)
        db_path, media_path, success = perform_full_backup()
        if success:
            print(f"\nFull backup completed successfully")
            if db_path:
                print(f"  Database backup: {db_path}")
            if media_path:
                print(f"  Media backup: {media_path}")
            sys.exit(0)
        else:
            print("Full backup completed with warnings")
            sys.exit(0)  # Still exit 0 as partial backup may have succeeded

    elif command == "config":
        show_config()
        sys.exit(0)

    elif command == "config-set":
        if len(sys.argv) > 3:
            set_config_key(sys.argv[2], " ".join(sys.argv[3:]))
        else:
            print("Error: Missing key or value for configuration")
            print("Usage: python backup_media.py config-set <key> <value>")
            sys.exit(1)
        sys.exit(0)

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)
