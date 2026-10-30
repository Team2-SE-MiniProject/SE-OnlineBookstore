#!/bin/sh

set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

mkdir -p "$BACKUP_DIR"

echo "Database backup service started."

while true; do
    TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/online_bookstore_$TIMESTAMP.dump"

    echo "Starting database backup: $BACKUP_FILE"

    if pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -Fc \
        -f "$BACKUP_FILE"; then

        echo "Backup completed successfully."

        find "$BACKUP_DIR" \
            -type f \
            -name "online_bookstore_*.dump" \
            -mtime +"$BACKUP_RETENTION_DAYS" \
            -delete
    else
        echo "ERROR: Database backup failed."
        rm -f "$BACKUP_FILE"
    fi

    echo "Next backup in $BACKUP_INTERVAL_SECONDS seconds."
    sleep "$BACKUP_INTERVAL_SECONDS"
done
