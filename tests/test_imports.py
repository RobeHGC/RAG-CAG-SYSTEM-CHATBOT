"""
Basic import tests to verify all modules can be imported correctly.
This ensures the project structure is set up properly.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_common_imports():
    """Test that common module imports work."""
    try:
        from src.common import config
        from src.common.config import Settings, settings, setup_logging
        
        assert hasattr(config, 'Settings')
        assert hasattr(config, 'settings')
        assert hasattr(config, 'setup_logging')
        assert isinstance(settings, Settings)
    except ImportError as e:
        pytest.fail(f"Failed to import common modules: {e}")


def test_userbot_imports():
    """Test that userbot module can be imported."""
    try:
        import src.userbot
        assert src.userbot is not None
    except ImportError as e:
        pytest.fail(f"Failed to import userbot module: {e}")


def test_orquestador_imports():
    """Test that orquestador module can be imported."""
    try:
        import src.orquestador
        assert src.orquestador is not None
    except ImportError as e:
        pytest.fail(f"Failed to import orquestador module: {e}")


def test_memoria_imports():
    """Test that memoria module can be imported."""
    try:
        import src.memoria
        assert src.memoria is not None
    except ImportError as e:
        pytest.fail(f"Failed to import memoria module: {e}")


def test_verificador_imports():
    """Test that verificador module can be imported."""
    try:
        import src.verificador
        assert src.verificador is not None
    except ImportError as e:
        pytest.fail(f"Failed to import verificador module: {e}")


def test_dashboard_imports():
    """Test that dashboard module can be imported."""
    try:
        import src.dashboard
        assert src.dashboard is not None
    except ImportError as e:
        pytest.fail(f"Failed to import dashboard module: {e}")


def test_project_structure():
    """Test that the project structure is correct."""
    project_root = Path(__file__).parent.parent
    
    # Check main directories exist
    assert (project_root / "src").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "docs").exists()
    assert (project_root / "scripts").exists()
    assert (project_root / "config").exists()
    assert (project_root / "bitacora").exists()
    
    # Check source subdirectories
    src_dirs = ["userbot", "orquestador", "memoria", "verificador", "dashboard", "common"]
    for dir_name in src_dirs:
        dir_path = project_root / "src" / dir_name
        assert dir_path.exists(), f"Directory {dir_path} does not exist"
        assert (dir_path / "__init__.py").exists(), f"__init__.py missing in {dir_path}"
    
    # Check important files exist
    assert (project_root / "requirements.txt").exists()
    assert (project_root / ".env.example").exists()
    assert (project_root / "README.md").exists()
    assert (project_root / ".gitignore").exists()
    
    # Check config files
    assert (project_root / "config" / "logging.yaml").exists()
    assert (project_root / "src" / "common" / "config.py").exists()
    
    # Check documentation
    assert (project_root / "docs" / "ARCHITECTURE.md").exists()
    assert (project_root / "bitacora" / "VISION_GENERAL.md").exists()
    
    # Check scripts
    assert (project_root / "scripts" / "setup_dev.sh").exists()
    assert (project_root / "scripts" / "setup_dev.sh").stat().st_mode & 0o111, "setup_dev.sh is not executable"


def test_config_loading():
    """Test that configuration can be loaded without errors."""
    try:
        from src.common.config import settings
        
        # Check some basic attributes exist
        assert hasattr(settings, 'project_name')
        assert hasattr(settings, 'version')
        assert hasattr(settings, 'debug')
        
        # Check computed properties
        assert hasattr(settings, 'postgres_url')
        assert hasattr(settings, 'redis_url')
        
        # Check paths are Path objects
        from pathlib import Path
        assert isinstance(settings.base_dir, Path)
        assert isinstance(settings.logs_dir, Path)
        assert isinstance(settings.data_dir, Path)
        
    except Exception as e:
        pytest.fail(f"Failed to load configuration: {e}")


def test_logging_setup():
    """Test that logging can be configured without errors."""
    import tempfile
    import shutil
    from pathlib import Path
    
    # Create a temporary directory for logs
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the logging config to temp directory
        temp_config_dir = Path(temp_dir) / "config"
        temp_config_dir.mkdir()
        
        original_config = Path(__file__).parent.parent / "config" / "logging.yaml"
        if original_config.exists():
            shutil.copy(original_config, temp_config_dir / "logging.yaml")
        
        # Test setup_logging function
        try:
            from src.common.config import setup_logging
            # This should not raise any exceptions
            setup_logging(temp_config_dir / "logging.yaml")
        except Exception as e:
            pytest.fail(f"Failed to setup logging: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])