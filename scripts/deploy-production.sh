#!/bin/bash

# Production Deployment Script for Artisan Platform
# This script deploys the complete production environment with monitoring and scaling

set -e

# Configuration
NAMESPACE="artisan-platform"
MONITORING_NAMESPACE="monitoring"
CLUSTER_NAME="artisan-platform-prod"
REGION="us-west-2"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if kubectl is installed and configured
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed"
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        error "helm is not installed"
    fi
    
    # Check if aws cli is installed
    if ! command -v aws &> /dev/null; then
        error "aws cli is not installed"
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
    fi
    
    log "Prerequisites check passed"
}

# Create namespaces
create_namespaces() {
    log "Creating namespaces..."
    
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace $MONITORING_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Label namespaces
    kubectl label namespace $NAMESPACE name=$NAMESPACE --overwrite
    kubectl label namespace $MONITORING_NAMESPACE name=$MONITORING_NAMESPACE --overwrite
    
    log "Namespaces created successfully"
}

# Deploy secrets
deploy_secrets() {
    log "Deploying secrets..."
    
    # Check if secrets exist
    if ! kubectl get secret postgres-credentials -n $NAMESPACE &> /dev/null; then
        warn "postgres-credentials secret not found. Please create it manually."
        info "kubectl create secret generic postgres-credentials -n $NAMESPACE \\"
        info "  --from-literal=host=postgres-cluster-rw \\"
        info "  --from-literal=database=artisan_platform \\"
        info "  --from-literal=username=app_user \\"
        info "  --from-literal=password=<secure-password>"
    fi
    
    if ! kubectl get secret redis-credentials -n $NAMESPACE &> /dev/null; then
        warn "redis-credentials secret not found. Please create it manually."
        info "kubectl create secret generic redis-credentials -n $NAMESPACE \\"
        info "  --from-literal=host=redis-cluster \\"
        info "  --from-literal=port=6379 \\"
        info "  --from-literal=url=redis://redis-cluster:6379"
    fi
    
    if ! kubectl get secret app-secrets -n $NAMESPACE &> /dev/null; then
        warn "app-secrets secret not found. Please create it manually."
        info "kubectl create secret generic app-secrets -n $NAMESPACE \\"
        info "  --from-literal=jwt-secret=<jwt-secret> \\"
        info "  --from-literal=session-secret=<session-secret>"
    fi
    
    log "Secrets deployment completed"
}

# Deploy monitoring stack
deploy_monitoring() {
    log "Deploying monitoring stack..."
    
    # Add Helm repositories
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Deploy Prometheus stack
    if ! helm list -n $MONITORING_NAMESPACE | grep -q prometheus; then
        log "Installing Prometheus stack..."
        helm install prometheus prometheus-community/kube-prometheus-stack \
            --namespace $MONITORING_NAMESPACE \
            --values k8s/production/prometheus-values.yaml \
            --wait
    else
        log "Upgrading Prometheus stack..."
        helm upgrade prometheus prometheus-community/kube-prometheus-stack \
            --namespace $MONITORING_NAMESPACE \
            --values k8s/production/prometheus-values.yaml \
            --wait
    fi
    
    # Deploy Loki stack
    if ! helm list -n $MONITORING_NAMESPACE | grep -q loki; then
        log "Installing Loki stack..."
        helm install loki grafana/loki-stack \
            --namespace $MONITORING_NAMESPACE \
            --values k8s/production/loki-values.yaml \
            --wait
    else
        log "Upgrading Loki stack..."
        helm upgrade loki grafana/loki-stack \
            --namespace $MONITORING_NAMESPACE \
            --values k8s/production/loki-values.yaml \
            --wait
    fi
    
    # Apply custom monitoring resources
    kubectl apply -f k8s/production/alertmanager-config.yaml
    kubectl apply -f k8s/production/prometheus-rules.yaml
    kubectl apply -f k8s/production/service-monitors.yaml
    
    log "Monitoring stack deployed successfully"
}

# Deploy database
deploy_database() {
    log "Deploying database..."
    
    # Apply PostgreSQL cluster configuration
    kubectl apply -f k8s/production/postgres-cluster.yaml
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    kubectl wait --for=condition=Ready pod/postgres-cluster-1 -n $NAMESPACE --timeout=300s
    
    log "Database deployed successfully"
}

# Deploy Redis
deploy_redis() {
    log "Deploying Redis cluster..."
    
    # Apply Redis cluster configuration
    kubectl apply -f k8s/production/redis-cluster.yaml
    
    # Wait for Redis to be ready
    log "Waiting for Redis cluster to be ready..."
    kubectl wait --for=condition=Ready pod -l app=redis-cluster -n $NAMESPACE --timeout=300s
    
    log "Redis cluster deployed successfully"
}

# Deploy application
deploy_application() {
    log "Deploying application..."
    
    # Apply security policies
    kubectl apply -f k8s/production/security-policies.yaml
    
    # Deploy application components
    kubectl apply -f k8s/production/deployment.yaml
    
    # Wait for deployments to be ready
    log "Waiting for application deployments to be ready..."
    kubectl rollout status deployment/artisan-platform-backend -n $NAMESPACE --timeout=300s
    kubectl rollout status deployment/artisan-platform-frontend -n $NAMESPACE --timeout=300s
    kubectl rollout status deployment/queue-worker -n $NAMESPACE --timeout=300s
    
    log "Application deployed successfully"
}

# Deploy autoscaling
deploy_autoscaling() {
    log "Deploying autoscaling configuration..."
    
    # Apply HPA configurations
    kubectl apply -f k8s/production/hpa.yaml
    
    # Apply cluster autoscaler
    kubectl apply -f k8s/production/cluster-autoscaler.yaml
    
    # Verify HPA is working
    kubectl get hpa -n $NAMESPACE
    
    log "Autoscaling deployed successfully"
}

# Deploy backup system
deploy_backup_system() {
    log "Deploying backup system..."
    
    # Apply backup CronJobs
    kubectl apply -f k8s/production/backup-cronjob.yaml
    
    # Verify backup jobs are scheduled
    kubectl get cronjobs -n $NAMESPACE
    
    log "Backup system deployed successfully"
}

# Deploy ingress
deploy_ingress() {
    log "Deploying ingress configuration..."
    
    # Apply ingress configuration
    kubectl apply -f k8s/production/security-policies.yaml
    
    # Wait for ingress to get external IP
    log "Waiting for ingress to get external IP..."
    kubectl get ingress artisan-platform-ingress -n $NAMESPACE -w --timeout=300s
    
    log "Ingress deployed successfully"
}

# Run health checks
run_health_checks() {
    log "Running health checks..."
    
    # Check pod status
    kubectl get pods -n $NAMESPACE
    kubectl get pods -n $MONITORING_NAMESPACE
    
    # Check services
    kubectl get services -n $NAMESPACE
    
    # Check ingress
    kubectl get ingress -n $NAMESPACE
    
    # Test application endpoints
    if kubectl get ingress artisan-platform-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' &> /dev/null; then
        INGRESS_HOST=$(kubectl get ingress artisan-platform-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
        log "Testing application health at $INGRESS_HOST"
        
        # Test health endpoint
        if curl -f -s "https://$INGRESS_HOST/monitoring/health" > /dev/null; then
            log "✓ Application health check passed"
        else
            warn "✗ Application health check failed"
        fi
        
        # Test metrics endpoint
        if curl -f -s "https://$INGRESS_HOST/monitoring/metrics" > /dev/null; then
            log "✓ Metrics endpoint accessible"
        else
            warn "✗ Metrics endpoint not accessible"
        fi
    else
        warn "Ingress not ready yet, skipping endpoint tests"
    fi
    
    log "Health checks completed"
}

# Setup monitoring dashboards
setup_dashboards() {
    log "Setting up monitoring dashboards..."
    
    # Get Grafana admin password
    GRAFANA_PASSWORD=$(kubectl get secret prometheus-grafana -n $MONITORING_NAMESPACE -o jsonpath="{.data.admin-password}" | base64 --decode)
    
    log "Grafana admin password: $GRAFANA_PASSWORD"
    log "Access Grafana at: https://grafana.artisan-platform.com"
    log "Default dashboards will be available after first login"
    
    log "Monitoring dashboards setup completed"
}

# Main deployment function
deploy_production() {
    log "Starting production deployment for Artisan Platform..."
    
    check_prerequisites
    create_namespaces
    deploy_secrets
    deploy_monitoring
    deploy_database
    deploy_redis
    deploy_application
    deploy_autoscaling
    deploy_backup_system
    deploy_ingress
    run_health_checks
    setup_dashboards
    
    log "Production deployment completed successfully!"
    log ""
    log "Next steps:"
    log "1. Configure DNS to point to the ingress load balancer"
    log "2. Set up SSL certificates (cert-manager should handle this automatically)"
    log "3. Configure external monitoring alerts"
    log "4. Run load tests to verify scaling"
    log "5. Set up backup verification procedures"
    log ""
    log "Important URLs:"
    log "- Application: https://app.artisan-platform.com"
    log "- API: https://api.artisan-platform.com"
    log "- Grafana: https://grafana.artisan-platform.com"
    log "- Prometheus: https://prometheus.artisan-platform.com"
}

# Rollback function
rollback_deployment() {
    log "Rolling back deployment..."
    
    # Rollback application deployments
    kubectl rollout undo deployment/artisan-platform-backend -n $NAMESPACE
    kubectl rollout undo deployment/artisan-platform-frontend -n $NAMESPACE
    kubectl rollout undo deployment/queue-worker -n $NAMESPACE
    
    # Wait for rollback to complete
    kubectl rollout status deployment/artisan-platform-backend -n $NAMESPACE
    kubectl rollout status deployment/artisan-platform-frontend -n $NAMESPACE
    kubectl rollout status deployment/queue-worker -n $NAMESPACE
    
    log "Rollback completed"
}

# Cleanup function
cleanup_deployment() {
    warn "This will delete the entire production deployment!"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Cleaning up deployment..."
        
        # Delete application resources
        kubectl delete namespace $NAMESPACE --ignore-not-found=true
        
        # Delete monitoring (optional)
        read -p "Delete monitoring stack as well? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kubectl delete namespace $MONITORING_NAMESPACE --ignore-not-found=true
        fi
        
        log "Cleanup completed"
    else
        log "Cleanup cancelled"
    fi
}

# Script usage
usage() {
    echo "Usage: $0 {deploy|rollback|cleanup|health-check}"
    echo ""
    echo "Commands:"
    echo "  deploy       - Deploy complete production environment"
    echo "  rollback     - Rollback application to previous version"
    echo "  cleanup      - Remove entire deployment (DESTRUCTIVE)"
    echo "  health-check - Run health checks on existing deployment"
    exit 1
}

# Main script logic
case "$1" in
    "deploy")
        deploy_production
        ;;
    "rollback")
        rollback_deployment
        ;;
    "cleanup")
        cleanup_deployment
        ;;
    "health-check")
        run_health_checks
        ;;
    *)
        usage
        ;;
esac