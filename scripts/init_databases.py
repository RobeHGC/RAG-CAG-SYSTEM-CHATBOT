#!/usr/bin/env python3
"""
Database initialization script for Bot Provisional.
This script initializes PostgreSQL, Redis, and Neo4j databases with proper schemas and initial data.
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple

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
    if status == "success":
        print(f"{Colors.GREEN}✓{Colors.END} {message}")
    elif status == "error":
        print(f"{Colors.RED}✗{Colors.END} {message}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
    elif status == "info":
        print(f"{Colors.BLUE}ℹ{Colors.END} {message}")
    elif status == "progress":
        print(f"{Colors.CYAN}→{Colors.END} {message}")
    else:
        print(message)

def print_header(title: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}{title.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}{'='*60}{Colors.END}\n")

def wait_for_databases(db_manager: DatabaseManager, max_retries: int = 30, delay: int = 2) -> bool:
    """
    Wait for all databases to be available.
    
    Args:
        db_manager: Database manager instance
        max_retries: Maximum number of connection attempts
        delay: Delay between attempts in seconds
        
    Returns:
        True if all databases are available, False otherwise
    """
    print_status("Waiting for databases to be available...", "progress")
    
    for attempt in range(1, max_retries + 1):
        print_status(f"Connection attempt {attempt}/{max_retries}", "info")
        
        results = db_manager.test_all_connections()
        
        if all(results.values()):
            print_status("All databases are available!", "success")
            return True
        
        failed_dbs = [db for db, success in results.items() if not success]
        print_status(f"Waiting for: {', '.join(failed_dbs)}", "warning")
        
        if attempt < max_retries:
            time.sleep(delay)
    
    print_status("Timeout waiting for databases", "error")
    return False

def init_postgresql(db_manager: DatabaseManager) -> bool:
    """
    Initialize PostgreSQL database.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        True if successful, False otherwise
    """
    print_header("Initializing PostgreSQL")
    
    try:
        # Test connection
        print_status("Testing PostgreSQL connection...", "progress")
        if not db_manager.postgres.test_connection():
            print_status("PostgreSQL connection failed", "error")
            return False
        print_status("PostgreSQL connection successful", "success")
        
        # Check if schemas exist
        print_status("Checking database schemas...", "progress")
        schema_check_query = """
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name IN ('fine_tuning', 'analytics')
        """
        
        existing_schemas = db_manager.postgres.execute_query(schema_check_query)
        existing_schema_names = [row['schema_name'] for row in existing_schemas]
        
        if 'fine_tuning' in existing_schema_names and 'analytics' in existing_schema_names:
            print_status("Database schemas already exist", "success")
        else:
            print_status("Database schemas need to be created", "warning")
            print_status("Note: Schemas are created by Docker init script", "info")
        
        # Check if tables exist
        print_status("Checking database tables...", "progress")
        table_check_query = """
        SELECT table_name, table_schema
        FROM information_schema.tables 
        WHERE table_schema IN ('fine_tuning', 'analytics')
        ORDER BY table_schema, table_name
        """
        
        existing_tables = db_manager.postgres.execute_query(table_check_query)
        
        if existing_tables:
            print_status("Found existing tables:", "success")
            for table in existing_tables:
                print_status(f"  - {table['table_schema']}.{table['table_name']}", "info")
        else:
            print_status("No tables found - they should be created by Docker init script", "warning")
        
        # Verify table structure for key tables
        print_status("Verifying table structures...", "progress")
        
        # Check conversations table
        conversations_check = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'fine_tuning' AND table_name = 'conversations'
        ORDER BY ordinal_position
        """
        
        conversations_columns = db_manager.postgres.execute_query(conversations_check)
        if conversations_columns:
            print_status("Conversations table structure verified", "success")
        else:
            print_status("Conversations table not found", "warning")
        
        # Check daily_stats table
        daily_stats_check = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'analytics' AND table_name = 'daily_stats'
        ORDER BY ordinal_position
        """
        
        daily_stats_columns = db_manager.postgres.execute_query(daily_stats_check)
        if daily_stats_columns:
            print_status("Daily stats table structure verified", "success")
        else:
            print_status("Daily stats table not found", "warning")
        
        print_status("PostgreSQL initialization completed", "success")
        return True
        
    except Exception as e:
        print_status(f"PostgreSQL initialization failed: {e}", "error")
        logger.error(f"PostgreSQL initialization error: {e}")
        return False

def init_redis(db_manager: DatabaseManager) -> bool:
    """
    Initialize Redis database.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        True if successful, False otherwise
    """
    print_header("Initializing Redis")
    
    try:
        # Test connection
        print_status("Testing Redis connection...", "progress")
        if not db_manager.redis.test_connection():
            print_status("Redis connection failed", "error")
            return False
        print_status("Redis connection successful", "success")
        
        # Set up initial cache keys
        print_status("Setting up initial cache structure...", "progress")
        
        # Create namespace keys for different cache types
        cache_namespaces = [
            "context:conversations",
            "context:memory", 
            "session:active",
            "metrics:stats",
            "config:settings"
        ]
        
        for namespace in cache_namespaces:
            test_key = f"{namespace}:_init_test"
            db_manager.redis.set(test_key, "initialized", ex=60)  # Expire in 60 seconds
            print_status(f"  - {namespace} namespace ready", "info")
        
        # Set up Redis configuration keys
        print_status("Setting up configuration keys...", "progress")
        
        config_keys = {
            "config:app:version": settings.version,
            "config:app:name": settings.project_name,
            "config:cache:default_ttl": "3600",  # 1 hour default TTL
            "config:session:timeout": "86400",   # 24 hours session timeout
        }
        
        for key, value in config_keys.items():
            db_manager.redis.set(key, value)
            print_status(f"  - {key} = {value}", "info")
        
        # Test cache operations
        print_status("Testing cache operations...", "progress")
        
        # Test SET/GET
        test_key = "test:init:cache_test"
        test_value = "Redis cache working correctly"
        db_manager.redis.set(test_key, test_value, ex=60)
        
        retrieved_value = db_manager.redis.get(test_key)
        if retrieved_value == test_value:
            print_status("Cache SET/GET operations working", "success")
            db_manager.redis.delete(test_key)  # Clean up
        else:
            print_status("Cache operations failed", "error")
            return False
        
        print_status("Redis initialization completed", "success")
        return True
        
    except Exception as e:
        print_status(f"Redis initialization failed: {e}", "error")
        logger.error(f"Redis initialization error: {e}")
        return False

def init_neo4j(db_manager: DatabaseManager) -> bool:
    """
    Initialize Neo4j database.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        True if successful, False otherwise
    """
    print_header("Initializing Neo4j")
    
    try:
        # Test connection
        print_status("Testing Neo4j connection...", "progress")
        if not db_manager.neo4j.test_connection():
            print_status("Neo4j connection failed", "error")
            return False
        print_status("Neo4j connection successful", "success")
        
        # Create constraints for better performance and data integrity
        print_status("Creating database constraints...", "progress")
        
        constraints = [
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT conversation_id_unique IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT fact_id_unique IF NOT EXISTS FOR (f:Fact) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT memory_id_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT topic_name_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
        ]
        
        for constraint in constraints:
            try:
                db_manager.neo4j.run_query(constraint)
                constraint_name = constraint.split("IF NOT EXISTS FOR")[0].split("CREATE CONSTRAINT")[1].strip()
                print_status(f"  - {constraint_name} constraint created", "info")
            except Exception as e:
                if "already exists" in str(e).lower():
                    constraint_name = constraint.split("IF NOT EXISTS FOR")[0].split("CREATE CONSTRAINT")[1].strip()
                    print_status(f"  - {constraint_name} constraint already exists", "info")
                else:
                    print_status(f"  - Constraint creation failed: {e}", "warning")
        
        # Create indexes for better query performance
        print_status("Creating database indexes...", "progress")
        
        indexes = [
            "CREATE INDEX user_name_index IF NOT EXISTS FOR (u:User) ON (u.name)",
            "CREATE INDEX conversation_timestamp_index IF NOT EXISTS FOR (c:Conversation) ON (c.timestamp)",
            "CREATE INDEX fact_timestamp_index IF NOT EXISTS FOR (f:Fact) ON (f.timestamp)",
            "CREATE INDEX memory_type_index IF NOT EXISTS FOR (m:Memory) ON (m.type)",
            "CREATE INDEX topic_category_index IF NOT EXISTS FOR (t:Topic) ON (t.category)",
        ]
        
        for index in indexes:
            try:
                db_manager.neo4j.run_query(index)
                index_name = index.split("IF NOT EXISTS FOR")[0].split("CREATE INDEX")[1].strip()
                print_status(f"  - {index_name} index created", "info")
            except Exception as e:
                if "already exists" in str(e).lower():
                    index_name = index.split("IF NOT EXISTS FOR")[0].split("CREATE INDEX")[1].strip()
                    print_status(f"  - {index_name} index already exists", "info")
                else:
                    print_status(f"  - Index creation failed: {e}", "warning")
        
        # Create initial nodes if they don't exist
        print_status("Creating initial nodes...", "progress")
        
        # Create system user node
        system_user_query = """
        MERGE (u:User {id: 'system'})
        ON CREATE SET 
            u.name = 'System',
            u.type = 'system',
            u.created_at = datetime(),
            u.description = 'System user for automated processes'
        RETURN u.id as user_id
        """
        
        result = db_manager.neo4j.run_query(system_user_query)
        if result:
            print_status("  - System user node ready", "info")
        
        # Create root topic node
        root_topic_query = """
        MERGE (t:Topic {name: 'General'})
        ON CREATE SET 
            t.category = 'root',
            t.description = 'Root topic for general conversations',
            t.created_at = datetime()
        RETURN t.name as topic_name
        """
        
        result = db_manager.neo4j.run_query(root_topic_query)
        if result:
            print_status("  - Root topic node ready", "info")
        
        # Test basic graph operations
        print_status("Testing graph operations...", "progress")
        
        # Test node creation and deletion
        test_node_query = """
        CREATE (test:TestNode {id: 'init_test', created_at: datetime()})
        RETURN test.id as node_id
        """
        
        test_result = db_manager.neo4j.run_query(test_node_query)
        if test_result:
            # Clean up test node
            cleanup_query = "MATCH (test:TestNode {id: 'init_test'}) DELETE test"
            db_manager.neo4j.run_query(cleanup_query)
            print_status("Graph operations working correctly", "success")
        
        print_status("Neo4j initialization completed", "success")
        return True
        
    except Exception as e:
        print_status(f"Neo4j initialization failed: {e}", "error")
        logger.error(f"Neo4j initialization error: {e}")
        return False

def verify_all_databases(db_manager: DatabaseManager) -> bool:
    """
    Verify all databases are properly initialized.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        True if all databases are verified, False otherwise
    """
    print_header("Verifying Database Setup")
    
    # Test all connections again
    print_status("Testing all database connections...", "progress")
    results = db_manager.test_all_connections()
    
    success_count = sum(results.values())
    total_count = len(results)
    
    if success_count == total_count:
        print_status(f"All {total_count} databases connected successfully", "success")
        
        # Additional verification tests
        print_status("Running verification tests...", "progress")
        
        try:
            # PostgreSQL test
            test_query = "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema IN ('fine_tuning', 'analytics')"
            pg_result = db_manager.postgres.execute_query(test_query)
            table_count = pg_result[0]['count'] if pg_result else 0
            print_status(f"PostgreSQL: {table_count} tables found", "info")
            
            # Redis test
            redis_keys = db_manager.redis.client.keys("config:*")
            print_status(f"Redis: {len(redis_keys)} config keys found", "info")
            
            # Neo4j test
            neo4j_query = "MATCH (n) RETURN COUNT(n) as node_count"
            neo4j_result = db_manager.neo4j.run_query(neo4j_query)
            node_count = neo4j_result[0]['node_count'] if neo4j_result else 0
            print_status(f"Neo4j: {node_count} nodes found", "info")
            
            print_status("All databases verified successfully!", "success")
            return True
            
        except Exception as e:
            print_status(f"Verification tests failed: {e}", "error")
            return False
    else:
        failed_dbs = [db for db, success in results.items() if not success]
        print_status(f"Database connection failures: {', '.join(failed_dbs)}", "error")
        return False

def main():
    """Main initialization function."""
    print_header("Bot Provisional - Database Initialization")
    
    print_status("Starting database initialization process...", "info")
    print_status(f"Project: {settings.project_name} v{settings.version}", "info")
    print_status(f"Debug mode: {settings.debug}", "info")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    try:
        # Step 1: Wait for databases to be available
        if not wait_for_databases(db_manager):
            print_status("Database initialization failed - databases not available", "error")
            return 1
        
        # Step 2: Initialize PostgreSQL
        if not init_postgresql(db_manager):
            print_status("Database initialization failed - PostgreSQL setup failed", "error")
            return 1
        
        # Step 3: Initialize Redis
        if not init_redis(db_manager):
            print_status("Database initialization failed - Redis setup failed", "error")
            return 1
        
        # Step 4: Initialize Neo4j
        if not init_neo4j(db_manager):
            print_status("Database initialization failed - Neo4j setup failed", "error")
            return 1
        
        # Step 5: Final verification
        if not verify_all_databases(db_manager):
            print_status("Database initialization failed - verification failed", "error")
            return 1
        
        # Success!
        print_header("Initialization Complete")
        print_status("All databases have been successfully initialized!", "success")
        print_status("", "info")
        print_status("Next steps:", "info")
        print_status("1. Start the application services", "info")
        print_status("2. Run the test suite: pytest", "info")
        print_status("3. Check the dashboard at http://localhost:8000", "info")
        
        return 0
        
    except KeyboardInterrupt:
        print_status("\nInitialization interrupted by user", "warning")
        return 1
    except Exception as e:
        print_status(f"Unexpected error during initialization: {e}", "error")
        logger.error(f"Initialization error: {e}")
        return 1
    finally:
        # Clean up connections
        db_manager.close_all()

if __name__ == "__main__":
    sys.exit(main())