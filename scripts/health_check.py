#!/usr/bin/env python3
"""
Bot Provisional - Health Check Script
This script performs comprehensive health checks on all system components.
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.config import settings, setup_logging
from common.database import DatabaseManager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.db_manager = DatabaseManager()
        self.checks = []
        
    async def run_all_checks(self, include_docker: bool = True) -> Dict[str, Any]:
        """Run all health checks and return results."""
        logger.info("Starting comprehensive health check...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "checks": {},
            "summary": {}
        }
        
        # Define all checks
        checks_to_run = [
            ("system", self._check_system_resources),
            ("python", self._check_python_environment),
            ("configuration", self._check_configuration),
            ("databases", self._check_databases),
            ("file_permissions", self._check_file_permissions),
            ("logs", self._check_logging_system),
        ]
        
        if include_docker:
            checks_to_run.insert(3, ("docker", self._check_docker_services))
            
        # Run all checks
        for check_name, check_func in checks_to_run:
            try:
                logger.info(f"Running {check_name} check...")
                check_result = await check_func()
                results["checks"][check_name] = check_result
                logger.info(f"{check_name} check completed: {check_result['status']}")
            except Exception as e:
                logger.error(f"Error in {check_name} check: {e}")
                results["checks"][check_name] = {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                
        # Calculate overall status
        results["overall_status"] = self._calculate_overall_status(results["checks"])
        results["summary"] = self._generate_summary(results["checks"])
        
        logger.info(f"Health check completed. Overall status: {results['overall_status']}")
        return results
        
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources (CPU, memory, disk)."""
        import psutil
        
        # Get system info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check thresholds
        issues = []
        if cpu_percent > 80:
            issues.append(f"High CPU usage: {cpu_percent}%")
        if memory.percent > 85:
            issues.append(f"High memory usage: {memory.percent}%")
        if disk.percent > 90:
            issues.append(f"High disk usage: {disk.percent}%")
            
        return {
            "status": "warning" if issues else "healthy",
            "details": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _check_python_environment(self) -> Dict[str, Any]:
        """Check Python environment and dependencies."""
        issues = []
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 10):
            issues.append(f"Python version {python_version} < required 3.10")
            
        # Check virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        if not in_venv:
            issues.append("Not running in virtual environment")
            
        # Check critical imports
        critical_modules = [
            'asyncio', 'logging', 'pathlib', 'json', 'datetime',
            'asyncpg', 'redis', 'neo4j', 'telethon', 'fastapi'
        ]
        
        missing_modules = []
        for module in critical_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
                
        if missing_modules:
            issues.append(f"Missing modules: {', '.join(missing_modules)}")
            
        # Check requirements.txt exists
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            issues.append("requirements.txt not found")
            
        return {
            "status": "unhealthy" if missing_modules else ("warning" if issues else "healthy"),
            "details": {
                "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                "virtual_env": in_venv,
                "missing_modules": missing_modules,
                "requirements_exists": requirements_file.exists()
            },
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _check_configuration(self) -> Dict[str, Any]:
        """Check configuration files and environment variables."""
        issues = []
        
        # Check required files
        required_files = [
            ".env.example",
            "config/logging.yaml",
            "docker-compose.yml",
            "requirements.txt"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
                
        if missing_files:
            issues.append(f"Missing files: {', '.join(missing_files)}")
            
        # Check .env file
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if not env_file.exists() and env_example.exists():
            issues.append(".env file not found (copy from .env.example)")
            
        # Check critical environment variables
        critical_env_vars = [
            "POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD",
            "REDIS_HOST", "NEO4J_HOST", "NEO4J_USER", "NEO4J_PASSWORD"
        ]
        
        missing_env_vars = []
        for var in critical_env_vars:
            if not hasattr(settings, var.lower()) or not getattr(settings, var.lower()):
                missing_env_vars.append(var)
                
        if missing_env_vars:
            issues.append(f"Missing/empty env vars: {', '.join(missing_env_vars)}")
            
        return {
            "status": "unhealthy" if missing_files or missing_env_vars else ("warning" if issues else "healthy"),
            "details": {
                "missing_files": missing_files,
                "env_file_exists": env_file.exists(),
                "missing_env_vars": missing_env_vars
            },
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _check_docker_services(self) -> Dict[str, Any]:
        """Check Docker and docker-compose services."""
        issues = []
        
        try:
            # Check if Docker is available
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                issues.append("Docker not available")
                return {
                    "status": "unhealthy",
                    "details": {"docker_available": False},
                    "issues": issues,
                    "timestamp": datetime.now().isoformat()
                }
                
            # Check docker-compose
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                issues.append("docker-compose not available")
                
            # Check running services
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            services_info = {}
            if result.returncode == 0 and result.stdout.strip():
                try:
                    services = [json.loads(line) for line in result.stdout.strip().split('\n') if line]
                    for service in services:
                        name = service.get("Service", "unknown")
                        state = service.get("State", "unknown")
                        services_info[name] = {
                            "state": state,
                            "status": service.get("Status", "unknown")
                        }
                        
                        if state != "running":
                            issues.append(f"Service {name} not running: {state}")
                except json.JSONDecodeError:
                    issues.append("Could not parse docker-compose ps output")
            else:
                issues.append("No services found or docker-compose ps failed")
                
        except subprocess.TimeoutExpired:
            issues.append("Docker commands timed out")
        except FileNotFoundError:
            issues.append("Docker or docker-compose not installed")
        except Exception as e:
            issues.append(f"Docker check error: {str(e)}")
            
        # Determine status
        if "Docker not available" in issues or "docker-compose not available" in issues:
            status = "unhealthy"
        elif any("not running" in issue for issue in issues):
            status = "warning"
        else:
            status = "healthy"
            
        return {
            "status": status,
            "details": {
                "docker_available": "Docker not available" not in issues,
                "compose_available": "docker-compose not available" not in issues,
                "services": services_info
            },
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _check_databases(self) -> Dict[str, Any]:
        """Check database connectivity and basic functionality."""
        issues = []
        db_status = {}
        
        # PostgreSQL check
        try:
            postgres_conn = await self.db_manager.get_postgres_connection()
            version = await postgres_conn.fetchval("SELECT version()")
            db_status["postgresql"] = {
                "connected": True,
                "version": version.split()[1] if version else "unknown"
            }
        except Exception as e:
            issues.append(f"PostgreSQL connection failed: {str(e)}")
            db_status["postgresql"] = {"connected": False, "error": str(e)}
            
        # Redis check
        try:
            redis_conn = await self.db_manager.get_redis_connection()
            info = await redis_conn.info()
            db_status["redis"] = {
                "connected": True,
                "version": info.get("redis_version", "unknown"),
                "memory_used": info.get("used_memory_human", "unknown")
            }
        except Exception as e:
            issues.append(f"Redis connection failed: {str(e)}")
            db_status["redis"] = {"connected": False, "error": str(e)}
            
        # Neo4j check
        try:
            neo4j_session = await self.db_manager.get_neo4j_session()
            result = await neo4j_session.run("CALL dbms.components() YIELD name, versions, edition")
            record = await result.single()
            if record:
                db_status["neo4j"] = {
                    "connected": True,
                    "version": record["versions"][0] if record["versions"] else "unknown",
                    "edition": record["edition"]
                }
            else:
                db_status["neo4j"] = {"connected": True, "version": "unknown"}
        except Exception as e:
            issues.append(f"Neo4j connection failed: {str(e)}")
            db_status["neo4j"] = {"connected": False, "error": str(e)}
            
        # Determine overall database status
        connected_dbs = sum(1 for db in db_status.values() if db.get("connected", False))
        if connected_dbs == 0:
            status = "unhealthy"
        elif connected_dbs < len(db_status):
            status = "warning"
        else:
            status = "healthy"
            
        return {
            "status": status,
            "details": db_status,
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _check_file_permissions(self) -> Dict[str, Any]:
        """Check file permissions and directory structure."""
        issues = []
        
        # Check script permissions
        script_files = [
            "scripts/setup_dev.sh",
            "scripts/check_connections.py",
            "scripts/init_databases.py",
            "scripts/populate_test_data.py",
            "scripts/reset_environment.py",
            "scripts/health_check.py"
        ]
        
        non_executable = []
        for script in script_files:
            script_path = self.project_root / script
            if script_path.exists():
                if not script_path.stat().st_mode & 0o111:  # Check execute permission
                    non_executable.append(script)
            else:
                issues.append(f"Script not found: {script}")
                
        if non_executable:
            issues.append(f"Scripts not executable: {', '.join(non_executable)}")
            
        # Check directory structure
        required_dirs = [
            "src", "tests", "scripts", "config", "docs"
        ]
        
        missing_dirs = []
        for dir_name in required_dirs:
            if not (self.project_root / dir_name).exists():
                missing_dirs.append(dir_name)
                
        if missing_dirs:
            issues.append(f"Missing directories: {', '.join(missing_dirs)}")
            
        # Check log directory permissions
        logs_dir = self.project_root / "logs"
        if logs_dir.exists():
            if not logs_dir.stat().st_mode & 0o200:  # Check write permission
                issues.append("Logs directory not writable")
        else:
            issues.append("Logs directory does not exist")
            
        return {
            "status": "warning" if issues else "healthy",
            "details": {
                "non_executable_scripts": non_executable,
                "missing_directories": missing_dirs,
                "logs_writable": logs_dir.exists() and logs_dir.stat().st_mode & 0o200
            },
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _check_logging_system(self) -> Dict[str, Any]:
        """Check logging configuration and functionality."""
        issues = []
        
        # Check logging config file
        logging_config = self.project_root / "config" / "logging.yaml"
        if not logging_config.exists():
            issues.append("Logging configuration file not found")
            
        # Check logs directory
        logs_dir = self.project_root / "logs"
        if not logs_dir.exists():
            issues.append("Logs directory does not exist")
            
        # Test logging functionality
        log_test_passed = False
        try:
            test_logger = logging.getLogger("health_check.test")
            test_logger.info("Health check logging test")
            log_test_passed = True
        except Exception as e:
            issues.append(f"Logging test failed: {str(e)}")
            
        # Check log files
        log_files = list(logs_dir.glob("*.log")) if logs_dir.exists() else []
        recent_logs = []
        
        for log_file in log_files:
            try:
                stat = log_file.stat()
                age_hours = (time.time() - stat.st_mtime) / 3600
                if age_hours < 24:  # Recent logs (less than 24 hours old)
                    recent_logs.append(log_file.name)
            except Exception:
                pass
                
        return {
            "status": "warning" if issues else "healthy",
            "details": {
                "config_exists": logging_config.exists(),
                "logs_dir_exists": logs_dir.exists(),
                "test_passed": log_test_passed,
                "log_files": [f.name for f in log_files],
                "recent_logs": recent_logs
            },
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
    def _calculate_overall_status(self, checks: Dict[str, Any]) -> str:
        """Calculate overall system status from individual checks."""
        statuses = [check.get("status", "unknown") for check in checks.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "warning" in statuses:
            return "warning"
        elif all(status == "healthy" for status in statuses):
            return "healthy"
        else:
            return "unknown"
            
    def _generate_summary(self, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from check results."""
        total = len(checks)
        healthy = sum(1 for check in checks.values() if check.get("status") == "healthy")
        warning = sum(1 for check in checks.values() if check.get("status") == "warning")
        unhealthy = sum(1 for check in checks.values() if check.get("status") == "unhealthy")
        
        all_issues = []
        for check in checks.values():
            all_issues.extend(check.get("issues", []))
            
        return {
            "total_checks": total,
            "healthy": healthy,
            "warning": warning,
            "unhealthy": unhealthy,
            "total_issues": len(all_issues),
            "critical_issues": len([issue for issue in all_issues if any(word in issue.lower() for word in ["failed", "not available", "missing"])])
        }
        
    async def cleanup(self):
        """Clean up resources."""
        await self.db_manager.close_all()


async def main():
    """Main function to run health checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run system health checks")
    parser.add_argument("--no-docker", action="store_true", help="Skip Docker checks")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    parser.add_argument("--check", help="Run only specific check (system, python, configuration, docker, databases, file_permissions, logs)")
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
        
    checker = HealthChecker()
    
    try:
        if args.check:
            # Run single check
            check_methods = {
                "system": checker._check_system_resources,
                "python": checker._check_python_environment,
                "configuration": checker._check_configuration,
                "docker": checker._check_docker_services,
                "databases": checker._check_databases,
                "file_permissions": checker._check_file_permissions,
                "logs": checker._check_logging_system
            }
            
            if args.check not in check_methods:
                print(f"Unknown check: {args.check}")
                print(f"Available: {', '.join(check_methods.keys())}")
                sys.exit(1)
                
            result = await check_methods[args.check]()
            
            if args.output == "json":
                print(json.dumps(result, indent=2))
            else:
                print(f"\n=== {args.check.upper()} CHECK ===")
                print(f"Status: {result['status']}")
                if result.get('issues'):
                    print("Issues:")
                    for issue in result['issues']:
                        print(f"  - {issue}")
                        
        else:
            # Run all checks
            results = await checker.run_all_checks(include_docker=not args.no_docker)
            
            if args.output == "json":
                print(json.dumps(results, indent=2))
            else:
                # Text output
                print(f"\n=== SYSTEM HEALTH CHECK ===")
                print(f"Timestamp: {results['timestamp']}")
                print(f"Overall Status: {results['overall_status'].upper()}")
                
                # Summary
                summary = results['summary']
                print(f"\nSummary:")
                print(f"  Total checks: {summary['total_checks']}")
                print(f"  Healthy: {summary['healthy']}")
                print(f"  Warning: {summary['warning']}")
                print(f"  Unhealthy: {summary['unhealthy']}")
                print(f"  Total issues: {summary['total_issues']}")
                
                # Individual check results
                print(f"\nDetailed Results:")
                for check_name, result in results['checks'].items():
                    status_icon = {"healthy": "✅", "warning": "⚠️", "unhealthy": "❌", "error": "💥"}.get(result['status'], "❓")
                    print(f"  {status_icon} {check_name}: {result['status']}")
                    
                    if result.get('issues'):
                        for issue in result['issues']:
                            print(f"    - {issue}")
                            
                # Exit with error code if unhealthy
                if results['overall_status'] == 'unhealthy':
                    sys.exit(1)
                elif results['overall_status'] == 'warning':
                    sys.exit(2)
                    
    except KeyboardInterrupt:
        print("\n⚠️ Health check cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}")
        print(f"\n❌ Health check failed: {e}")
        sys.exit(1)
    finally:
        await checker.cleanup()


if __name__ == "__main__":
    asyncio.run(main())