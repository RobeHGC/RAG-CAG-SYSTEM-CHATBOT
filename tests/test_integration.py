"""
Integration tests for Bot Provisional components.
These tests verify that different components work together correctly.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import settings


@pytest.mark.integration
def test_environment_setup():
    """Test that the environment is properly configured for testing."""
    # This test ensures the basic environment is working
    assert settings is not None
    assert settings.project_name == "Bot Provisional"
    assert settings.version == "0.1.0"


@pytest.mark.integration
@pytest.mark.database
def test_database_configuration():
    """Test that database configurations are properly set."""
    # Test PostgreSQL URL format
    postgres_url = settings.postgres_url
    assert "postgresql" in postgres_url
    assert settings.postgres_db in postgres_url
    
    # Test Redis URL format
    redis_url = settings.redis_url
    assert "redis" in redis_url
    assert str(settings.redis_port) in redis_url
    
    # Test Neo4j configuration
    assert settings.neo4j_uri is not None
    assert "bolt://" in settings.neo4j_uri or "neo4j://" in settings.neo4j_uri
    assert settings.neo4j_user is not None


@pytest.mark.integration
def test_logging_configuration():
    """Test that logging is properly configured."""
    import logging
    from src.common.config import setup_logging
    
    # Test that setup_logging doesn't raise exceptions
    try:
        setup_logging()
        logger = logging.getLogger("test_integration")
        logger.info("Test log message")
        assert True  # If we get here, logging is working
    except Exception as e:
        pytest.fail(f"Logging configuration failed: {e}")


@pytest.mark.integration
def test_project_structure_integrity():
    """Test that the project structure is intact and accessible."""
    project_root = Path(__file__).parent.parent
    
    # Test critical directories exist
    critical_dirs = [
        "src", "tests", "docs", "scripts", "config"
    ]
    
    for dir_name in critical_dirs:
        dir_path = project_root / dir_name
        assert dir_path.exists(), f"Critical directory {dir_name} is missing"
        assert dir_path.is_dir(), f"{dir_name} exists but is not a directory"
    
    # Test critical files exist
    critical_files = [
        "requirements.txt",
        "pyproject.toml",
        ".flake8",
        ".coveragerc",
        "README.md"
    ]
    
    for file_name in critical_files:
        file_path = project_root / file_name
        assert file_path.exists(), f"Critical file {file_name} is missing"
        assert file_path.is_file(), f"{file_name} exists but is not a file"


@pytest.mark.integration
def test_module_imports_work_together():
    """Test that all main modules can be imported together without conflicts."""
    try:
        # Import all main modules
        from src.common import config
        from src.common.config import settings
        
        # Import other modules (these should work even if they're placeholder)
        import src.userbot
        import src.orquestador
        import src.memoria
        import src.verificador
        import src.dashboard
        
        # Test that settings is accessible from different contexts
        assert config.settings is settings
        assert settings.project_name is not None
        
    except ImportError as e:
        pytest.fail(f"Module import integration failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])