#!/usr/bin/env python3
"""
Validation script for Docker configuration.
Checks that all necessary files exist and are properly configured.
"""

import sys
from pathlib import Path
import yaml


def validate_docker_files():
    """Validate Docker configuration files."""
    project_root = Path(__file__).parent.parent
    
    # Check required files exist
    required_files = [
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.dev.yml", 
        "docker-compose.prod.yml",
        ".dockerignore",
        "docker/postgres/init.sql"
    ]
    
    print("🐳 Validating Docker configuration files...")
    
    missing_files = []
    for file in required_files:
        file_path = project_root / file
        if file_path.exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - Missing!")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    
    # Validate YAML syntax
    print("\n📄 Validating YAML syntax...")
    yaml_files = [
        "docker-compose.yml",
        "docker-compose.dev.yml",
        "docker-compose.prod.yml"
    ]
    
    for yaml_file in yaml_files:
        try:
            with open(project_root / yaml_file, 'r') as f:
                yaml.safe_load(f)
            print(f"✅ {yaml_file} - Valid YAML")
        except Exception as e:
            print(f"❌ {yaml_file} - Invalid YAML: {e}")
            return False
    
    # Check service definitions
    print("\n🔧 Validating service configuration...")
    
    with open(project_root / "docker-compose.yml", 'r') as f:
        compose_config = yaml.safe_load(f)
    
    required_services = ["postgres", "redis", "neo4j", "app"]
    services = compose_config.get("services", {})
    
    for service in required_services:
        if service in services:
            print(f"✅ Service '{service}' defined")
        else:
            print(f"❌ Service '{service}' missing!")
            return False
    
    # Check networks and volumes
    if "networks" in compose_config:
        print("✅ Networks configured")
    else:
        print("❌ No networks defined")
        return False
    
    if "volumes" in compose_config:
        print("✅ Volumes configured")
    else:
        print("❌ No volumes defined")
        return False
    
    print("\n🎉 All Docker configuration files are valid!")
    return True


def validate_module_structure():
    """Validate that required Python modules exist."""
    project_root = Path(__file__).parent.parent
    
    print("\n🐍 Validating Python module structure...")
    
    required_modules = [
        "src/dashboard/main.py",
        "src/userbot/main.py", 
        "src/common/celery_app.py",
        "src/common/tasks.py",
        "src/common/config.py"
    ]
    
    for module in required_modules:
        module_path = project_root / module
        if module_path.exists():
            print(f"✅ {module}")
        else:
            print(f"❌ {module} - Missing!")
            return False
    
    print("✅ All required Python modules exist!")
    return True


def main():
    """Main validation function."""
    print("🔍 Bot Provisional - Docker Configuration Validator\n")
    
    docker_valid = validate_docker_files()
    modules_valid = validate_module_structure()
    
    if docker_valid and modules_valid:
        print("\n🎉 All validations passed! Docker configuration is ready.")
        print("\n📝 Next steps:")
        print("1. Install Docker and Docker Compose")
        print("2. Copy .env.example to .env and configure your settings")
        print("3. Run: docker-compose up -d")
        return 0
    else:
        print("\n❌ Validation failed! Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())