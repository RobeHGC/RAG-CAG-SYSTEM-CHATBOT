#!/bin/bash

# Redis initialization script for Bot Provisional
# This script runs the Lua initialization and sets up Redis for the chatbot

set -e  # Exit on error

echo "Starting Redis initialization for Bot Provisional..."

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
timeout=30
counter=0

while [ $counter -lt $timeout ]; do
    if redis-cli ping > /dev/null 2>&1; then
        echo "Redis is ready!"
        break
    fi
    
    echo "Waiting for Redis... ($counter/$timeout)"
    sleep 1
    ((counter++))
done

if [ $counter -eq $timeout ]; then
    echo "ERROR: Redis failed to start within $timeout seconds"
    exit 1
fi

# Check if Redis is already initialized
if redis-cli GET init:completed > /dev/null 2>&1; then
    init_status=$(redis-cli GET init:completed)
    if [ "$init_status" = "true" ]; then
        echo "Redis is already initialized, skipping initialization"
        exit 0
    fi
fi

echo "Running Redis initialization script..."

# Execute the Lua initialization script
redis-cli --eval /usr/local/etc/redis/init.lua

if [ $? -eq 0 ]; then
    echo "Redis initialization completed successfully!"
    
    # Verify initialization by checking a few key structures
    echo "Verifying initialization..."
    
    # Check if app metadata was created
    app_name=$(redis-cli HGET app:metadata name)
    if [ "$app_name" = "Bot Provisional" ]; then
        echo "✓ App metadata initialized"
    else
        echo "✗ App metadata initialization failed"
        exit 1
    fi
    
    # Check if namespaces were created
    namespace_count=$(redis-cli HLEN app:namespaces)
    if [ "$namespace_count" -gt "0" ]; then
        echo "✓ Namespaces initialized ($namespace_count namespaces)"
    else
        echo "✗ Namespace initialization failed"
        exit 1
    fi
    
    # Check if configuration was set
    default_ttl=$(redis-cli HGET config:cache default_ttl)
    if [ "$default_ttl" = "3600" ]; then
        echo "✓ Cache configuration initialized"
    else
        echo "✗ Cache configuration initialization failed"
        exit 1
    fi
    
    echo "All verification checks passed!"
    echo "Redis is ready for Bot Provisional"
    
else
    echo "ERROR: Redis initialization script failed"
    exit 1
fi