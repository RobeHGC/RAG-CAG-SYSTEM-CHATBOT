#!/usr/bin/env python3
"""
Database migration script for Bot Provisional.
Handles schema changes and data migrations for PostgreSQL, Redis, and Neo4j.
"""

import sys
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import settings, setup_logging
from src.common.database import DatabaseManager, DatabaseError

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(message: str, status: str = "info"):
    """Print colored status message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "success":
        print(f"[{timestamp}] {Colors.GREEN}✓{Colors.END} {message}")
    elif status == "error":
        print(f"[{timestamp}] {Colors.RED}✗{Colors.END} {message}")
    elif status == "warning":
        print(f"[{timestamp}] {Colors.YELLOW}⚠{Colors.END} {message}")
    elif status == "info":
        print(f"[{timestamp}] {Colors.BLUE}ℹ{Colors.END} {message}")
    elif status == "progress":
        print(f"[{timestamp}] {Colors.CYAN}→{Colors.END} {message}")
    else:
        print(f"[{timestamp}] {message}")

def print_header(title: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}{title.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}{'='*60}{Colors.END}\n")

@dataclass
class Migration:
    """Represents a database migration."""
    id: str
    name: str
    description: str
    database: str  # 'postgres', 'redis', 'neo4j', or 'all'
    version: str
    sql_script: Optional[str] = None
    python_function: Optional[str] = None
    rollback_script: Optional[str] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """Ensure migration tracking table exists in PostgreSQL."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS migration_history (
            id SERIAL PRIMARY KEY,
            migration_id VARCHAR(255) UNIQUE NOT NULL,
            migration_name VARCHAR(255) NOT NULL,
            database_name VARCHAR(50) NOT NULL,
            version VARCHAR(50) NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            applied_by VARCHAR(255) DEFAULT 'system',
            checksum VARCHAR(64) NOT NULL,
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT,
            rollback_available BOOLEAN DEFAULT FALSE
        );
        
        CREATE INDEX IF NOT EXISTS idx_migration_history_migration_id 
        ON migration_history(migration_id);
        
        CREATE INDEX IF NOT EXISTS idx_migration_history_applied_at 
        ON migration_history(applied_at);
        """
        
        try:
            self.db_manager.postgres.execute_query(create_table_sql)
            print_status("Migration tracking table ready", "success")
        except Exception as e:
            print_status(f"Failed to create migration table: {e}", "error")
            raise
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate MD5 checksum of migration content."""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_migration_applied(self, migration_id: str) -> bool:
        """Check if migration has already been applied."""
        query = """
        SELECT COUNT(*) as count 
        FROM migration_history 
        WHERE migration_id = :migration_id AND success = TRUE
        """
        
        try:
            result = self.db_manager.postgres.execute_query(query, {"migration_id": migration_id})
            return result[0]["count"] > 0
        except Exception as e:
            print_status(f"Error checking migration status: {e}", "warning")
            return False
    
    def _record_migration(self, migration: Migration, success: bool, error_message: str = None):
        """Record migration execution in history."""
        checksum = ""
        if migration.sql_script:
            checksum = self._calculate_checksum(migration.sql_script)
        elif migration.python_function:
            checksum = self._calculate_checksum(migration.python_function)
        
        insert_sql = """
        INSERT INTO migration_history 
        (migration_id, migration_name, database_name, version, checksum, success, error_message, rollback_available)
        VALUES (:migration_id, :migration_name, :database_name, :version, :checksum, :success, :error_message, :rollback_available)
        """
        
        try:
            self.db_manager.postgres.execute_query(insert_sql, {
                "migration_id": migration.id,
                "migration_name": migration.name,
                "database_name": migration.database,
                "version": migration.version,
                "checksum": checksum,
                "success": success,
                "error_message": error_message,
                "rollback_available": migration.rollback_script is not None
            })
        except Exception as e:
            print_status(f"Failed to record migration: {e}", "warning")
    
    def execute_postgres_migration(self, migration: Migration) -> bool:
        """Execute PostgreSQL migration."""
        print_status(f"Executing PostgreSQL migration: {migration.name}", "progress")
        
        if not migration.sql_script:
            print_status("No SQL script provided for PostgreSQL migration", "error")
            return False
        
        try:
            # Split SQL script into individual statements
            statements = [stmt.strip() for stmt in migration.sql_script.split(';') if stmt.strip()]
            
            for statement in statements:
                self.db_manager.postgres.execute_query(statement)
            
            print_status(f"PostgreSQL migration completed: {migration.name}", "success")
            return True
            
        except Exception as e:
            print_status(f"PostgreSQL migration failed: {e}", "error")
            return False
    
    def execute_redis_migration(self, migration: Migration) -> bool:
        """Execute Redis migration."""
        print_status(f"Executing Redis migration: {migration.name}", "progress")
        
        # Redis migrations are typically Python functions
        if migration.python_function:
            try:
                # Execute Python code for Redis migration
                exec(migration.python_function)
                print_status(f"Redis migration completed: {migration.name}", "success")
                return True
            except Exception as e:
                print_status(f"Redis migration failed: {e}", "error")
                return False
        else:
            print_status("No Python function provided for Redis migration", "error")
            return False
    
    def execute_neo4j_migration(self, migration: Migration) -> bool:
        """Execute Neo4j migration."""
        print_status(f"Executing Neo4j migration: {migration.name}", "progress")
        
        if not migration.sql_script:  # Cypher script
            print_status("No Cypher script provided for Neo4j migration", "error")
            return False
        
        try:
            # Execute Cypher script
            self.db_manager.neo4j.run_query(migration.sql_script)
            print_status(f"Neo4j migration completed: {migration.name}", "success")
            return True
            
        except Exception as e:
            print_status(f"Neo4j migration failed: {e}", "error")
            return False
    
    def execute_migration(self, migration: Migration) -> bool:
        """Execute a single migration."""
        print_status(f"Starting migration: {migration.id} - {migration.name}", "info")
        
        # Check if already applied
        if self._is_migration_applied(migration.id):
            print_status(f"Migration already applied: {migration.id}", "warning")
            return True
        
        # Check dependencies
        for dep_id in migration.dependencies:
            if not self._is_migration_applied(dep_id):
                print_status(f"Dependency not met: {dep_id}", "error")
                return False
        
        success = False
        error_message = None
        
        try:
            # Execute based on database type
            if migration.database == "postgres":
                success = self.execute_postgres_migration(migration)
            elif migration.database == "redis":
                success = self.execute_redis_migration(migration)
            elif migration.database == "neo4j":
                success = self.execute_neo4j_migration(migration)
            elif migration.database == "all":
                # Execute for all databases
                success = True
                if migration.sql_script:
                    success &= self.execute_postgres_migration(migration)
                    success &= self.execute_neo4j_migration(migration)
                if migration.python_function:
                    success &= self.execute_redis_migration(migration)
            else:
                print_status(f"Unknown database type: {migration.database}", "error")
                success = False
                
        except Exception as e:
            error_message = str(e)
            success = False
            print_status(f"Migration execution failed: {e}", "error")
        
        # Record migration result
        self._record_migration(migration, success, error_message)
        
        return success
    
    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get list of applied migrations."""
        query = """
        SELECT migration_id, migration_name, database_name, version, applied_at, success
        FROM migration_history
        ORDER BY applied_at
        """
        
        try:
            return self.db_manager.postgres.execute_query(query)
        except Exception as e:
            print_status(f"Failed to get migration history: {e}", "error")
            return []
    
    def get_pending_migrations(self, migrations: List[Migration]) -> List[Migration]:
        """Get list of pending migrations."""
        applied_ids = {m["migration_id"] for m in self.get_applied_migrations() if m["success"]}
        return [m for m in migrations if m.id not in applied_ids]

def load_migrations() -> List[Migration]:
    """Load migration definitions."""
    migrations = []
    
    # Example migrations - in practice, these would be loaded from files
    
    # Migration 1: Add user preferences table to PostgreSQL
    migrations.append(Migration(
        id="001_add_user_preferences",
        name="Add user preferences table",
        description="Add table to store user preferences and settings",
        database="postgres",
        version="1.1.0",
        sql_script="""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            preference_key VARCHAR(100) NOT NULL,
            preference_value JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id, preference_key)
        );
        
        CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id 
        ON user_preferences(user_id);
        """
    ))
    
    # Migration 2: Add conversation metrics to PostgreSQL
    migrations.append(Migration(
        id="002_add_conversation_metrics",
        name="Add conversation metrics",
        description="Add detailed metrics tracking for conversations",
        database="postgres",
        version="1.1.0",
        sql_script="""
        ALTER TABLE fine_tuning.conversations 
        ADD COLUMN IF NOT EXISTS response_time_ms INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS tokens_used INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS model_used VARCHAR(100),
        ADD COLUMN IF NOT EXISTS satisfaction_score INTEGER CHECK (satisfaction_score >= 1 AND satisfaction_score <= 5);
        
        CREATE INDEX IF NOT EXISTS idx_conversations_response_time 
        ON fine_tuning.conversations(response_time_ms);
        
        CREATE INDEX IF NOT EXISTS idx_conversations_model_used 
        ON fine_tuning.conversations(model_used);
        """
    ))
    
    # Migration 3: Update Redis configuration
    migrations.append(Migration(
        id="003_update_redis_config",
        name="Update Redis configuration",
        description="Update Redis configuration with new namespaces",
        database="redis",
        version="1.1.0",
        python_function="""
# Update Redis configuration
redis_client = self.db_manager.redis.client

# Add new configuration keys
redis_client.hset('config:features', 
    'conversation_summarization', 'true',
    'sentiment_analysis', 'true',
    'topic_detection', 'true'
)

# Add new metrics tracking
redis_client.hset('metrics:features',
    'summarization_requests', '0',
    'sentiment_analyses', '0',
    'topic_detections', '0'
)

print_status("Redis configuration updated with new features", "success")
"""
    ))
    
    # Migration 4: Add relationship weights to Neo4j
    migrations.append(Migration(
        id="004_add_relationship_weights",
        name="Add relationship weights",
        description="Add weight properties to relationships for better graph analysis",
        database="neo4j",
        version="1.1.0",
        sql_script="""
        MATCH ()-[r:RELATED_TO]->()
        WHERE r.weight IS NULL
        SET r.weight = 0.5;
        
        MATCH ()-[r:KNOWS]->()
        WHERE r.weight IS NULL
        SET r.weight = 1.0;
        
        MATCH ()-[r:MENTIONS]->()
        WHERE r.weight IS NULL
        SET r.weight = 0.3;
        """
    ))
    
    # Migration 5: Comprehensive schema update for all databases
    migrations.append(Migration(
        id="005_schema_v1_1_0",
        name="Schema update to v1.1.0",
        description="Comprehensive schema update for version 1.1.0",
        database="all",
        version="1.1.0",
        sql_script="""
        -- PostgreSQL: Add version tracking
        CREATE TABLE IF NOT EXISTS schema_versions (
            id SERIAL PRIMARY KEY,
            version VARCHAR(20) UNIQUE NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            description TEXT
        );
        
        INSERT INTO schema_versions (version, description)
        VALUES ('1.1.0', 'Schema update with user preferences and conversation metrics')
        ON CONFLICT (version) DO NOTHING;
        """,
        python_function="""
# Redis: Update version info
redis_client = self.db_manager.redis.client
redis_client.hset('app:metadata', 'schema_version', '1.1.0')
print_status("Redis schema version updated to 1.1.0", "success")
""",
        dependencies=["001_add_user_preferences", "002_add_conversation_metrics", "003_update_redis_config", "004_add_relationship_weights"]
    ))
    
    return migrations

def show_migration_status(migration_manager: MigrationManager, migrations: List[Migration]):
    """Show current migration status."""
    print_header("Migration Status")
    
    applied_migrations = migration_manager.get_applied_migrations()
    pending_migrations = migration_manager.get_pending_migrations(migrations)
    
    print_status(f"Total migrations defined: {len(migrations)}", "info")
    print_status(f"Applied migrations: {len(applied_migrations)}", "success")
    print_status(f"Pending migrations: {len(pending_migrations)}", "warning")
    
    if applied_migrations:
        print("\nApplied Migrations:")
        for migration in applied_migrations:
            status_icon = "✓" if migration["success"] else "✗"
            print(f"  {status_icon} {migration['migration_id']} - {migration['migration_name']} ({migration['database_name']})")
    
    if pending_migrations:
        print("\nPending Migrations:")
        for migration in pending_migrations:
            print(f"  → {migration.id} - {migration.name} ({migration.database})")

def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration Tool for Bot Provisional")
    parser.add_argument("--action", choices=["status", "migrate", "rollback"], default="status",
                        help="Action to perform")
    parser.add_argument("--migration-id", help="Specific migration ID to target")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without executing")
    parser.add_argument("--force", action="store_true", help="Force migration even if already applied")
    
    args = parser.parse_args()
    
    print_header("Database Migration Tool")
    print_status(f"Project: {settings.project_name}", "info")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    try:
        # Test database connections
        print_status("Testing database connections...", "progress")
        results = db_manager.test_all_connections()
        
        if not all(results.values()):
            failed_dbs = [db for db, success in results.items() if not success]
            print_status(f"Database connection failures: {', '.join(failed_dbs)}", "error")
            return 1
        
        print_status("All database connections successful", "success")
        
        # Initialize migration manager
        migration_manager = MigrationManager(db_manager)
        
        # Load migrations
        migrations = load_migrations()
        
        if args.action == "status":
            show_migration_status(migration_manager, migrations)
            
        elif args.action == "migrate":
            if args.migration_id:
                # Migrate specific migration
                target_migration = next((m for m in migrations if m.id == args.migration_id), None)
                if not target_migration:
                    print_status(f"Migration not found: {args.migration_id}", "error")
                    return 1
                
                if args.dry_run:
                    print_status(f"Would execute migration: {target_migration.id}", "info")
                else:
                    success = migration_manager.execute_migration(target_migration)
                    return 0 if success else 1
            else:
                # Migrate all pending migrations
                pending = migration_manager.get_pending_migrations(migrations)
                
                if not pending:
                    print_status("No pending migrations", "success")
                    return 0
                
                print_status(f"Found {len(pending)} pending migrations", "info")
                
                if args.dry_run:
                    print_status("Would execute the following migrations:", "info")
                    for migration in pending:
                        print(f"  → {migration.id} - {migration.name}")
                    return 0
                
                # Execute pending migrations
                success_count = 0
                for migration in pending:
                    if migration_manager.execute_migration(migration):
                        success_count += 1
                    else:
                        print_status(f"Migration failed, stopping: {migration.id}", "error")
                        break
                
                print_status(f"Executed {success_count}/{len(pending)} migrations", "info")
                return 0 if success_count == len(pending) else 1
        
        elif args.action == "rollback":
            print_status("Rollback functionality not yet implemented", "warning")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print_status("\nMigration interrupted by user", "warning")
        return 130
    except Exception as e:
        print_status(f"Migration failed: {e}", "error")
        logger.error(f"Migration error: {e}")
        return 1
    finally:
        # Clean up connections
        db_manager.close_all()

if __name__ == "__main__":
    sys.exit(main())