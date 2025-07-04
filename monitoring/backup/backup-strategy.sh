#!/bin/bash

# VictoriaMetrics Backup Strategy Implementation
# Implements tiered backup with verification and restoration capabilities

set -euo pipefail

# Configuration
VM_URL="${VM_URL:-http://victoriametrics:8428}"
BACKUP_ROOT="${BACKUP_ROOT:-/data/backups/monitoring}"
S3_BUCKET="${S3_BUCKET:-docaiche-monitoring-backups}"
RETENTION_HOT_HOURS="${RETENTION_HOT_HOURS:-48}"
RETENTION_DAILY_DAYS="${RETENTION_DAILY_DAYS:-7}"
RETENTION_WEEKLY_WEEKS="${RETENTION_WEEKLY_WEEKS:-4}"
RETENTION_MONTHLY_MONTHS="${RETENTION_MONTHLY_MONTHS:-12}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-/etc/monitoring/backup-key}"
NOTIFICATION_WEBHOOK="${NOTIFICATION_WEBHOOK:-}"

# Backup directories
HOT_BACKUP_DIR="$BACKUP_ROOT/hot"
DAILY_BACKUP_DIR="$BACKUP_ROOT/daily"
WEEKLY_BACKUP_DIR="$BACKUP_ROOT/weekly"
MONTHLY_BACKUP_DIR="$BACKUP_ROOT/monthly"
STAGING_DIR="$BACKUP_ROOT/staging"

# Create directories
mkdir -p "$HOT_BACKUP_DIR" "$DAILY_BACKUP_DIR" "$WEEKLY_BACKUP_DIR" "$MONTHLY_BACKUP_DIR" "$STAGING_DIR"

# Logging
LOG_FILE="$BACKUP_ROOT/backup.log"
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    send_notification "error" "Backup failed: $1"
    exit 1
}

# Send notification via webhook
send_notification() {
    local status=$1
    local message=$2
    
    if [ -n "$NOTIFICATION_WEBHOOK" ]; then
        curl -s -X POST "$NOTIFICATION_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
            || log "Warning: Failed to send notification"
    fi
}

# Create snapshot
create_snapshot() {
    local snapshot_type=$1
    log "Creating $snapshot_type snapshot..."
    
    # Request snapshot creation
    local response=$(curl -sf "$VM_URL/snapshot/create" || echo '{"error": "Failed to create snapshot"}')
    local snapshot_name=$(echo "$response" | jq -r '.snapshot // empty')
    
    if [ -z "$snapshot_name" ]; then
        error_exit "Failed to create snapshot: $(echo "$response" | jq -r '.error // "Unknown error"')"
    fi
    
    log "Snapshot created: $snapshot_name"
    echo "$snapshot_name"
}

# Delete snapshot
delete_snapshot() {
    local snapshot_name=$1
    log "Deleting snapshot: $snapshot_name"
    
    curl -sf "$VM_URL/snapshot/delete?snapshot=$snapshot_name" || log "Warning: Failed to delete snapshot $snapshot_name"
}

# Compress and encrypt backup
compress_and_encrypt() {
    local source_path=$1
    local dest_path=$2
    local backup_type=$3
    
    log "Compressing and encrypting backup..."
    
    # Create metadata
    local metadata_file="$STAGING_DIR/metadata.json"
    cat > "$metadata_file" <<EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "vm_version": "$(curl -s $VM_URL/api/v1/status/buildinfo | jq -r .data.version)",
    "source_path": "$source_path",
    "host": "$(hostname)",
    "retention_policy": {
        "hot_hours": $RETENTION_HOT_HOURS,
        "daily_days": $RETENTION_DAILY_DAYS,
        "weekly_weeks": $RETENTION_WEEKLY_WEEKS,
        "monthly_months": $RETENTION_MONTHLY_MONTHS
    }
}
EOF
    
    # Compress with metadata
    tar -czf - -C "$(dirname "$source_path")" "$(basename "$source_path")" "$metadata_file" | \
        openssl enc -aes-256-cbc -pbkdf2 -pass file:"$ENCRYPTION_KEY" > "$dest_path"
    
    # Calculate checksum
    sha256sum "$dest_path" > "$dest_path.sha256"
    
    log "Backup compressed and encrypted: $dest_path"
}

# Verify backup integrity
verify_backup() {
    local backup_path=$1
    log "Verifying backup integrity: $backup_path"
    
    # Check checksum
    if [ -f "$backup_path.sha256" ]; then
        if sha256sum -c "$backup_path.sha256" > /dev/null 2>&1; then
            log "✓ Checksum verification passed"
        else
            error_exit "Checksum verification failed for $backup_path"
        fi
    else
        log "Warning: No checksum file found for $backup_path"
    fi
    
    # Try to decrypt and list contents
    if openssl enc -aes-256-cbc -pbkdf2 -d -pass file:"$ENCRYPTION_KEY" -in "$backup_path" | tar -tzf - > /dev/null 2>&1; then
        log "✓ Backup decryption and structure verification passed"
        return 0
    else
        error_exit "Failed to decrypt or read backup $backup_path"
    fi
}

# Upload to S3 (optional offsite backup)
upload_to_s3() {
    local backup_path=$1
    local s3_path=$2
    
    if command -v aws >/dev/null 2>&1; then
        log "Uploading to S3: $s3_path"
        
        aws s3 cp "$backup_path" "s3://$S3_BUCKET/$s3_path" \
            --storage-class GLACIER \
            --metadata "backup-type=$backup_type,timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            || log "Warning: Failed to upload to S3"
        
        # Also upload checksum
        [ -f "$backup_path.sha256" ] && \
            aws s3 cp "$backup_path.sha256" "s3://$S3_BUCKET/$s3_path.sha256" || true
    else
        log "AWS CLI not available, skipping S3 upload"
    fi
}

# Hot backup (every 6 hours)
hot_backup() {
    log "=== Starting hot backup ==="
    
    local snapshot_name=$(create_snapshot "hot")
    local backup_name="hot_$(date +%Y%m%d_%H%M%S).backup"
    local backup_path="$HOT_BACKUP_DIR/$backup_name"
    
    # Get snapshot path in container
    local snapshot_path="/snapshots/$snapshot_name"
    
    # Export snapshot data
    docker exec victoriametrics tar -cf - "$snapshot_path" > "$STAGING_DIR/snapshot.tar"
    
    # Compress and encrypt
    compress_and_encrypt "$STAGING_DIR/snapshot.tar" "$backup_path" "hot"
    
    # Cleanup staging
    rm -f "$STAGING_DIR/snapshot.tar"
    
    # Delete snapshot
    delete_snapshot "$snapshot_name"
    
    # Verify backup
    verify_backup "$backup_path"
    
    # Clean old hot backups
    find "$HOT_BACKUP_DIR" -name "hot_*.backup" -mmin +$((RETENTION_HOT_HOURS * 60)) -delete
    find "$HOT_BACKUP_DIR" -name "hot_*.backup.sha256" -mmin +$((RETENTION_HOT_HOURS * 60)) -delete
    
    log "Hot backup completed: $backup_path"
    send_notification "success" "Hot backup completed successfully"
}

# Daily backup (incremental)
daily_backup() {
    log "=== Starting daily backup ==="
    
    local snapshot_name=$(create_snapshot "daily")
    local backup_name="daily_$(date +%Y%m%d).backup"
    local backup_path="$DAILY_BACKUP_DIR/$backup_name"
    
    # Export snapshot data
    local snapshot_path="/snapshots/$snapshot_name"
    docker exec victoriametrics tar -cf - "$snapshot_path" > "$STAGING_DIR/snapshot.tar"
    
    # Compress and encrypt
    compress_and_encrypt "$STAGING_DIR/snapshot.tar" "$backup_path" "daily"
    
    # Cleanup
    rm -f "$STAGING_DIR/snapshot.tar"
    delete_snapshot "$snapshot_name"
    
    # Verify backup
    verify_backup "$backup_path"
    
    # Upload to S3 if configured
    upload_to_s3 "$backup_path" "daily/$backup_name"
    
    # Clean old daily backups
    find "$DAILY_BACKUP_DIR" -name "daily_*.backup" -mtime +$RETENTION_DAILY_DAYS -delete
    find "$DAILY_BACKUP_DIR" -name "daily_*.backup.sha256" -mtime +$RETENTION_DAILY_DAYS -delete
    
    log "Daily backup completed: $backup_path"
    send_notification "success" "Daily backup completed successfully"
}

# Weekly backup (full)
weekly_backup() {
    log "=== Starting weekly backup ==="
    
    local snapshot_name=$(create_snapshot "weekly")
    local backup_name="weekly_$(date +%Y%m%d).backup"
    local backup_path="$WEEKLY_BACKUP_DIR/$backup_name"
    
    # Export full data including configuration
    local snapshot_path="/snapshots/$snapshot_name"
    docker exec victoriametrics tar -cf - "$snapshot_path" /victoria-metrics-data/metadata > "$STAGING_DIR/snapshot.tar"
    
    # Compress and encrypt
    compress_and_encrypt "$STAGING_DIR/snapshot.tar" "$backup_path" "weekly"
    
    # Cleanup
    rm -f "$STAGING_DIR/snapshot.tar"
    delete_snapshot "$snapshot_name"
    
    # Verify backup
    verify_backup "$backup_path"
    
    # Upload to S3
    upload_to_s3 "$backup_path" "weekly/$backup_name"
    
    # Clean old weekly backups
    find "$WEEKLY_BACKUP_DIR" -name "weekly_*.backup" -mtime +$((RETENTION_WEEKLY_WEEKS * 7)) -delete
    find "$WEEKLY_BACKUP_DIR" -name "weekly_*.backup.sha256" -mtime +$((RETENTION_WEEKLY_WEEKS * 7)) -delete
    
    log "Weekly backup completed: $backup_path"
    send_notification "success" "Weekly backup completed successfully"
}

# Monthly backup (full with archive)
monthly_backup() {
    log "=== Starting monthly backup ==="
    
    local snapshot_name=$(create_snapshot "monthly")
    local backup_name="monthly_$(date +%Y%m).backup"
    local backup_path="$MONTHLY_BACKUP_DIR/$backup_name"
    
    # Export complete data directory
    local snapshot_path="/snapshots/$snapshot_name"
    docker exec victoriametrics tar -cf - "$snapshot_path" /victoria-metrics-data > "$STAGING_DIR/snapshot.tar"
    
    # Add additional metadata and documentation
    cat > "$STAGING_DIR/backup-info.txt" <<EOF
Monthly Backup Information
========================
Date: $(date)
VictoriaMetrics Version: $(curl -s $VM_URL/api/v1/status/buildinfo | jq -r .data.version)
Total Series: $(curl -s "$VM_URL/api/v1/query?query=vm_rows" | jq -r '.data.result[0].value[1]')
Storage Size: $(curl -s "$VM_URL/api/v1/query?query=vm_data_size_bytes" | jq -r '.data.result[0].value[1]' | numfmt --to=iec)
Snapshot: $snapshot_name

Recovery Instructions:
1. Decrypt: openssl enc -aes-256-cbc -pbkdf2 -d -pass file:$ENCRYPTION_KEY -in $backup_name -out snapshot.tar
2. Extract: tar -xf snapshot.tar
3. Restore: Copy extracted data to VictoriaMetrics data directory
4. Start VictoriaMetrics with restored data
EOF
    
    tar -rf "$STAGING_DIR/snapshot.tar" -C "$STAGING_DIR" backup-info.txt
    
    # Compress and encrypt
    compress_and_encrypt "$STAGING_DIR/snapshot.tar" "$backup_path" "monthly"
    
    # Cleanup
    rm -f "$STAGING_DIR/snapshot.tar" "$STAGING_DIR/backup-info.txt"
    delete_snapshot "$snapshot_name"
    
    # Verify backup
    verify_backup "$backup_path"
    
    # Upload to S3 with Glacier Deep Archive for long-term storage
    if command -v aws >/dev/null 2>&1; then
        aws s3 cp "$backup_path" "s3://$S3_BUCKET/monthly/$backup_name" \
            --storage-class DEEP_ARCHIVE \
            --metadata "backup-type=monthly,timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    fi
    
    # Clean old monthly backups (keep for 1 year)
    find "$MONTHLY_BACKUP_DIR" -name "monthly_*.backup" -mtime +$((RETENTION_MONTHLY_MONTHS * 30)) -delete
    find "$MONTHLY_BACKUP_DIR" -name "monthly_*.backup.sha256" -mtime +$((RETENTION_MONTHLY_MONTHS * 30)) -delete
    
    log "Monthly backup completed: $backup_path"
    send_notification "success" "Monthly backup completed successfully"
}

# Restore from backup
restore_backup() {
    local backup_path=$1
    local restore_path=${2:-"/tmp/vm-restore"}
    
    log "=== Starting restore from $backup_path ==="
    
    # Verify backup first
    verify_backup "$backup_path"
    
    # Create restore directory
    mkdir -p "$restore_path"
    
    # Decrypt and extract
    log "Decrypting and extracting backup..."
    openssl enc -aes-256-cbc -pbkdf2 -d -pass file:"$ENCRYPTION_KEY" -in "$backup_path" | \
        tar -xzf - -C "$restore_path"
    
    log "Backup extracted to: $restore_path"
    log "To complete restoration:"
    log "1. Stop VictoriaMetrics"
    log "2. Copy data from $restore_path to VictoriaMetrics data directory"
    log "3. Start VictoriaMetrics"
    
    send_notification "info" "Backup extracted successfully to $restore_path"
}

# List available backups
list_backups() {
    log "=== Available Backups ==="
    
    echo -e "\nHot Backups (last 48 hours):"
    ls -lh "$HOT_BACKUP_DIR"/*.backup 2>/dev/null || echo "No hot backups found"
    
    echo -e "\nDaily Backups (last 7 days):"
    ls -lh "$DAILY_BACKUP_DIR"/*.backup 2>/dev/null || echo "No daily backups found"
    
    echo -e "\nWeekly Backups (last 4 weeks):"
    ls -lh "$WEEKLY_BACKUP_DIR"/*.backup 2>/dev/null || echo "No weekly backups found"
    
    echo -e "\nMonthly Backups (last 12 months):"
    ls -lh "$MONTHLY_BACKUP_DIR"/*.backup 2>/dev/null || echo "No monthly backups found"
    
    # Check S3 if available
    if command -v aws >/dev/null 2>&1; then
        echo -e "\nS3 Backups:"
        aws s3 ls "s3://$S3_BUCKET/" --recursive | grep ".backup$" | tail -20
    fi
}

# Main function
main() {
    local action=${1:-help}
    
    case "$action" in
        hot)
            hot_backup
            ;;
        daily)
            daily_backup
            ;;
        weekly)
            weekly_backup
            ;;
        monthly)
            monthly_backup
            ;;
        restore)
            restore_backup "${2:-}" "${3:-}"
            ;;
        list)
            list_backups
            ;;
        verify)
            verify_backup "${2:-}"
            ;;
        help|*)
            cat <<EOF
Usage: $0 {hot|daily|weekly|monthly|restore|list|verify|help}

Commands:
  hot       - Create hot backup (6-hour snapshots)
  daily     - Create daily incremental backup
  weekly    - Create weekly full backup
  monthly   - Create monthly archive backup
  restore   - Restore from backup file
  list      - List available backups
  verify    - Verify backup integrity
  help      - Show this help message

Examples:
  $0 hot                                    # Create hot backup
  $0 restore /path/to/backup.tar.gz.enc    # Restore from backup
  $0 verify /path/to/backup.tar.gz.enc     # Verify backup integrity
EOF
            ;;
    esac
}

# Run main function
main "$@"