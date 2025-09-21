#!/bin/bash

# Artisan Platform Backup and Restore Script
# This script handles database backups, file storage backups, and disaster recovery

set -e

# Configuration
BACKUP_DIR="/backups"
S3_BACKUP_BUCKET="artisan-platform-backups"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_DB="${POSTGRES_DB:-artisan_platform}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

backup_database() {
    log "Starting database backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/postgres_backup_$timestamp.sql"
    
    # Create database dump
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --verbose \
        --clean \
        --no-owner \
        --no-privileges \
        > "$backup_file"
    
    if [ $? -eq 0 ]; then
        log "Database backup completed: $backup_file"
        
        # Compress backup
        gzip "$backup_file"
        backup_file="${backup_file}.gz"
        
        # Upload to S3
        aws s3 cp "$backup_file" "s3://$S3_BACKUP_BUCKET/database/" --storage-class STANDARD_IA
        
        log "Database backup uploaded to S3"
        
        # Keep only last 7 days of local backups
        find "$BACKUP_DIR" -name "postgres_backup_*.sql.gz" -mtime +7 -delete
        
        return 0
    else
        error "Database backup failed"
    fi
}

backup_redis() {
    log "Starting Redis backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/redis_backup_$timestamp.rdb"
    
    # Create Redis backup
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --rdb "$backup_file"
    
    if [ $? -eq 0 ]; then
        log "Redis backup completed: $backup_file"
        
        # Compress backup
        gzip "$backup_file"
        backup_file="${backup_file}.gz"
        
        # Upload to S3
        aws s3 cp "$backup_file" "s3://$S3_BACKUP_BUCKET/redis/" --storage-class STANDARD_IA
        
        log "Redis backup uploaded to S3"
        
        # Keep only last 7 days of local backups
        find "$BACKUP_DIR" -name "redis_backup_*.rdb.gz" -mtime +7 -delete
        
        return 0
    else
        error "Redis backup failed"
    fi
}

backup_files() {
    log "Starting file storage backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    # Sync uploaded files to backup bucket
    aws s3 sync s3://artisan-platform-files s3://$S3_BACKUP_BUCKET/files/$timestamp/ \
        --storage-class GLACIER \
        --exclude "*.tmp" \
        --exclude "temp/*"
    
    if [ $? -eq 0 ]; then
        log "File storage backup completed"
        return 0
    else
        error "File storage backup failed"
    fi
}

restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "Please specify backup file to restore"
    fi
    
    log "Starting database restore from: $backup_file"
    
    # Download from S3 if it's an S3 path
    if [[ "$backup_file" == s3://* ]]; then
        local local_file="$BACKUP_DIR/$(basename $backup_file)"
        aws s3 cp "$backup_file" "$local_file"
        backup_file="$local_file"
    fi
    
    # Decompress if needed
    if [[ "$backup_file" == *.gz ]]; then
        gunzip "$backup_file"
        backup_file="${backup_file%.gz}"
    fi
    
    # Restore database
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        < "$backup_file"
    
    if [ $? -eq 0 ]; then
        log "Database restore completed successfully"
    else
        error "Database restore failed"
    fi
}

restore_redis() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "Please specify Redis backup file to restore"
    fi
    
    log "Starting Redis restore from: $backup_file"
    
    # Download from S3 if it's an S3 path
    if [[ "$backup_file" == s3://* ]]; then
        local local_file="$BACKUP_DIR/$(basename $backup_file)"
        aws s3 cp "$backup_file" "$local_file"
        backup_file="$local_file"
    fi
    
    # Decompress if needed
    if [[ "$backup_file" == *.gz ]]; then
        gunzip "$backup_file"
        backup_file="${backup_file%.gz}"
    fi
    
    # Stop Redis, restore file, start Redis
    warn "This will stop Redis service temporarily"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl stop redis
        cp "$backup_file" /var/lib/redis/dump.rdb
        chown redis:redis /var/lib/redis/dump.rdb
        systemctl start redis
        log "Redis restore completed successfully"
    else
        log "Redis restore cancelled"
    fi
}

disaster_recovery() {
    log "Starting disaster recovery procedure..."
    
    # Check if this is a disaster recovery scenario
    if [ ! -f "/tmp/disaster_recovery_mode" ]; then
        warn "This will perform a full system restore. This should only be used in disaster recovery scenarios."
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Disaster recovery cancelled"
            exit 0
        fi
        touch "/tmp/disaster_recovery_mode"
    fi
    
    # Get latest backups
    local latest_db_backup=$(aws s3 ls s3://$S3_BACKUP_BUCKET/database/ | sort | tail -n 1 | awk '{print $4}')
    local latest_redis_backup=$(aws s3 ls s3://$S3_BACKUP_BUCKET/redis/ | sort | tail -n 1 | awk '{print $4}')
    
    if [ -z "$latest_db_backup" ]; then
        error "No database backup found for disaster recovery"
    fi
    
    log "Latest database backup: $latest_db_backup"
    log "Latest Redis backup: $latest_redis_backup"
    
    # Restore database
    restore_database "s3://$S3_BACKUP_BUCKET/database/$latest_db_backup"
    
    # Restore Redis if backup exists
    if [ -n "$latest_redis_backup" ]; then
        restore_redis "s3://$S3_BACKUP_BUCKET/redis/$latest_redis_backup"
    fi
    
    # Restore file storage (this syncs the entire backup)
    log "Restoring file storage..."
    aws s3 sync s3://$S3_BACKUP_BUCKET/files/ s3://artisan-platform-files/ \
        --exclude "*.tmp" \
        --exclude "temp/*"
    
    log "Disaster recovery completed successfully"
    rm -f "/tmp/disaster_recovery_mode"
}

health_check() {
    log "Performing system health check..."
    
    # Check database connectivity
    PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB"
    if [ $? -eq 0 ]; then
        log "✓ Database is healthy"
    else
        error "✗ Database is not accessible"
    fi
    
    # Check Redis connectivity
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null
    if [ $? -eq 0 ]; then
        log "✓ Redis is healthy"
    else
        warn "✗ Redis is not accessible"
    fi
    
    # Check S3 connectivity
    aws s3 ls s3://$S3_BACKUP_BUCKET/ > /dev/null
    if [ $? -eq 0 ]; then
        log "✓ S3 backup bucket is accessible"
    else
        error "✗ S3 backup bucket is not accessible"
    fi
    
    # Check disk space
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 80 ]; then
        log "✓ Disk usage is healthy ($disk_usage%)"
    else
        warn "✗ Disk usage is high ($disk_usage%)"
    fi
    
    log "Health check completed"
}

# Main script logic
case "$1" in
    "backup-db")
        backup_database
        ;;
    "backup-redis")
        backup_redis
        ;;
    "backup-files")
        backup_files
        ;;
    "backup-all")
        backup_database
        backup_redis
        backup_files
        ;;
    "restore-db")
        restore_database "$2"
        ;;
    "restore-redis")
        restore_redis "$2"
        ;;
    "disaster-recovery")
        disaster_recovery
        ;;
    "health-check")
        health_check
        ;;
    *)
        echo "Usage: $0 {backup-db|backup-redis|backup-files|backup-all|restore-db|restore-redis|disaster-recovery|health-check}"
        echo ""
        echo "Commands:"
        echo "  backup-db          - Backup PostgreSQL database"
        echo "  backup-redis       - Backup Redis data"
        echo "  backup-files       - Backup file storage"
        echo "  backup-all         - Backup everything"
        echo "  restore-db <file>  - Restore database from backup"
        echo "  restore-redis <file> - Restore Redis from backup"
        echo "  disaster-recovery  - Full system restore from latest backups"
        echo "  health-check       - Check system health"
        exit 1
        ;;
esac