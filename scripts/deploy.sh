#!/bin/bash

# Production deployment script for Artisan Promotion Platform
# This script handles the complete deployment process

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_FILE="$PROJECT_ROOT/logs/deployment.log"

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
mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

# Function to check prerequisites
check_prerequisites() {
    log "Checking deployment prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker first."
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not available. Please install Docker Compose."
    fi
    
    # Check if environment file exists
    if [[ ! -f "$PROJECT_ROOT/.env.production" ]]; then
        error "Production environment file not found. Please create .env.production from .env.production.example"
    fi
    
    success "Prerequisites check passed"
}

# Function to backup database
backup_database() {
    log "Creating database backup..."
    
    local backup_file="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # Load environment variables
    source "$PROJECT_ROOT/.env.production"
    
    # Create backup using docker exec
    if docker ps | grep -q "artisan-platform-db"; then
        docker exec artisan-platform-db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$backup_file"
        success "Database backup created: $backup_file"
    else
        warning "Database container not running, skipping backup"
    fi
}

# Function to build images
build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build backend image
    log "Building backend image..."
    docker build -t artisan-platform-backend:latest ./backend
    
    # Build frontend image
    log "Building frontend image..."
    docker build -t artisan-platform-frontend:latest ./frontend
    
    success "Docker images built successfully"
}

# Function to run database migrations
run_migrations() {
    log "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    
    # Run migrations using docker-compose
    docker-compose -f docker-compose.prod.yml run --rm migrate
    
    success "Database migrations completed"
}

# Function to deploy services
deploy_services() {
    log "Deploying services..."
    
    cd "$PROJECT_ROOT"
    
    # Pull latest images if using registry
    # docker-compose -f docker-compose.prod.yml pull
    
    # Deploy with zero-downtime strategy
    docker-compose -f docker-compose.prod.yml up -d --remove-orphans
    
    success "Services deployed successfully"
}

# Function to run health checks
run_health_checks() {
    log "Running health checks..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Health check attempt $attempt/$max_attempts"
        
        # Check backend health
        if curl -f http://localhost:8000/health &> /dev/null; then
            success "Backend health check passed"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error "Health checks failed after $max_attempts attempts"
        fi
        
        sleep 10
        ((attempt++))
    done
    
    # Check frontend health
    if curl -f http://localhost:80/health &> /dev/null; then
        success "Frontend health check passed"
    else
        error "Frontend health check failed"
    fi
}

# Function to cleanup old resources
cleanup() {
    log "Cleaning up old resources..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove old backups (keep last 7 days)
    find "$BACKUP_DIR" -name "db_backup_*.sql" -mtime +7 -delete
    
    success "Cleanup completed"
}

# Main deployment function
main() {
    log "Starting deployment of Artisan Promotion Platform..."
    
    # Parse command line arguments
    SKIP_BACKUP=false
    SKIP_HEALTH_CHECK=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-backup        Skip database backup"
                echo "  --skip-health-check  Skip health checks"
                echo "  --help              Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
    
    # Run deployment steps
    check_prerequisites
    
    if [[ "$SKIP_BACKUP" != true ]]; then
        backup_database
    fi
    
    build_images
    run_migrations
    deploy_services
    
    if [[ "$SKIP_HEALTH_CHECK" != true ]]; then
        run_health_checks
    fi
    
    cleanup
    
    success "Deployment completed successfully!"
    log "Application is now running at:"
    log "  - Frontend: http://localhost:80"
    log "  - Backend API: http://localhost:8000"
    log "  - API Documentation: http://localhost:8000/docs"
}

# Run main function with all arguments
main "$@"