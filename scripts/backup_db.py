#!/usr/bin/env python3
"""
Scooper CMS - Database Backup Script
Command-line interface for database backup and restore operations.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backup_utils import create_backup_with_timestamp, restore_database, get_latest_backup

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backup_db.py backup     - Create a new backup")
        print("  python backup_db.py restore    - Restore from latest backup")
        print("  python backup_db.py restore <path> - Restore from specific backup")
        sys.exit(1)

    command = sys.argv[1]

    if command == "backup":
        backup_path = create_backup_with_timestamp()
        if backup_path:
            print(f"Success: {backup_path}")
            sys.exit(0)
        else:
            print("Backup failed")
            sys.exit(1)
    elif command == "restore":
        if len(sys.argv) > 2:
            success = restore_database(sys.argv[2])
        else:
            latest = get_latest_backup()
            if latest:
                success = restore_database(latest)
            else:
                print("No backups found in backups/ directory")
                success = False
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
