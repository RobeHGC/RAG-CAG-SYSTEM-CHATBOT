#!/bin/bash

# AI Companion Monitoring Stack Management Script
# This script manages the complete monitoring infrastructure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.monitoring.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running or not accessible"
        exit 1
    fi
}

# Check if Docker Compose is available
check_compose() {
    if ! command -v docker-compose > /dev/null 2>&1 && ! docker compose version > /dev/null 2>&1; then
        error "Docker Compose is not available"
        exit 1
    fi
}

# Determine the docker compose command to use
get_compose_cmd() {
    if docker compose version > /dev/null 2>&1; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

# Create necessary directories
setup_directories() {
    log "Creating monitoring directories..."
    
    mkdir -p "$PROJECT_DIR/monitoring/prometheus"
    mkdir -p "$PROJECT_DIR/monitoring/alertmanager"
    mkdir -p "$PROJECT_DIR/monitoring/grafana/provisioning/datasources"
    mkdir -p "$PROJECT_DIR/monitoring/grafana/provisioning/dashboards"
    mkdir -p "$PROJECT_DIR/monitoring/grafana/dashboards"
    mkdir -p "$PROJECT_DIR/profiling_results"
    mkdir -p "$PROJECT_DIR/logs"
    
    log "Directories created successfully"
}

# Start the monitoring stack
start_monitoring() {
    local compose_cmd=$(get_compose_cmd)
    
    log "Starting AI Companion monitoring stack..."
    
    # Create directories first
    setup_directories
    
    # Start the services
    $compose_cmd -f "$COMPOSE_FILE" up -d
    
    if [ $? -eq 0 ]; then
        log "Monitoring stack started successfully!"
        info "Services accessible at:"
        info "  • Grafana: http://localhost:3000 (admin/ai-companion-grafana)"
        info "  • Prometheus: http://localhost:9090"
        info "  • Alertmanager: http://localhost:9093"
        info "  • Elasticsearch: http://localhost:9200"
        info "  • Kibana: http://localhost:5601"
        info "  • Jaeger: http://localhost:16686"
        info "  • cAdvisor: http://localhost:8080"
    else
        error "Failed to start monitoring stack"
        exit 1
    fi
}

# Stop the monitoring stack
stop_monitoring() {
    local compose_cmd=$(get_compose_cmd)
    
    log "Stopping AI Companion monitoring stack..."
    
    $compose_cmd -f "$COMPOSE_FILE" down
    
    if [ $? -eq 0 ]; then
        log "Monitoring stack stopped successfully!"
    else
        error "Failed to stop monitoring stack"
        exit 1
    fi
}

# Restart the monitoring stack
restart_monitoring() {
    log "Restarting AI Companion monitoring stack..."
    stop_monitoring
    sleep 5
    start_monitoring
}

# Show status of monitoring services
status_monitoring() {
    local compose_cmd=$(get_compose_cmd)
    
    log "Monitoring stack status:"
    $compose_cmd -f "$COMPOSE_FILE" ps
}

# Show logs for monitoring services
logs_monitoring() {
    local compose_cmd=$(get_compose_cmd)
    local service=${1:-""}
    
    if [ -n "$service" ]; then
        log "Showing logs for service: $service"
        $compose_cmd -f "$COMPOSE_FILE" logs -f "$service"
    else
        log "Showing logs for all monitoring services:"
        $compose_cmd -f "$COMPOSE_FILE" logs -f
    fi
}

# Clean up monitoring resources
cleanup_monitoring() {
    local compose_cmd=$(get_compose_cmd)
    
    warn "This will remove all monitoring containers and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Cleaning up monitoring stack..."
        $compose_cmd -f "$COMPOSE_FILE" down -v --remove-orphans
        
        # Remove dangling images
        docker image prune -f
        
        log "Cleanup completed!"
    else
        info "Cleanup cancelled"
    fi
}

# Update monitoring stack
update_monitoring() {
    local compose_cmd=$(get_compose_cmd)
    
    log "Updating AI Companion monitoring stack..."
    
    # Pull latest images
    $compose_cmd -f "$COMPOSE_FILE" pull
    
    # Recreate containers with new images
    $compose_cmd -f "$COMPOSE_FILE" up -d --force-recreate
    
    log "Monitoring stack updated successfully!"
}

# Backup monitoring data
backup_monitoring() {
    local backup_dir="$PROJECT_DIR/monitoring_backup_$(date +%Y%m%d_%H%M%S)"
    
    log "Creating backup of monitoring data..."
    
    mkdir -p "$backup_dir"
    
    # Backup Grafana data
    docker cp ai-companion-grafana:/var/lib/grafana "$backup_dir/grafana_data" 2>/dev/null || warn "Could not backup Grafana data"
    
    # Backup Prometheus data
    docker cp ai-companion-prometheus:/prometheus "$backup_dir/prometheus_data" 2>/dev/null || warn "Could not backup Prometheus data"
    
    # Backup configuration files
    cp -r "$PROJECT_DIR/monitoring" "$backup_dir/config"
    
    log "Backup created at: $backup_dir"
}

# Check health of monitoring services
health_check() {
    log "Checking health of monitoring services..."
    
    local services=(
        "prometheus:9090/api/v1/query?query=up"
        "grafana:3000/api/health"
        "alertmanager:9093/api/v1/status"
        "elasticsearch:9200/_cluster/health"
    )
    
    for service in "${services[@]}"; do
        local name=$(echo "$service" | cut -d':' -f1)
        local url="http://localhost:$(echo "$service" | cut -d':' -f2-)"
        
        if curl -s -f "$url" > /dev/null 2>&1; then
            info "✓ $name is healthy"
        else
            warn "✗ $name is not responding"
        fi
    done
}

# Install monitoring dependencies
install_deps() {
    log "Installing monitoring dependencies..."
    
    # Check for required tools
    local missing_tools=()
    
    command -v curl >/dev/null 2>&1 || missing_tools+=("curl")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        warn "Missing tools: ${missing_tools[*]}"
        info "Please install them using your package manager"
        info "Ubuntu/Debian: sudo apt-get install ${missing_tools[*]}"
        info "CentOS/RHEL: sudo yum install ${missing_tools[*]}"
        info "macOS: brew install ${missing_tools[*]}"
    else
        log "All required tools are installed"
    fi
}

# Show help
show_help() {
    echo "AI Companion Monitoring Stack Management"
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start        Start the monitoring stack"
    echo "  stop         Stop the monitoring stack"
    echo "  restart      Restart the monitoring stack"
    echo "  status       Show status of monitoring services"
    echo "  logs [svc]   Show logs (optionally for specific service)"
    echo "  cleanup      Remove all containers and volumes"
    echo "  update       Update monitoring stack to latest images"
    echo "  backup       Create backup of monitoring data"
    echo "  health       Check health of monitoring services"
    echo "  install      Install required dependencies"
    echo "  help         Show this help message"
    echo ""
    echo "Services:"
    echo "  • prometheus     Metrics collection and alerting"
    echo "  • grafana        Metrics visualization"
    echo "  • alertmanager   Alert routing and notification"
    echo "  • elasticsearch  Log storage and search"
    echo "  • kibana         Log visualization"
    echo "  • jaeger         Distributed tracing"
    echo "  • node-exporter  System metrics"
    echo "  • cadvisor       Container metrics"
    echo ""
    echo "Examples:"
    echo "  $0 start                 # Start all monitoring services"
    echo "  $0 logs prometheus       # Show Prometheus logs"
    echo "  $0 health               # Check service health"
}

# Main script logic
main() {
    check_docker
    check_compose
    
    case "${1:-}" in
        start)
            start_monitoring
            ;;
        stop)
            stop_monitoring
            ;;
        restart)
            restart_monitoring
            ;;
        status)
            status_monitoring
            ;;
        logs)
            logs_monitoring "$2"
            ;;
        cleanup)
            cleanup_monitoring
            ;;
        update)
            update_monitoring
            ;;
        backup)
            backup_monitoring
            ;;
        health)
            health_check
            ;;
        install)
            install_deps
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            warn "No command specified"
            show_help
            exit 1
            ;;
        *)
            error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"