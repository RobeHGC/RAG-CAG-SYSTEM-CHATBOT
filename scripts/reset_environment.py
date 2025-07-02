#!/usr/bin/env python3
"""
Bot Provisional - Environment Reset/Cleanup Script
This script resets the development environment to a clean state.
"""

import asyncio
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.config import settings, setup_logging
from common.database import DatabaseManager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class EnvironmentResetter:
    """Handles resetting and cleaning the development environment."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.db_manager = None
        
    async def reset_all(self, 
                       databases: bool = True,
                       logs: bool = True, 
                       cache: bool = True,
                       docker: bool = True,
                       keep_venv: bool = True) -> bool:
        """Reset the entire development environment."""
        try:
            logger.info("Starting environment reset...")
            
            if docker:
                await self._reset_docker_services()
                
            if databases and docker:
                # Wait for services to be ready after restart
                await asyncio.sleep(5)
                self.db_manager = DatabaseManager()
                await self._reset_databases()
                
            if logs:
                await self._reset_logs()
                
            if cache:
                await self._reset_cache()
                
            if not keep_venv:
                await self._reset_virtual_environment()
                
            logger.info("Environment reset completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error during environment reset: {e}")
            return False
        finally:
            if self.db_manager:
                await self.db_manager.close_all()
                
    async def _reset_docker_services(self):
        """Reset Docker services (stop, remove, and restart)."""
        logger.info("Resetting Docker services...")
        
        try:
            # Stop all services
            result = subprocess.run(
                ["docker-compose", "down", "-v"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning(f"Docker compose down failed: {result.stderr}")
            else:
                logger.info("Docker services stopped successfully")
                
            # Remove volumes to ensure clean state
            result = subprocess.run(
                ["docker", "volume", "prune", "-f"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning(f"Docker volume prune failed: {result.stderr}")
            else:
                logger.info("Docker volumes cleaned")
                
            # Start services again
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to restart Docker services: {result.stderr}")
                raise Exception("Docker services restart failed")
            else:
                logger.info("Docker services restarted successfully")
                
        except FileNotFoundError:
            logger.warning("Docker or docker-compose not found, skipping Docker reset")
        except Exception as e:
            logger.error(f"Error resetting Docker services: {e}")
            raise
            
    async def _reset_databases(self):
        """Reset all databases to clean state."""
        logger.info("Resetting databases...")
        
        try:
            # Reset PostgreSQL
            await self._reset_postgres()
            
            # Reset Redis
            await self._reset_redis()
            
            # Reset Neo4j
            await self._reset_neo4j()
            
            logger.info("All databases reset successfully")
            
        except Exception as e:
            logger.error(f"Error resetting databases: {e}")
            raise
            
    async def _reset_postgres(self):
        """Reset PostgreSQL database."""
        logger.info("Resetting PostgreSQL...")
        
        try:
            postgres_conn = await self.db_manager.get_postgres_connection()
            
            # Get list of all tables
            tables_result = await postgres_conn.fetch("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            
            if tables_result:
                # Disable foreign key checks and truncate all tables
                async with postgres_conn.transaction():
                    for table in tables_result:
                        table_name = table['tablename']
                        await postgres_conn.execute(f'TRUNCATE TABLE "{table_name}" CASCADE')
                        
                logger.info(f"Truncated {len(tables_result)} PostgreSQL tables")
            else:
                logger.info("No PostgreSQL tables found to reset")
                
        except Exception as e:
            logger.warning(f"PostgreSQL reset failed (may be expected if DB not initialized): {e}")
            
    async def _reset_redis(self):
        """Reset Redis database."""
        logger.info("Resetting Redis...")
        
        try:
            redis_conn = await self.db_manager.get_redis_connection()
            
            # Flush all Redis databases
            await redis_conn.flushall()
            
            logger.info("Redis databases flushed successfully")
            
        except Exception as e:
            logger.warning(f"Redis reset failed: {e}")
            
    async def _reset_neo4j(self):
        """Reset Neo4j database."""
        logger.info("Resetting Neo4j...")
        
        try:
            neo4j_session = await self.db_manager.get_neo4j_session()
            
            # Delete all nodes and relationships
            await neo4j_session.run("MATCH (n) DETACH DELETE n")
            
            logger.info("Neo4j database cleared successfully")
            
        except Exception as e:
            logger.warning(f"Neo4j reset failed: {e}")
            
    async def _reset_logs(self):
        """Reset log files."""
        logger.info("Resetting log files...")
        
        logs_dir = self.project_root / "logs"
        
        if logs_dir.exists():
            # Remove all log files
            for log_file in logs_dir.glob("*.log*"):
                try:
                    log_file.unlink()
                    logger.debug(f"Removed log file: {log_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove log file {log_file}: {e}")
                    
            # Remove JSON log files
            for log_file in logs_dir.glob("*.json"):
                try:
                    log_file.unlink()
                    logger.debug(f"Removed JSON log file: {log_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove JSON log file {log_file}: {e}")
                    
            logger.info("Log files reset successfully")
        else:
            logger.info("No logs directory found")
            
    async def _reset_cache(self):
        """Reset cache directories and temporary files."""
        logger.info("Resetting cache and temporary files...")
        
        # Python cache directories
        cache_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo",
            "**/.pytest_cache"
        ]
        
        for pattern in cache_patterns:
            for path in self.project_root.glob(pattern):
                try:
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        shutil.rmtree(path)
                    logger.debug(f"Removed cache: {path}")
                except Exception as e:
                    logger.warning(f"Failed to remove cache {path}: {e}")
                    
        # Remove data directory if it exists
        data_dir = self.project_root / "data"
        if data_dir.exists():
            try:
                shutil.rmtree(data_dir)
                logger.info("Data directory removed")
            except Exception as e:
                logger.warning(f"Failed to remove data directory: {e}")
                
        logger.info("Cache and temporary files reset successfully")
        
    async def _reset_virtual_environment(self):
        """Reset Python virtual environment."""
        logger.info("Resetting virtual environment...")
        
        venv_dir = self.project_root / "venv"
        
        if venv_dir.exists():
            try:
                shutil.rmtree(venv_dir)
                logger.info("Virtual environment removed")
                
                # Recreate virtual environment
                subprocess.run([
                    sys.executable, "-m", "venv", "venv"
                ], cwd=self.project_root, check=True)
                
                logger.info("New virtual environment created")
                logger.warning("Remember to activate venv and run: pip install -r requirements.txt")
                
            except Exception as e:
                logger.error(f"Failed to reset virtual environment: {e}")
                raise
        else:
            logger.info("No virtual environment found")
            
    async def get_environment_status(self) -> Dict[str, Any]:
        """Get current environment status."""
        status = {}
        
        try:
            # Docker status
            try:
                result = subprocess.run(
                    ["docker-compose", "ps", "--format", "json"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    import json
                    services = [json.loads(line) for line in result.stdout.strip().split('\n') if line]
                    status["docker"] = {
                        "available": True,
                        "services": len(services),
                        "running": len([s for s in services if s.get("State") == "running"])
                    }
                else:
                    status["docker"] = {"available": False, "error": "docker-compose not working"}
            except FileNotFoundError:
                status["docker"] = {"available": False, "error": "docker-compose not found"}
            
            # Database status
            if self.db_manager:
                try:
                    # Test connections
                    postgres_conn = await self.db_manager.get_postgres_connection()
                    redis_conn = await self.db_manager.get_redis_connection()
                    neo4j_session = await self.db_manager.get_neo4j_session()
                    
                    status["databases"] = {
                        "postgresql": "connected",
                        "redis": "connected", 
                        "neo4j": "connected"
                    }
                except Exception as e:
                    status["databases"] = {"error": str(e)}
            
            # File system status
            logs_dir = self.project_root / "logs"
            venv_dir = self.project_root / "venv"
            
            status["filesystem"] = {
                "logs_exist": logs_dir.exists(),
                "log_files": len(list(logs_dir.glob("*.log*"))) if logs_dir.exists() else 0,
                "venv_exists": venv_dir.exists(),
                "cache_dirs": len(list(self.project_root.glob("**/__pycache__")))
            }
            
        except Exception as e:
            logger.error(f"Error getting environment status: {e}")
            status["error"] = str(e)
            
        return status


async def main():
    """Main function to run environment reset."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reset development environment")
    parser.add_argument("--no-databases", action="store_true", help="Skip database reset")
    parser.add_argument("--no-logs", action="store_true", help="Skip log cleanup")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache cleanup")
    parser.add_argument("--no-docker", action="store_true", help="Skip Docker services reset")
    parser.add_argument("--remove-venv", action="store_true", help="Remove and recreate virtual environment")
    parser.add_argument("--status-only", action="store_true", help="Only show environment status")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
        
    resetter = EnvironmentResetter()
    
    try:
        if args.status_only:
            if not args.no_docker:
                resetter.db_manager = DatabaseManager()
                
            status = await resetter.get_environment_status()
            print("\n=== Environment Status ===")
            for component, info in status.items():
                print(f"\n{component.upper()}:")
                if isinstance(info, dict):
                    for key, value in info.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {info}")
        else:
            # Confirm destructive operation
            if not args.quiet:
                print("\n⚠️  WARNING: This will reset your development environment!")
                print("This operation will:")
                if not args.no_docker: print("  - Stop and restart Docker services")
                if not args.no_databases: print("  - Clear all database data")
                if not args.no_logs: print("  - Remove all log files")
                if not args.no_cache: print("  - Clean Python cache and temporary files")
                if args.remove_venv: print("  - Remove and recreate virtual environment")
                
                confirm = input("\nDo you want to continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Operation cancelled.")
                    return
                    
            success = await resetter.reset_all(
                databases=not args.no_databases,
                logs=not args.no_logs,
                cache=not args.no_cache,
                docker=not args.no_docker,
                keep_venv=not args.remove_venv
            )
            
            if success:
                print("\n✅ Environment reset completed successfully!")
                print("\nNext steps:")
                if args.remove_venv:
                    print("1. Activate virtual environment: source venv/bin/activate")
                    print("2. Install dependencies: pip install -r requirements.txt")
                if not args.no_docker:
                    print("3. Wait for databases to initialize (~30 seconds)")
                    print("4. Initialize databases: python scripts/init_databases.py")
                    print("5. Optionally populate test data: python scripts/populate_test_data.py")
                
            else:
                print("\n❌ Environment reset failed!")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        if resetter.db_manager:
            await resetter.db_manager.close_all()


if __name__ == "__main__":
    asyncio.run(main())