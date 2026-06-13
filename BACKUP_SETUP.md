# Scooper CMS Backup Strategy

## Overview

This document describes the backup strategy for Scooper CMS, which includes:

- **Database Backups**: Automatic backups of the SQLite database (`db/scooper.db`)
- **Media Asset Backups**: Automatic backups of uploaded media files (`static/uploads/`)
- **Offsite Replication**: Optional remote backup to cloud storage using rclone

## Quick Start

### 1. Local Backup (No Remote)

For local backups only (backups stored on the same server):

```bash
# Create a local backup of both database and media
python3 scripts/backup_all.py

# Or use individual scripts
python3 scripts/backup_db.py backup
python3 scripts/backup_media.py backup
```

Backups are stored in the `backups/` directory:
- Database backups: `backups/scooper_backup_YYYYMMDD_HHMMSS.db`
- Media backups: `backups/media_backup_YYYYMMDD_HHMMSS.tar.gz`

### 2. Configure Remote Backup (Recommended)

For offsite backups, you need to configure remote storage.

#### Option A: Using rclone (Recommended)

1. **Install rclone** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt install rclone
   
   # macOS (Homebrew)
   brew install rclone
   
   # Download from https://rclone.org/
   ```

2. **Configure rclone remote**:
   ```bash
   rclone config
   ```
   Follow the prompts to set up your cloud storage (Google Drive, S3, Dropbox, etc.).

3. **Configure Scooper backup**:
   ```bash
   # Enable remote backup
   python3 scripts/backup_media.py config-set remote_enabled true
   
   # Set your rclone remote name (from step 2)
   python3 scripts/backup_media.py config-set rclone_remote myremote
   
   # Optional: Set custom remote path
   python3 scripts/backup_media.py config-set rclone_path scooper_backups
   
   # View current configuration
   python3 scripts/backup_media.py config
   ```

#### Option B: Using Local Path

To copy backups to another directory on the same server:

```bash
python3 scripts/backup_media.py config-set remote_enabled true
python3 scripts/backup_media.py config-set remote_type local
python3 scripts/backup_media.py config-set local_backup_path /mnt/backup-server/scooper
```

### 3. Test Your Backup Configuration

```bash
# Test full backup with remote upload
python3 scripts/backup_all.py

# Check backups directory
ls -la backups/
```

## Automated Backups with Cron

### Basic Cron Setup

1. **Edit your crontab**:
   ```bash
   crontab -e
   ```

2. **Add scheduled backup jobs**:

   ```bash
   # Daily backup at 2:00 AM
   0 2 * * * /usr/bin/python3 /path/to/scooper/scripts/backup_all.py >> /var/log/scooper_backup.log 2>&1
   
   # Hourly backup (if you need more frequent backups)
   0 * * * * /usr/bin/python3 /path/to/scooper/scripts/backup_all.py >> /var/log/scooper_backup.log 2>&1
   ```

   Replace `/path/to/scooper` with your actual Scooper installation path.

### Advanced Cron Setup with Rotation

For better organization and log rotation:

```bash
# Daily backup with date-based log files
0 2 * * * /usr/bin/python3 /path/to/scooper/scripts/backup_all.py >> /var/log/scooper_backup_$(date +\%Y\%m\%d).log 2>&1

# Clean up logs older than 30 days
0 3 * * * find /var/log/scooper_backup_*.log -mtime +30 -delete
```

### Systemd Timer (Alternative to Cron)

For systems using systemd, you can create a timer:

1. **Create service file** (`/etc/systemd/system/scooper-backup.service`):
   ```ini
   [Unit]
   Description=Scooper CMS Backup
   
   [Service]
   Type=oneshot
   ExecStart=/usr/bin/python3 /path/to/scooper/scripts/backup_all.py
   User=your_username
   WorkingDirectory=/path/to/scooper
   StandardOutput=append:/var/log/scooper_backup.log
   StandardError=append:/var/log/scooper_backup_error.log
   ```

2. **Create timer file** (`/etc/systemd/system/scooper-backup.timer`):
   ```ini
   [Unit]
   Description=Daily Scooper CMS Backup
   
   [Timer]
   OnCalendar=daily
   Persistent=true
   
   [Install]
   WantedBy=timers.target
   ```

3. **Enable and start**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable scooper-backup.timer
   sudo systemctl start scooper-backup.timer
   ```

## Backup Management

### List Available Backups

```bash
# List all backups
ls -la backups/

# List with timestamps
ls -lt backups/
```

### Restore from Backup

#### Restore Database

```bash
# Restore from latest backup
python3 scripts/backup_db.py restore

# Restore from specific backup
python3 scripts/backup_db.py restore backups/scooper_backup_20240101_120000.db
```

#### Restore Media Assets

```bash
# Restore from latest media backup
python3 scripts/backup_media.py restore

# Restore from specific backup
python3 scripts/backup_media.py restore backups/media_backup_20240101_120000.tar.gz
```

### Configuration Reference

All configuration is stored in `backup_config.json`:

```json
{
  "remote_enabled": false,
  "remote_type": "rclone",
  "rclone_remote": "myremote",
  "rclone_path": "scooper_backups",
  "local_backup_path": "/mnt/backup-server/scooper",
  "backup_media": true,
  "backup_database": true,
  "retention_days": 30,
  "compress_backups": true
}
```

| Setting | Description | Default | Example |
|---------|-------------|---------|---------|
| `remote_enabled` | Enable offsite backup | `false` | `true` |
| `remote_type` | Remote type: `rclone` or `local` | `rclone` | `local` |
| `rclone_remote` | Name of rclone remote | `""` | `"gdrive"` |
| `rclone_path` | Path on remote storage | `"scooper_backups"` | `"backups/scooper"` |
| `local_backup_path` | Local directory for backups | `""` | `"/mnt/backups/scooper"` |
| `backup_media` | Enable media asset backups | `true` | `false` |
| `backup_database` | Enable database backups | `true` | `false` |
| `retention_days` | Days to keep backups | `30` | `90` |
| `compress_backups` | Compress media backups | `true` | `false` |

### Command Line Configuration

```bash
# Show current configuration
python3 scripts/backup_media.py config

# Set a configuration value
python3 scripts/backup_media.py config-set remote_enabled true
python3 scripts/backup_media.py config-set rclone_remote mygdrive
python3 scripts/backup_media.py config-set retention_days 60
```

## Disaster Recovery

### Complete System Restore

1. **Install Scooper CMS** on a new server
2. **Copy backup files** from your backup location
3. **Restore database**:
   ```bash
   python3 scripts/backup_db.py restore /path/to/backup.db
   ```
4. **Restore media**:
   ```bash
   python3 scripts/backup_media.py restore /path/to/media_backup.tar.gz
   ```
5. **Restart Scooper CMS**

### Verify Backup Integrity

```bash
# Test database backup
sqlite3 backups/scooper_backup_*.db "SELECT COUNT(*) FROM stories;"

# Test media backup
tar -tzf backups/media_backup_*.tar.gz
```

## Security Considerations

1. **Backup File Permissions**: Ensure backup files are readable only by authorized users:
   ```bash
   chmod 600 backups/*.db backups/*.tar.gz
   chmod 700 backups/
   ```

2. **Remote Storage Security**: Use encrypted remote storage when possible.

3. **Configuration File**: The `backup_config.json` file may contain sensitive information. It's added to `.gitignore` by default.

4. **Log Files**: Backup logs may contain sensitive paths. Secure your log directory:
   ```bash
   chmod 700 /var/log/scooper_backup.log
   ```

## Troubleshooting

### Common Issues

1. **rclone not installed**:
   ```
   Error: rclone command not found
   ```
   Solution: Install rclone as described above.

2. **Permission denied**:
   ```
   Permission denied: backups/
   ```
   Solution: `chmod 755 backups/` or run as the correct user.

3. **No space left on device**:
   ```
   No space left on device
   ```
   Solution: Clean up old backups or increase disk space.

4. **rclone configuration not found**:
   ```
   Error: rclone_remote not configured
   ```
   Solution: Run `rclone config` and set up your remote.

### Debug Mode

Run backup scripts with verbose output:

```bash
python3 -v scripts/backup_all.py
```

Or check logs:

```bash
tail -f /var/log/scooper_backup.log
```

## Monitoring

### Simple Monitoring Script

Create a script to check backup status:

```bash
#!/bin/bash
# check_backups.sh

BACKUP_DIR="/path/to/scooper/backups"

# Check for recent database backup
LATEST_DB=$(ls -t "$BACKUP_DIR"/scooper_backup_*.db 2>/dev/null | head -1)
if [ -z "$LATEST_DB" ]; then
    echo "WARNING: No database backup found"
    exit 1
fi

# Check if backup is recent (within 24 hours)
DB_AGE=$(( $(date +%s) - $(stat -c %Y "$LATEST_DB") ))
if [ $DB_AGE -gt 86400 ]; then
    echo "WARNING: Database backup is older than 24 hours"
    exit 1
fi

# Check for media backup
LATEST_MEDIA=$(ls -t "$BACKUP_DIR"/media_backup_*.tar.gz 2>/dev/null | head -1)
if [ -z "$LATEST_MEDIA" ]; then
    echo "WARNING: No media backup found"
    exit 1
fi

echo "Backups are healthy"
exit 0
```

Then add to cron:

```bash
# Check backups every 6 hours
0 */6 * * * /bin/bash /path/to/check_backups.sh
```

## Performance Optimization

For large upload directories, consider:

1. **Exclude large files**: Modify the backup script to skip very large files if needed.
2. **Incremental backups**: Use rclone's sync instead of copy for incremental updates.
3. **Compression level**: Adjust tar compression level (currently gzip default).

## Migration from Existing Setup

If you already have database backups running:

1. **Keep existing database backups**: The new system will create separate media backups.
2. **Update cron job**: Replace your existing database backup cron with the new `backup_all.py` script.
3. **Test both systems**: Run both old and new backups in parallel for a few days to verify.

## Examples

### Example 1: Daily Local Backups
```bash
# Edit crontab
crontab -e

# Add this line
0 2 * * * /usr/bin/python3 /home/user/scooper/scripts/backup_all.py
```

### Example 2: Hourly Backups to Google Drive
```bash
# Configure rclone
rclone config
# (Set up Google Drive remote named "gdrive")

# Configure Scooper
python3 scripts/backup_media.py config-set remote_enabled true
python3 scripts/backup_media.py config-set rclone_remote gdrive
python3 scripts/backup_media.py config-set rclone_path scooper-cms-backups

# Set up cron
0 * * * * /usr/bin/python3 /home/user/scooper/scripts/backup_all.py
```

### Example 3: Weekly Full Backup, Daily Incremental
```bash
# Weekly full backup (Sunday at 2 AM)
0 2 * * 0 /usr/bin/python3 /home/user/scooper/scripts/backup_all.py

# Daily database-only backup (other days at 2 AM)
0 2 * * 1-6 /usr/bin/python3 /home/user/scooper/scripts/backup_db.py backup
```

## Support

For issues with:
- **rclone**: See https://rclone.org/docs/
- **Cron**: See `man crontab` or https://crontab.guru/
- **Python**: Ensure Python 3.6+ is installed

---

**Note**: Always test your backup and restore procedures regularly to ensure they work when needed.