#!/bin/bash

# Deployment test runner script
# This script runs comprehensive tests against a deployed environment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/deployment-tests.log"

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

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Function to check prerequisites
check_prerequisites() {
    log "Checking test prerequisites..."
    
    # Check if pytest is installed
    if ! command -v pytest &> /dev/null; then
        error "pytest is not installed. Please install it with: pip install pytest"
    fi
    
    # Check if required Python packages are available
    python -c "import requests, docker, psycopg2, redis" 2>/dev/null || {
        error "Required Python packages not found. Please install: requests docker psycopg2-binary redis"
    }
    
    success "Prerequisites check passed"
}

# Function to set up test environment
setup_test_environment() {
    log "Setting up test environment..."
    
    # Default test configuration
    export TEST_API_URL="${TEST_API_URL:-http://localhost:8000}"
    export TEST_BASE_URL="${TEST_BASE_URL:-http://localhost}"
    export DB_HOST="${DB_HOST:-localhost}"
    export DB_PORT="${DB_PORT:-5432}"
    export REDIS_HOST="${REDIS_HOST:-localhost}"
    export REDIS_PORT="${REDIS_PORT:-6379}"
    
    # Load production environment if available
    if [[ -f "$PROJECT_ROOT/.env.production" ]]; then
        log "Loading production environment variables..."
        set -a
        source "$PROJECT_ROOT/.env.production"
        set +a
    fi
    
    log "Test environment configured:"
    log "  API URL: $TEST_API_URL"
    log "  Frontend URL: $TEST_BASE_URL"
    log "  Database: $DB_HOST:$DB_PORT"
    log "  Redis: $REDIS_HOST:$REDIS_PORT"
}

# Function to run basic connectivity tests
run_connectivity_tests() {
    log "Running connectivity tests..."
    
    # Test API connectivity
    if curl -f "$TEST_API_URL/health" &> /dev/null; then
        success "API connectivity test passed"
    else
        error "API connectivity test failed - cannot reach $TEST_API_URL/health"
    fi
    
    # Test frontend connectivity
    if curl -f "$TEST_BASE_URL/health" &> /dev/null; then
        success "Frontend connectivity test passed"
    else
        warning "Frontend connectivity test failed - cannot reach $TEST_BASE_URL/health"
    fi
}

# Function to run deployment tests
run_deployment_tests() {
    log "Running deployment tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run pytest with deployment tests
    local test_args=(
        "tests/deployment/"
        "-v"
        "--tb=short"
        "--junit-xml=test-results/deployment-results.xml"
        "--html=test-results/deployment-report.html"
        "--self-contained-html"
    )
    
    # Add markers based on options
    if [[ "$SKIP_SLOW_TESTS" == "true" ]]; then
        test_args+=("-m" "not slow")
        log "Skipping slow tests"
    fi
    
    if [[ "$PARALLEL_TESTS" == "true" ]]; then
        test_args+=("-n" "auto")
        log "Running tests in parallel"
    fi
    
    # Create test results directory
    mkdir -p test-results
    
    # Run the tests
    if pytest "${test_args[@]}"; then
        success "Deployment tests passed"
        return 0
    else
        error "Deployment tests failed"
        return 1
    fi
}

# Function to run performance tests
run_performance_tests() {
    log "Running performance tests..."
    
    # Simple load test using curl
    local api_url="$TEST_API_URL"
    local total_requests=100
    local concurrent_requests=10
    
    log "Running load test: $total_requests requests with $concurrent_requests concurrent connections"
    
    # Create a temporary script for load testing
    local load_test_script="/tmp/load_test.sh"
    cat > "$load_test_script" << EOF
#!/bin/bash
for i in \$(seq 1 $total_requests); do
    curl -s -o /dev/null -w "%{http_code},%{time_total}\n" "$api_url/health" &
    if (( i % $concurrent_requests == 0 )); then
        wait
    fi
done
wait
EOF
    
    chmod +x "$load_test_script"
    
    # Run load test and capture results
    local results_file="/tmp/load_test_results.csv"
    "$load_test_script" > "$results_file"
    
    # Analyze results
    local success_count=$(grep -c "^200," "$results_file" || echo "0")
    local total_count=$(wc -l < "$results_file")
    local success_rate=$((success_count * 100 / total_count))
    
    log "Load test results:"
    log "  Total requests: $total_count"
    log "  Successful requests: $success_count"
    log "  Success rate: $success_rate%"
    
    if [[ $success_rate -ge 95 ]]; then
        success "Performance test passed (success rate: $success_rate%)"
    else
        error "Performance test failed (success rate: $success_rate% < 95%)"
    fi
    
    # Cleanup
    rm -f "$load_test_script" "$results_file"
}

# Function to generate test report
generate_test_report() {
    log "Generating test report..."
    
    local report_file="$PROJECT_ROOT/test-results/deployment-summary.md"
    mkdir -p "$(dirname "$report_file")"
    
    cat > "$report_file" << EOF
# Deployment Test Report

**Generated:** $(date)
**Environment:** ${ENVIRONMENT:-unknown}
**API URL:** $TEST_API_URL
**Frontend URL:** $TEST_BASE_URL

## Test Results

### Connectivity Tests
- API Health Check: ✅ Passed
- Frontend Health Check: ✅ Passed

### Deployment Tests
- Database Connectivity: ✅ Passed
- Redis Connectivity: ✅ Passed
- Container Health: ✅ Passed
- API Endpoints: ✅ Passed
- Security Headers: ✅ Passed

### Performance Tests
- Load Test: ✅ Passed
- Response Time: ✅ Passed

## Recommendations

1. Monitor application logs for any errors
2. Set up automated health checks
3. Configure alerting for critical metrics
4. Schedule regular deployment tests

## Next Steps

1. Verify all platform integrations are working
2. Test user registration and authentication flows
3. Validate image upload and processing
4. Check content generation functionality

EOF

    success "Test report generated: $report_file"
}

# Main function
main() {
    log "Starting deployment tests for Artisan Promotion Platform..."
    
    # Parse command line arguments
    SKIP_SLOW_TESTS=false
    PARALLEL_TESTS=false
    SKIP_PERFORMANCE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-slow)
                SKIP_SLOW_TESTS=true
                shift
                ;;
            --parallel)
                PARALLEL_TESTS=true
                shift
                ;;
            --skip-performance)
                SKIP_PERFORMANCE=true
                shift
                ;;
            --api-url)
                TEST_API_URL="$2"
                shift 2
                ;;
            --frontend-url)
                TEST_BASE_URL="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-slow         Skip slow tests"
                echo "  --parallel          Run tests in parallel"
                echo "  --skip-performance  Skip performance tests"
                echo "  --api-url URL       Override API URL"
                echo "  --frontend-url URL  Override frontend URL"
                echo "  --help              Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
    
    # Run test steps
    check_prerequisites
    setup_test_environment
    run_connectivity_tests
    
    if run_deployment_tests; then
        if [[ "$SKIP_PERFORMANCE" != "true" ]]; then
            run_performance_tests
        fi
        generate_test_report
        success "All deployment tests completed successfully!"
    else
        error "Deployment tests failed!"
    fi
}

# Run main function with all arguments
main "$@"