# CI/CD Setup Documentation

## Overview

This document describes the complete Continuous Integration and Continuous Deployment (CI/CD) setup for the Bot Provisional project. Our CI/CD pipeline ensures code quality, runs comprehensive tests, and maintains security standards.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [GitHub Actions Workflows](#github-actions-workflows)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Code Quality Tools](#code-quality-tools)
- [Dependency Management](#dependency-management)
- [Local Development Workflow](#local-development-workflow)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

Our CI/CD pipeline consists of several components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Local Dev      │    │  GitHub Actions │    │  GitHub Pages   │
│                 │    │                 │    │                 │
│ • Pre-commit    │───▶│ • CI Pipeline   │───▶│ • Coverage      │
│ • Local Tests   │    │ • Coverage      │    │   Reports       │
│ • Linting       │    │ • Security      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │
        │                       ▼
        │              ┌─────────────────┐
        │              │  Dependabot     │
        │              │                 │
        └─────────────▶│ • Auto Updates  │
                       │ • Security      │
                       │   Patches       │
                       └─────────────────┘
```

## GitHub Actions Workflows

### 1. Main CI Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Push to main/master/develop branches
- Pull requests to main/master/develop
- Manual workflow dispatch

**Jobs:**

#### Lint Job
- **Duration:** ~5-10 minutes
- **Purpose:** Fast feedback on code quality
- **Checks:**
  - Code formatting (Black)
  - Import sorting (isort)
  - Linting (flake8)
  - Type checking (mypy)
  - Security scanning (bandit)
  - Dependency vulnerabilities (safety)

#### Test Matrix Job
- **Duration:** ~15-30 minutes
- **Purpose:** Comprehensive testing across Python versions
- **Matrix:** Python 3.10, 3.11, 3.12
- **Services:** PostgreSQL, Redis, Neo4j
- **Features:**
  - Unit and integration tests
  - Coverage reporting
  - Test result artifacts
  - Codecov integration

#### Integration Test Job
- **Duration:** ~30-45 minutes
- **Purpose:** Full Docker environment testing
- **Runs:** Only on non-draft PRs and pushes
- **Features:**
  - Full Docker Compose stack
  - Database initialization
  - End-to-end testing

#### Build Validation Job
- **Duration:** ~10-15 minutes
- **Purpose:** Ensure package can be built and installed
- **Features:**
  - Python package building
  - Installation verification

#### Security Analysis Job
- **Duration:** ~10-15 minutes
- **Purpose:** Security and vulnerability analysis
- **Tools:**
  - Bandit (Python security linter)
  - Safety (dependency vulnerability scanner)
  - Semgrep (static analysis)

### 2. Coverage Workflow (`.github/workflows/coverage.yml`)

**Purpose:** Dedicated coverage reporting and GitHub Pages deployment

**Features:**
- Detailed coverage reports
- Coverage badges
- PR comments with coverage info
- GitHub Pages deployment for coverage HTML reports

**Coverage Thresholds:**
- **Target:** 80% minimum
- **Excellent:** 90%+
- **Warning:** Below 80%

### 3. Dependabot Integration

**Purpose:** Automated dependency updates

**Configuration:**
- **Python packages:** Weekly updates (Mondays)
- **GitHub Actions:** Weekly updates (Mondays)
- **Docker images:** Weekly updates (Tuesdays)
- **Pre-commit hooks:** Weekly updates (Wednesdays)

**Grouping Strategy:**
- Production dependencies grouped together
- Development dependencies grouped together
- GitHub Actions grouped together

## Pre-commit Hooks

Pre-commit hooks run locally before each commit to catch issues early.

### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
make pre-commit-install
# or
pre-commit install
```

### Configured Hooks

1. **Built-in Hooks:**
   - Trailing whitespace removal
   - End-of-file fixer
   - YAML/JSON/TOML validation
   - Large file detection
   - Merge conflict detection
   - Private key detection

2. **Python Code Quality:**
   - **Black:** Code formatting
   - **isort:** Import sorting
   - **flake8:** Linting with plugins
   - **Ruff:** Modern Python linter
   - **mypy:** Type checking
   - **bandit:** Security linting

3. **Documentation:**
   - **pydocstyle:** Docstring conventions
   - **prettier:** Markdown/YAML formatting

4. **Shell Scripts:**
   - **shellcheck:** Shell script linting

5. **Dependencies:**
   - **safety:** Vulnerability scanning

### Running Pre-commit Hooks

```bash
# Run on all files
make pre-commit
# or
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Update hook versions
make pre-commit-update
# or
pre-commit autoupdate
```

## Code Quality Tools

### Configuration Files

- **`pyproject.toml`:** Central configuration for most Python tools
- **`.flake8`:** Flake8-specific configuration
- **`.coveragerc`:** Coverage configuration
- **`.pre-commit-config.yaml`:** Pre-commit hooks configuration

### Tool Integration

#### Black (Code Formatting)
```bash
# Format code
make format
# Check formatting
black --check src/ tests/ scripts/
```

#### isort (Import Sorting)
```bash
# Sort imports
isort src/ tests/ scripts/
# Check import sorting
isort --check-only src/ tests/ scripts/
```

#### flake8 (Linting)
```bash
# Lint code
make lint
# Advanced linting
flake8 src/ tests/ scripts/
```

#### mypy (Type Checking)
```bash
# Type check
make type-check
# Advanced type checking
mypy src/ tests/ scripts/
```

#### pytest (Testing)
```bash
# Run all tests
make test
# Run with coverage
make coverage
# Run specific test types
make test-unit
make test-integration
```

### Quality Gates

The CI pipeline enforces several quality gates:

1. **Code Formatting:** Must pass Black formatting check
2. **Import Sorting:** Must pass isort check
3. **Linting:** Must pass flake8 with no errors
4. **Type Checking:** Must pass mypy (warnings allowed)
5. **Security:** Must pass bandit security scan
6. **Coverage:** Must maintain 80% minimum coverage
7. **Tests:** All tests must pass across Python versions

## Dependency Management

### Automatic Updates

Dependabot manages dependency updates with the following schedule:

- **Monday:** Python packages and GitHub Actions
- **Tuesday:** Docker images
- **Wednesday:** Pre-commit hooks

### Manual Updates

```bash
# Update dependencies
pip install -U -r requirements.txt

# Update pre-commit hooks
pre-commit autoupdate

# Check for security vulnerabilities
safety check
```

### Security Monitoring

- **Safety:** Checks for known vulnerabilities in Python packages
- **Bandit:** Scans code for security issues
- **Dependabot:** Provides security advisories and automatic patches

## Local Development Workflow

### Setup

```bash
# Set up development environment
make setup

# Install pre-commit hooks
make pre-commit-install
```

### Daily Development

```bash
# Start development environment
make dev

# Run local CI pipeline
make ci-local

# Quick quality check
make quality-gate
```

### Before Committing

```bash
# Format code
make format

# Run linting
make lint

# Run type checking
make type-check

# Run tests
make test

# Or run everything
make ci
```

### Pull Request Workflow

1. **Create branch:** `git checkout -b feature/your-feature`
2. **Develop:** Write code with tests
3. **Local CI:** Run `make ci-local`
4. **Commit:** Pre-commit hooks run automatically
5. **Push:** `git push origin feature/your-feature`
6. **Create PR:** GitHub Actions run automatically
7. **Review:** Check CI status and coverage
8. **Merge:** After approval and CI pass

## Configuration Examples

### Environment Variables for CI

```bash
# Required for coverage uploads
CODECOV_TOKEN=your_codecov_token

# Optional for enhanced security scanning
SEMGREP_TOKEN=your_semgrep_token
```

### Local Testing with Docker

```bash
# Start services
make docker

# Run integration tests
make test-integration

# Check service health
make health
```

## Troubleshooting

### Common Issues

#### Pre-commit Hook Failures

```bash
# Skip hooks temporarily (not recommended)
git commit --no-verify

# Fix formatting issues
make format
git add .
git commit

# Update hooks if outdated
pre-commit autoupdate
```

#### CI Test Failures

```bash
# Run tests locally with same conditions
make ci-local

# Check specific test failure
python -m pytest tests/test_specific.py -v

# Debug with Docker services
make docker
python scripts/check_connections.py
```

#### Coverage Issues

```bash
# Generate local coverage report
make coverage-html
open htmlcov/index.html

# Check coverage by file
python -m pytest --cov=src --cov-report=term-missing
```

#### Type Checking Errors

```bash
# Run mypy with verbose output
mypy src/ --show-error-codes --show-error-context

# Check specific file
mypy src/specific_file.py
```

### Performance Optimization

#### Faster CI Runs

1. **Cache dependencies:** Already configured in workflows
2. **Run linting first:** Fails fast on simple issues
3. **Parallel jobs:** Matrix testing across Python versions
4. **Skip integration tests:** On draft PRs

#### Local Development Speed

```bash
# Quick tests only
make test-quick

# Skip slow tests
python -m pytest -m "not slow"

# Run tests in parallel
python -m pytest -n auto
```

### Monitoring and Metrics

#### CI Performance

- **Lint job:** Target < 10 minutes
- **Test matrix:** Target < 30 minutes
- **Integration tests:** Target < 45 minutes
- **Total pipeline:** Target < 60 minutes

#### Code Quality Metrics

- **Coverage:** Maintain > 80%
- **Type coverage:** Target > 70%
- **Security issues:** Zero high-severity
- **Dependency freshness:** < 30 days behind

## Best Practices

### Commit Messages

Follow conventional commit format:
```
type(scope): description

feat(userbot): add message debouncing
fix(database): resolve connection timeout
docs(ci): update pipeline documentation
```

### Pull Request Guidelines

1. **Small, focused changes:** Easier to review and test
2. **Descriptive titles:** Clear purpose and scope
3. **Test coverage:** Include tests for new functionality
4. **Documentation:** Update docs for significant changes
5. **CI status:** Ensure all checks pass before requesting review

### Code Quality

1. **Write tests first:** TDD approach when possible
2. **Type hints:** Add type annotations for better tooling
3. **Docstrings:** Document public APIs with Google style
4. **Error handling:** Use appropriate exception types
5. **Logging:** Use structured logging with appropriate levels

### Security

1. **Secrets management:** Never commit credentials
2. **Dependency updates:** Keep dependencies current
3. **Code scanning:** Address bandit findings
4. **Input validation:** Sanitize all user inputs
5. **Database security:** Use parameterized queries

This CI/CD setup provides a robust foundation for maintaining code quality, ensuring reliability, and enabling confident deployments of the Bot Provisional project.