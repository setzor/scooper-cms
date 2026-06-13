#!/usr/bin/env python3
"""
Scooper CMS - Complete Backup Script
Performs database and media asset backups together.
Designed to be run via cron for scheduled backups.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backup_utils import (
    backup_database_to_remote,
    backup_media_local,
    backup_media_to_remote,
    create_backup_with_timestamp,
    get_backup_config,
    perform_full_backup,
)


def main():
    """Main backup execution."""
    print("=" * 60)
    print("Scooper CMS - Complete Backup")
    print("=" * 60)

    # Show configuration
    config = get_backup_config()
    print(f"\nConfiguration:")
    print(f"  - Database backup enabled: {config.get('backup_database', True)}")
    print(f"  - Media backup enabled: {config.get('backup_media', True)}")
    print(f"  - Remote backup enabled: {config.get('remote_enabled', False)}")
    if config.get("remote_enabled", False):
        print(f"  - Remote type: {config.get('remote_type', 'rclone')}")
    print()

    # Perform full backup
    db_path, media_path, success = perform_full_backup()

    # Summary
    print("\n" + "=" * 60)
    print("Backup Summary")
    print("=" * 60)

    if db_path:
        print(f"✓ Database backup created: {db_path}")
    else:
        print("✗ Database backup failed or disabled")

    if media_path:
        print(f"✓ Media backup created: {media_path}")
    else:
        print("✗ Media backup failed or disabled")

    if success:
        print("\n✓ All backups completed successfully!")
        return 0
    else:
        print("\n⚠ Some backups completed with warnings")
        return 0  # Still return success as partial backup may have worked


if __name__ == "__main__":
    sys.exit(main())
