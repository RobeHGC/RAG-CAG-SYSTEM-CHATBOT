#!/bin/bash

# Bot Provisional - Development Setup Script
# This script sets up the development environment for the project

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Header
echo "========================================"
echo "Bot Provisional - Development Setup"
echo "========================================"
echo ""

# Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    print_status "Python $python_version found (>= $required_version required)"
else
    print_error "Python $python_version found but >= $required_version is required"
    exit 1
fi

# Create virtual environment
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Skipping creation..."
else
    print_status "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate || {
    print_error "Failed to activate virtual environment"
    exit 1
}

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p data

# Create .env file if it doesn't exist
if [ -f ".env" ]; then
    print_warning ".env file already exists. Skipping creation..."
else
    print_status "Creating .env file from .env.example..."
    cp .env.example .env
    print_warning "Please edit .env file with your configuration values!"
fi

# Download spaCy language model (if needed)
print_status "Checking spaCy language model..."
python -c "import spacy; spacy.load('es_core_news_sm')" 2>/dev/null || {
    print_status "Downloading Spanish spaCy model..."
    python -m spacy download es_core_news_sm
}

# Run basic import test
print_status "Running basic import test..."
python -c "from src.common.config import settings; print('✓ Config module imported successfully')" || {
    print_error "Failed to import config module"
    exit 1
}

# Create logs directory and test logging
print_status "Testing logging configuration..."
python -c "
import logging
from src.common.config import setup_logging
logger = logging.getLogger('setup.test')
logger.info('Logging system working correctly')
print('✓ Logging configured successfully')
" || {
    print_error "Failed to configure logging"
    exit 1
}

# Summary
echo ""
echo "========================================"
echo "Setup completed successfully!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Configure your .env file with the required values"
echo "3. Set up your databases (PostgreSQL, Redis, Neo4j)"
echo "4. Run tests: pytest"
echo "5. Start developing!"
echo ""
print_warning "Don't forget to configure your Telegram API credentials in .env!"