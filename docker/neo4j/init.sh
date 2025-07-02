#!/bin/bash

# Neo4j initialization script for Bot Provisional
# This script runs all Cypher initialization scripts in the correct order

set -e  # Exit on error

echo "Starting Neo4j initialization for Bot Provisional..."

# Configuration
NEO4J_HOST=${NEO4J_HOST:-localhost}
NEO4J_PORT=${NEO4J_PORT:-7687}
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-neo4j}
SCRIPT_DIR="/var/lib/neo4j/import"
MAX_RETRIES=30
RETRY_DELAY=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for Neo4j to be ready
wait_for_neo4j() {
    log_info "Waiting for Neo4j to be ready..."
    
    local counter=0
    while [ $counter -lt $MAX_RETRIES ]; do
        if cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1" > /dev/null 2>&1; then
            log_success "Neo4j is ready!"
            return 0
        fi
        
        log_info "Waiting for Neo4j... ($counter/$MAX_RETRIES)"
        sleep $RETRY_DELAY
        ((counter++))
    done
    
    log_error "Neo4j failed to start within $((MAX_RETRIES * RETRY_DELAY)) seconds"
    return 1
}

# Function to check if initialization has already been completed
check_initialization_status() {
    log_info "Checking if Neo4j is already initialized..."
    
    local result
    result=$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (marker:ProcedureMarker {id: 'neo4j_procedures_loaded'}) RETURN count(marker) AS count" \
        --format plain 2>/dev/null | tail -n +2 || echo "0")
    
    if [ "$result" = "1" ]; then
        log_success "Neo4j is already initialized"
        return 0
    else
        log_info "Neo4j needs initialization"
        return 1
    fi
}

# Function to execute a Cypher script
execute_cypher_script() {
    local script_file="$1"
    local script_name=$(basename "$script_file" .cypher)
    
    log_info "Executing script: $script_name"
    
    if [ ! -f "$script_file" ]; then
        log_error "Script file not found: $script_file"
        return 1
    fi
    
    # Execute the script
    if cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f "$script_file"; then
        log_success "Script executed successfully: $script_name"
        return 0
    else
        log_error "Script execution failed: $script_name"
        return 1
    fi
}

# Function to verify initialization
verify_initialization() {
    log_info "Verifying Neo4j initialization..."
    
    # Check constraints
    local constraint_count
    constraint_count=$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "SHOW CONSTRAINTS YIELD name RETURN count(name) AS count" \
        --format plain 2>/dev/null | tail -n +2 || echo "0")
    
    if [ "$constraint_count" -gt "0" ]; then
        log_success "✓ Constraints created ($constraint_count constraints)"
    else
        log_warning "✗ No constraints found"
        return 1
    fi
    
    # Check indexes
    local index_count
    index_count=$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "SHOW INDEXES YIELD name RETURN count(name) AS count" \
        --format plain 2>/dev/null | tail -n +2 || echo "0")
    
    if [ "$index_count" -gt "0" ]; then
        log_success "✓ Indexes created ($index_count indexes)"
    else
        log_warning "✗ No indexes found"
        return 1
    fi
    
    # Check initial nodes
    local user_count
    user_count=$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (u:User) RETURN count(u) AS count" \
        --format plain 2>/dev/null | tail -n +2 || echo "0")
    
    if [ "$user_count" -gt "0" ]; then
        log_success "✓ Initial users created ($user_count users)"
    else
        log_warning "✗ No users found"
        return 1
    fi
    
    # Check topics
    local topic_count
    topic_count=$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (t:Topic) RETURN count(t) AS count" \
        --format plain 2>/dev/null | tail -n +2 || echo "0")
    
    if [ "$topic_count" -gt "0" ]; then
        log_success "✓ Initial topics created ($topic_count topics)"
    else
        log_warning "✗ No topics found" 
        return 1
    fi
    
    # Check procedure marker
    local marker_count
    marker_count=$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (marker:ProcedureMarker) RETURN count(marker) AS count" \
        --format plain 2>/dev/null | tail -n +2 || echo "0")
    
    if [ "$marker_count" -gt "0" ]; then
        log_success "✓ Procedure marker found"
    else
        log_warning "✗ Procedure marker not found"
        return 1
    fi
    
    log_success "All verification checks passed!"
    return 0
}

# Function to display graph statistics
display_statistics() {
    log_info "Displaying Neo4j graph statistics..."
    
    echo ""
    echo "=== Node Counts ==="
    cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (n) RETURN labels(n)[0] AS node_type, count(n) AS count ORDER BY count DESC" \
        --format table 2>/dev/null || log_warning "Could not retrieve node statistics"
    
    echo ""
    echo "=== Relationship Counts ==="
    cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH ()-[r]->() RETURN type(r) AS relationship_type, count(r) AS count ORDER BY count DESC" \
        --format table 2>/dev/null || log_warning "Could not retrieve relationship statistics"
    
    echo ""
    echo "=== Constraint Count ==="
    cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "SHOW CONSTRAINTS YIELD name RETURN count(name) AS constraint_count" \
        --format table 2>/dev/null || log_warning "Could not retrieve constraint count"
    
    echo ""
    echo "=== Index Count ==="
    cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "SHOW INDEXES YIELD name RETURN count(name) AS index_count" \
        --format table 2>/dev/null || log_warning "Could not retrieve index count"
}

# Main initialization function
main() {
    log_info "Bot Provisional Neo4j Initialization"
    log_info "======================================"
    
    # Wait for Neo4j to be available
    if ! wait_for_neo4j; then
        log_error "Cannot proceed without Neo4j connection"
        exit 1
    fi
    
    # Check if already initialized
    if check_initialization_status; then
        log_info "Skipping initialization (already completed)"
        display_statistics
        exit 0
    fi
    
    # List of scripts to execute in order
    local scripts=(
        "$SCRIPT_DIR/01_constraints.cypher"
        "$SCRIPT_DIR/02_initial_nodes.cypher"
        "$SCRIPT_DIR/03_procedures.cypher"
    )
    
    # Execute scripts in order
    log_info "Executing initialization scripts..."
    for script in "${scripts[@]}"; do
        if ! execute_cypher_script "$script"; then
            log_error "Initialization failed at script: $(basename "$script")"
            exit 1
        fi
    done
    
    # Verify initialization
    if verify_initialization; then
        log_success "Neo4j initialization completed successfully!"
        display_statistics
        
        log_info ""
        log_info "Next steps:"
        log_info "1. Start the application services"
        log_info "2. Check the Neo4j browser at http://localhost:7474"
        log_info "3. Run connection tests with: python scripts/check_connections.py"
        
        exit 0
    else
        log_error "Initialization verification failed"
        exit 1
    fi
}

# Handle script interruption
trap 'log_warning "Script interrupted by user"; exit 130' INT TERM

# Execute main function
main "$@"