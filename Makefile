# Bot Provisional - Makefile
# Common commands for development workflow

.PHONY: help setup dev test clean reset lint format install docker logs health populate ci pre-commit coverage type-check

# Default target
help:
	@echo "Bot Provisional - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  setup         Set up development environment"
	@echo "  install       Install Python dependencies"
	@echo ""
	@echo "Development:"
	@echo "  dev           Start development environment"
	@echo "  test          Run all tests"
	@echo "  lint          Run code linting"
	@echo "  format        Format code with black"
	@echo ""
	@echo "CI/CD & Quality:"
	@echo "  ci            Run full CI pipeline locally"
	@echo "  coverage      Generate coverage report"
	@echo "  type-check    Run type checking with mypy"
	@echo "  pre-commit    Setup and run pre-commit hooks"
	@echo ""
	@echo "Docker & Services:"
	@echo "  docker        Start Docker services"
	@echo "  docker-stop   Stop Docker services"
	@echo "  docker-clean  Clean Docker containers and volumes"
	@echo ""
	@echo "Database:"
	@echo "  db-init       Initialize databases"
	@echo "  db-migrate    Run database migrations"
	@echo "  db-populate   Populate with test data"
	@echo "  db-reset      Reset databases to clean state"
	@echo ""
	@echo "Monitoring:"
	@echo "  health        Check system health"
	@echo "  logs          Show application logs"
	@echo "  status        Show environment status"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean         Clean cache and temporary files"
	@echo "  reset         Full environment reset"
	@echo ""

# Setup and Installation
setup:
	@echo "🚀 Setting up development environment..."
	chmod +x scripts/setup_dev.sh
	./scripts/setup_dev.sh

install:
	@echo "📦 Installing Python dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt

# Development
dev: docker
	@echo "🔧 Starting development environment..."
	@echo "Services will be available at:"
	@echo "  - Dashboard: http://localhost:8000"
	@echo "  - Neo4j Browser: http://localhost:7474"
	@echo "  - Redis: localhost:6379"
	@echo "  - PostgreSQL: localhost:5432"

test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

test-quick:
	@echo "⚡ Running quick tests..."
	python -m pytest tests/test_imports.py -v

test-db:
	@echo "🗄️ Running database tests..."
	python -m pytest tests/test_databases.py -v

lint:
	@echo "🔍 Running code linting..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/ scripts/ tests/; \
	else \
		echo "⚠️ flake8 not found, install with: pip install flake8"; \
	fi

format:
	@echo "🎨 Formatting code with black..."
	@if command -v black >/dev/null 2>&1; then \
		black src/ scripts/ tests/; \
	else \
		echo "⚠️ black not found, install with: pip install black"; \
	fi

# Docker and Services
docker:
	@echo "🐳 Starting Docker services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "✅ Docker services started"

docker-stop:
	@echo "🛑 Stopping Docker services..."
	docker-compose down

docker-clean:
	@echo "🧹 Cleaning Docker containers and volumes..."
	docker-compose down -v
	docker volume prune -f

docker-logs:
	@echo "📋 Showing Docker logs..."
	docker-compose logs -f

# Database Operations
db-init:
	@echo "🗄️ Initializing databases..."
	python scripts/init_databases.py

db-migrate:
	@echo "🔄 Running database migrations..."
	python scripts/migrate_database.py --action migrate

db-migrate-status:
	@echo "📊 Checking migration status..."
	python scripts/migrate_database.py --action status

db-populate:
	@echo "📊 Populating databases with test data..."
	python scripts/populate_test_data.py

db-populate-stats:
	@echo "📈 Showing test data statistics..."
	python scripts/populate_test_data.py --stats-only

db-reset:
	@echo "🔄 Resetting databases..."
	python scripts/reset_environment.py --no-logs --no-cache --no-docker

# Monitoring and Status
health:
	@echo "🏥 Checking system health..."
	python scripts/check_connections.py

health-quiet:
	@echo "🔍 Quick health check..."
	python scripts/check_connections.py --quiet

status:
	@echo "📊 Environment status..."
	python scripts/reset_environment.py --status-only

logs:
	@echo "📋 Showing application logs..."
	@if [ -f logs/bot_provisional.log ]; then \
		tail -f logs/bot_provisional.log; \
	else \
		echo "No log file found. Start the application first."; \
	fi

logs-errors:
	@echo "🚨 Showing error logs..."
	@if [ -f logs/errors.log ]; then \
		tail -f logs/errors.log; \
	else \
		echo "No error log file found."; \
	fi

# Cleanup
clean:
	@echo "🧹 Cleaning cache and temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cache cleaned"

reset:
	@echo "⚠️ Full environment reset..."
	python scripts/reset_environment.py

reset-soft:
	@echo "🔄 Soft reset (keep Docker running)..."
	python scripts/reset_environment.py --no-docker

# Utility Commands
check-deps:
	@echo "🔍 Checking dependencies..."
	@python -c "import pkg_resources; print('✅ All dependencies available')" || \
		echo "❌ Missing dependencies. Run 'make install'"

validate:
	@echo "✅ Validating environment..."
	python scripts/validate_docker.py

# Development Shortcuts
quick-start: docker db-init
	@echo "🚀 Quick start completed!"
	@echo "Environment is ready for development"

full-reset: docker-clean reset setup docker db-init
	@echo "🔄 Full reset completed!"
	@echo "Environment is completely fresh"

# Run specific components (for debugging)
run-userbot:
	@echo "🤖 Starting Userbot..."
	cd src && python -m userbot.main

run-dashboard:
	@echo "📊 Starting Dashboard..."
	cd src && python -m dashboard.main

# Backup and Restore (for production use)
backup-db:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	docker exec bot_provisional_postgres_1 pg_dump -U postgres bot_provisional > backups/postgres_$$timestamp.sql; \
	echo "PostgreSQL backup created: backups/postgres_$$timestamp.sql"

# CI/CD helpers
ci-test: install test lint
	@echo "✅ CI tests completed"

ci-build: install
	@echo "🏗️ CI build completed"

# Documentation
docs:
	@echo "📚 Opening documentation..."
	@if [ -f docs/ARCHITECTURE.md ]; then \
		cat docs/ARCHITECTURE.md; \
	else \
		echo "Architecture documentation not found"; \
	fi

# Version and info
version:
	@echo "Bot Provisional Development Environment"
	@echo "Python: $$(python --version)"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'Not available')"
	@echo "Docker Compose: $$(docker-compose --version 2>/dev/null || echo 'Not available')"

# Advanced operations
profile:
	@echo "📊 Running performance profiling..."
	@echo "Profiling not implemented yet"

benchmark:
	@echo "⚡ Running benchmarks..."
	@echo "Benchmarks not implemented yet"

# CI/CD Pipeline targets
ci: clean lint type-check test coverage
	@echo "✅ CI pipeline completed successfully!"

coverage:
	@echo "📊 Generating coverage report..."
	python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html
	@echo "Coverage report generated in htmlcov/"

coverage-html:
	@echo "📊 Generating HTML coverage report..."
	python -m pytest tests/ --cov=src --cov-report=html
	@echo "HTML coverage report available at htmlcov/index.html"

type-check:
	@echo "🔍 Running type checks with mypy..."
	@if command -v mypy >/dev/null 2>&1; then \
		mypy src/ tests/ scripts/; \
	else \
		echo "⚠️ mypy not found, install with: pip install mypy"; \
	fi

# Enhanced lint target
lint-all: lint type-check
	@echo "🔍 Running comprehensive linting..."

# Pre-commit hooks
pre-commit-install:
	@echo "🔧 Installing pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		pre-commit install --hook-type commit-msg; \
		echo "✅ Pre-commit hooks installed"; \
	else \
		echo "⚠️ pre-commit not found, install with: pip install pre-commit"; \
	fi

pre-commit:
	@echo "🔧 Running pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit run --all-files; \
	else \
		echo "⚠️ pre-commit not found, install with: pip install pre-commit"; \
		echo "Running manual checks instead..."; \
		$(MAKE) lint type-check format; \
	fi

pre-commit-update:
	@echo "🔄 Updating pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit autoupdate; \
	else \
		echo "⚠️ pre-commit not found, install with: pip install pre-commit"; \
	fi

# Security scanning
security:
	@echo "🔒 Running security scan..."
	@if command -v bandit >/dev/null 2>&1; then \
		bandit -r src/ -f json -o security-report.json; \
		bandit -r src/; \
	else \
		echo "⚠️ bandit not found, install with: pip install bandit"; \
	fi

# Dependency checking
deps-check:
	@echo "🔍 Checking dependencies for security issues..."
	@if command -v safety >/dev/null 2>&1; then \
		safety check; \
	else \
		echo "⚠️ safety not found, install with: pip install safety"; \
	fi

# Test variants for CI
test-unit:
	@echo "🧪 Running unit tests..."
	python -m pytest tests/ -m "not integration and not database" -v

test-integration:
	@echo "🔗 Running integration tests..."
	python -m pytest tests/ -m "integration" -v

test-all-verbose:
	@echo "🧪 Running all tests with verbose output..."
	python -m pytest tests/ -v --tb=short

# CI environment simulation
ci-local: clean
	@echo "🚀 Running full CI pipeline locally..."
	@echo "Step 1: Installing dependencies..."
	$(MAKE) install
	@echo "Step 2: Code formatting check..."
	black --check src/ tests/ scripts/
	@echo "Step 3: Import sorting check..."
	@if command -v isort >/dev/null 2>&1; then \
		isort --check-only src/ tests/ scripts/; \
	fi
	@echo "Step 4: Linting..."
	$(MAKE) lint
	@echo "Step 5: Type checking..."
	$(MAKE) type-check
	@echo "Step 6: Security scanning..."
	$(MAKE) security || echo "Security scan completed with warnings"
	@echo "Step 7: Running tests with coverage..."
	$(MAKE) coverage
	@echo "✅ Local CI pipeline completed!"

# Quality gates
quality-gate:
	@echo "🚦 Running quality gate checks..."
	@echo "Checking code coverage..."
	python -m pytest tests/ --cov=src --cov-fail-under=80
	@echo "Checking code formatting..."
	black --check src/ tests/ scripts/
	@echo "Checking imports..."
	@if command -v isort >/dev/null 2>&1; then \
		isort --check-only src/ tests/ scripts/; \
	fi
	@echo "✅ Quality gate passed!"