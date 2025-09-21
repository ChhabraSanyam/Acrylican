#!/bin/bash

# Rollback script for Artisan Promotion Platform
# This script handles rollback to the previous working version

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_FILE="$PROJECT_ROOT/logs/rollback.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

# Create necessary directories
mkdir -p "$(dirname "$LOG_FILE")"

# Function to get the latest backup
get_latest_backup() {
    local latest_backup=$(ls -t "$BACKUP_DIR"/db_backup_*.sql 2>/dev/null | head -n1)
    if [[ -z "$latest_backup" ]]; then
        error "No database backup found for rollback"
    fi
    echo "$latest_backup"
}

# Function to rollback database
rollback_database() {
    log "Rolling back database..."
    
    local backup_file=$(get_latest_backup)
    log "Using backup file: $backup_file"
    
    # Load environment variables
    source "$PROJECT_ROOT/.env.production"
    
    # Create a backup of current state before rollback
    local current_backup="$BACKUP_DIR/pre_rollback_backup_$(date +%Y%m%d_%H%M%S).sql"
    if docker ps | grep -q "artisan-platform-db"; then
        docker exec artisan-platform-db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$current_backup"
        log "Current database backed up to: $current_backup"
    fi
    
    # Restore from backup
    docker exec -i artisan-platform-db psql -U "$POSTGRES_USER" "$POSTGRES_DB" < "$backup_file"
    
    success "Database rollback completed"
}

# Function to rollback application
rollback_application() {
    log "Rolling back application..."
    
    cd "$PROJECT_ROOT"
    
    # Get the previous commit
    local previous_commit=$(git log --oneline -n 2 | tail -n 1 | cut -d' ' -f1)
    log "Rolling back to commit: $previous_commit"
    
    # Checkout previous commit
    git checkout "$previous_commit"
    
    # Rebuild and redeploy
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml build
    docker-compose -f docker-compose.prod.yml up -d
    
    success "Application rollback completed"
}

# Function to verify rollback
verify_rollback() {
    log "Verifying rollback..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Verification attempt $attempt/$max_attempts"
        
        # Check backend health
        if curl -f http://localhost:8000/health &> /dev/null; then
            success "Backend is responding after rollback"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error "Rollback verification failed after $max_attempts attempts"
        fi
        
        sleep 10
        ((attempt++))
    done
    
    # Check frontend health
    if curl -f http://localhost:80/health &> /dev/null; then
        success "Frontend is responding after rollback"
    else
        error "Frontend verification failed after rollback"
    fi
}

# Main rollback function
main() {
    log "Starting rollback of Artisan Promotion Platform..."
    
    # Parse command line arguments
    SKIP_DB_ROLLBACK=false
    FORCE_ROLLBACK=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-db)
                SKIP_DB_ROLLBACK=true
                shift
                ;;
            --force)
                FORCE_ROLLBACK=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-db    Skip database rollback"
                echo "  --force      Force rollback without confirmation"
                echo "  --help       Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
    
    # Confirmation prompt
    if [[ "$FORCE_ROLLBACK" != true ]]; then
        echo -e "${YELLOW}WARNING: This will rollback the application to the previous version.${NC}"
        echo -e "${YELLOW}This action cannot be undone automatically.${NC}"
        read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Rollback cancelled by user"
            exit 0
        fi
    fi
    
    # Run rollback steps
    if [[ "$SKIP_DB_ROLLBACK" != true ]]; then
        rollback_database
    fi
    
    rollback_application
    verify_rollback
    
    success "Rollback completed successfully!"
    log "Application has been rolled back to the previous version"
    log "Please monitor the application and investigate the issues that caused the rollback"
}

# Run main function with all arguments
main "$@"