# Scripts Usage Documentation

This document provides comprehensive usage instructions for all development and maintenance scripts in the Bot Provisional project.

## Overview

The project includes several utility scripts designed to facilitate development, testing, and maintenance workflows. These scripts are located in the `scripts/` directory and can be executed directly or through the Makefile.

## Scripts Directory Structure

```
scripts/
├── setup_dev.sh              # Development environment setup
├── check_connections.py      # Database connectivity testing
├── init_databases.py         # Database initialization
├── migrate_database.py       # Database migration management
├── validate_docker.py        # Docker environment validation
├── populate_test_data.py     # Test data population
├── reset_environment.py      # Environment reset and cleanup
└── health_check.py           # Comprehensive system health checks
```

## Individual Script Documentation

### 1. setup_dev.sh

**Purpose**: Sets up the complete development environment from scratch.

**Usage**:
```bash
# Make executable and run
chmod +x scripts/setup_dev.sh
./scripts/setup_dev.sh

# Or through Makefile
make setup
```

**What it does**:
- Checks Python version (requires ≥3.10)
- Creates and activates virtual environment
- Upgrades pip and installs dependencies
- Creates necessary directories (logs, data)
- Creates .env file from .env.example
- Downloads spaCy language model
- Tests basic imports and logging
- Optionally starts Docker services and initializes databases

**Options**: Interactive prompts for database startup.

---

### 2. check_connections.py

**Purpose**: Tests connectivity to all databases and external services.

**Usage**:
```bash
# Basic connectivity check
python scripts/check_connections.py

# Quiet mode (minimal output)
python scripts/check_connections.py --quiet

# Through Makefile
make health-quiet
```

**What it checks**:
- PostgreSQL connection and basic queries
- Redis connection and operations
- Neo4j connection and authentication
- Service response times

**Exit codes**:
- 0: All connections successful
- 1: One or more connections failed

---

### 3. init_databases.py

**Purpose**: Initializes database schemas and basic configuration.

**Usage**:
```bash
# Initialize all databases
python scripts/init_databases.py

# Initialize specific database
python scripts/init_databases.py --database postgres
python scripts/init_databases.py --database redis
python scripts/init_databases.py --database neo4j

# Force recreation (drops existing data)
python scripts/init_databases.py --force

# Through Makefile
make db-init
```

**What it does**:
- Creates PostgreSQL tables and indexes
- Sets up Redis key spaces and configurations
- Creates Neo4j constraints and indexes
- Validates schema creation

**⚠️ Warning**: `--force` flag will destroy existing data.

---

### 4. migrate_database.py

**Purpose**: Manages database schema migrations and versioning.

**Usage**:
```bash
# Run pending migrations
python scripts/migrate_database.py --action migrate

# Check migration status
python scripts/migrate_database.py --action status

# Rollback last migration
python scripts/migrate_database.py --action rollback

# Create new migration
python scripts/migrate_database.py --action create --name "add_user_preferences"

# Through Makefile
make db-migrate
make db-migrate-status
```

**Migration actions**:
- `migrate`: Apply pending migrations
- `status`: Show current migration state
- `rollback`: Revert last migration
- `create`: Generate new migration template

---

### 5. validate_docker.py

**Purpose**: Validates Docker environment and service configurations.

**Usage**:
```bash
# Validate Docker setup
python scripts/validate_docker.py

# Check specific service
python scripts/validate_docker.py --service postgres

# Validate docker-compose files
python scripts/validate_docker.py --compose-only

# Through Makefile
make validate
```

**What it validates**:
- Docker and docker-compose installation
- Service definitions in docker-compose files
- Port availability
- Volume mounts and permissions
- Environment variable configuration

---

### 6. populate_test_data.py

**Purpose**: Populates databases with realistic test data for development.

**Usage**:
```bash
# Populate all databases with test data
python scripts/populate_test_data.py

# Clear existing test data first
python scripts/populate_test_data.py --clear

# Show test data statistics only
python scripts/populate_test_data.py --stats-only

# Quiet mode
python scripts/populate_test_data.py --quiet

# Through Makefile
make db-populate
make db-populate-stats
```

**Test data includes**:
- 3 sample users (2 active, 1 inactive)
- Sample conversations and responses
- Cached context data in Redis
- Knowledge graph with users, topics, and relationships
- Realistic timestamps and metadata

**Options**:
- `--clear`: Remove existing test data before populating
- `--stats-only`: Show statistics without modification
- `--quiet`: Suppress verbose output

---

### 7. reset_environment.py

**Purpose**: Resets the development environment to a clean state.

**Usage**:
```bash
# Full environment reset (interactive confirmation)
python scripts/reset_environment.py

# Reset specific components
python scripts/reset_environment.py --no-databases
python scripts/reset_environment.py --no-logs
python scripts/reset_environment.py --no-cache
python scripts/reset_environment.py --no-docker

# Remove and recreate virtual environment
python scripts/reset_environment.py --remove-venv

# Show environment status only
python scripts/reset_environment.py --status-only

# Through Makefile
make reset              # Full reset
make reset-soft         # Skip Docker restart
make status            # Status only
```

**Reset operations**:
- **Docker services**: Stop, remove volumes, restart
- **Databases**: Clear all data (preserves schema)
- **Logs**: Remove all log files
- **Cache**: Remove Python cache and temporary files
- **Virtual environment**: Optionally recreate from scratch

**⚠️ Warning**: This is a destructive operation. Always confirm before proceeding.

---

### 8. health_check.py

**Purpose**: Performs comprehensive health checks on all system components.

**Usage**:
```bash
# Complete health check
python scripts/health_check.py

# Skip Docker checks
python scripts/health_check.py --no-docker

# JSON output format
python scripts/health_check.py --output json

# Run specific check only
python scripts/health_check.py --check databases
python scripts/health_check.py --check system

# Quiet mode
python scripts/health_check.py --quiet

# Through Makefile
make health
```

**Health check categories**:
1. **System Resources**: CPU, memory, disk usage
2. **Python Environment**: Version, virtual env, dependencies
3. **Configuration**: Files, environment variables
4. **Docker Services**: Container status, service health
5. **Databases**: Connectivity, versions, basic operations
6. **File Permissions**: Script executability, directory structure
7. **Logging System**: Configuration, log files, functionality

**Output formats**:
- `text`: Human-readable status report
- `json`: Machine-readable structured data

**Exit codes**:
- 0: All checks healthy
- 1: One or more checks unhealthy
- 2: One or more checks show warnings

## Makefile Integration

All scripts are integrated into the Makefile for convenient access:

### Setup Commands
```bash
make setup          # Run setup_dev.sh
make install        # Install Python dependencies
```

### Development Commands
```bash
make dev            # Start development environment
make test           # Run all tests
make test-db        # Run database tests
```

### Database Commands
```bash
make db-init        # Initialize databases
make db-migrate     # Run migrations
make db-populate    # Add test data
make db-reset       # Reset databases
```

### Monitoring Commands
```bash
make health         # Comprehensive health check
make status         # Environment status
make logs           # Show application logs
```

### Cleanup Commands
```bash
make clean          # Clean cache files
make reset          # Full environment reset
```

## Best Practices

### Development Workflow

1. **Initial Setup**:
   ```bash
   make setup
   # Follow prompts for database startup
   ```

2. **Daily Development**:
   ```bash
   make health         # Check system status
   make dev           # Start development environment
   ```

3. **Testing Changes**:
   ```bash
   make test          # Run test suite
   make db-populate   # Refresh test data if needed
   ```

4. **Environment Issues**:
   ```bash
   make health        # Diagnose problems
   make reset-soft    # Soft reset if needed
   ```

### Troubleshooting

#### Common Issues

**"Permission denied" errors**:
```bash
# Make scripts executable
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

**Database connection failures**:
```bash
# Check Docker services
make health --check docker

# Restart services
make docker-clean
make docker
```

**Missing dependencies**:
```bash
# Reinstall requirements
make install

# Or full reset
make reset
make setup
```

#### Script Dependencies

Before running scripts, ensure:
1. Virtual environment is activated
2. Dependencies are installed (`pip install -r requirements.txt`)
3. Docker services are running (for database scripts)
4. Environment variables are configured (`.env` file)

### Security Considerations

- Never commit `.env` files with real credentials
- Use `--quiet` flag in production environments
- Review test data before using in production-like environments
- Regularly rotate database passwords and API keys

### Performance Notes

- Health checks may take 30-60 seconds for complete evaluation
- Database reset operations can take several minutes
- Test data population scales with the amount of sample data
- Docker operations depend on system resources and network speed

## Error Handling

All scripts include comprehensive error handling:

- **Exit codes**: Follow Unix conventions (0=success, >0=error)
- **Logging**: Structured logging with appropriate levels
- **Rollback**: Database operations can be rolled back on failure
- **Validation**: Input validation and dependency checking
- **Recovery**: Guidance for manual recovery when automated fixes fail

## Contributing

When adding new scripts:

1. Follow the existing naming convention
2. Include comprehensive help text (`--help`)
3. Add Makefile integration
4. Update this documentation
5. Include error handling and logging
6. Add tests for script functionality

## Support

For issues with scripts:

1. Run health check: `make health`
2. Check logs: `make logs`
3. Review environment status: `make status`
4. Consult this documentation
5. Check project README.md for additional guidance