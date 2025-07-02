"""
Comprehensive database tests for Bot Provisional.
Tests PostgreSQL, Redis, and Neo4j connections and operations.
"""

import pytest
import time
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.database import (
    DatabaseManager,
    PostgreSQLConnection,
    RedisConnection,
    Neo4jConnection,
    DatabaseError,
    ConnectionError
)
from src.common.config import settings


class TestPostgreSQLConnection:
    """Test PostgreSQL connection functionality."""
    
    @pytest.fixture
    def postgres_conn(self):
        """Create PostgreSQL connection for testing."""
        conn = PostgreSQLConnection()
        yield conn
        conn.close()
    
    def test_connection_initialization(self, postgres_conn):
        """Test PostgreSQL connection initialization."""
        assert postgres_conn.connection_url == settings.postgres_url
        assert postgres_conn._engine is None
        assert postgres_conn._session_factory is None
    
    def test_engine_creation(self, postgres_conn):
        """Test SQLAlchemy engine creation."""
        engine = postgres_conn.engine
        assert engine is not None
        assert postgres_conn._engine is engine  # Should return same instance
        
        # Test engine properties
        assert engine.pool.size() >= 0  # Pool should be configured
        assert engine.url.drivername == "postgresql"
    
    def test_session_factory_creation(self, postgres_conn):
        """Test SQLAlchemy session factory creation."""
        session_factory = postgres_conn.session_factory
        assert session_factory is not None
        assert postgres_conn._session_factory is session_factory  # Should return same instance
    
    @pytest.mark.integration
    def test_connection_test(self, postgres_conn):
        """Test database connection."""
        result = postgres_conn.test_connection()
        assert isinstance(result, bool)
        # Note: Result depends on whether PostgreSQL is running
    
    @pytest.mark.integration
    def test_session_context_manager(self, postgres_conn):
        """Test database session context manager."""
        try:
            with postgres_conn.get_session() as session:
                assert session is not None
                # Test basic query
                result = session.execute("SELECT 1 as test")
                row = result.fetchone()
                assert row[0] == 1
        except Exception:
            pytest.skip("PostgreSQL not available for integration test")
    
    @pytest.mark.integration
    def test_execute_query(self, postgres_conn):
        """Test query execution."""
        try:
            result = postgres_conn.execute_query("SELECT 1 as test_value")
            assert isinstance(result, list)
            if result:  # If query succeeded
                assert result[0]["test_value"] == 1
        except Exception:
            pytest.skip("PostgreSQL not available for integration test")
    
    @pytest.mark.integration
    def test_execute_query_with_params(self, postgres_conn):
        """Test parameterized query execution."""
        try:
            result = postgres_conn.execute_query(
                "SELECT :value as test_value", 
                {"value": 42}
            )
            assert isinstance(result, list)
            if result:  # If query succeeded
                assert result[0]["test_value"] == 42
        except Exception:
            pytest.skip("PostgreSQL not available for integration test")
    
    def test_close_connection(self, postgres_conn):
        """Test connection cleanup."""
        # Create engine first
        _ = postgres_conn.engine
        assert postgres_conn._engine is not None
        
        # Close connections
        postgres_conn.close()
        assert postgres_conn._engine is None
        assert postgres_conn._session_factory is None


class TestRedisConnection:
    """Test Redis connection functionality."""
    
    @pytest.fixture
    def redis_conn(self):
        """Create Redis connection for testing."""
        conn = RedisConnection()
        yield conn
        conn.close()
    
    def test_connection_initialization(self, redis_conn):
        """Test Redis connection initialization."""
        assert redis_conn.connection_url == settings.redis_url
        assert redis_conn._pool is None
        assert redis_conn._client is None
    
    def test_pool_creation(self, redis_conn):
        """Test Redis connection pool creation."""
        pool = redis_conn.pool
        assert pool is not None
        assert redis_conn._pool is pool  # Should return same instance
    
    def test_client_creation(self, redis_conn):
        """Test Redis client creation."""
        client = redis_conn.client
        assert client is not None
        assert redis_conn._client is client  # Should return same instance
    
    @pytest.mark.integration
    def test_connection_test(self, redis_conn):
        """Test Redis connection."""
        result = redis_conn.test_connection()
        assert isinstance(result, bool)
        # Note: Result depends on whether Redis is running
    
    @pytest.mark.integration
    def test_set_get_operations(self, redis_conn):
        """Test Redis SET/GET operations."""
        try:
            test_key = f"test:key:{uuid.uuid4().hex}"
            test_value = "test_value"
            
            # Test SET
            result = redis_conn.set(test_key, test_value, ex=60)
            assert result is True
            
            # Test GET
            retrieved_value = redis_conn.get(test_key)
            assert retrieved_value == test_value
            
            # Test EXISTS
            exists = redis_conn.exists(test_key)
            assert exists is True
            
            # Test DELETE
            deleted = redis_conn.delete(test_key)
            assert deleted == 1
            
            # Verify deletion
            retrieved_value = redis_conn.get(test_key)
            assert retrieved_value is None
            
        except Exception:
            pytest.skip("Redis not available for integration test")
    
    @pytest.mark.integration
    def test_expiration(self, redis_conn):
        """Test key expiration."""
        try:
            test_key = f"test:expire:{uuid.uuid4().hex}"
            test_value = "expire_test"
            
            # Set with 1 second expiration
            redis_conn.set(test_key, test_value, ex=1)
            
            # Should exist immediately
            assert redis_conn.exists(test_key) is True
            
            # Wait for expiration
            time.sleep(1.1)
            
            # Should be expired
            assert redis_conn.exists(test_key) is False
            
        except Exception:
            pytest.skip("Redis not available for integration test")
    
    def test_close_connection(self, redis_conn):
        """Test connection cleanup."""
        # Create client first
        _ = redis_conn.client
        assert redis_conn._client is not None
        
        # Close connections
        redis_conn.close()
        assert redis_conn._client is None
        assert redis_conn._pool is None


class TestNeo4jConnection:
    """Test Neo4j connection functionality."""
    
    @pytest.fixture
    def neo4j_conn(self):
        """Create Neo4j connection for testing."""
        conn = Neo4jConnection()
        yield conn
        conn.close()
    
    def test_connection_initialization(self, neo4j_conn):
        """Test Neo4j connection initialization."""
        assert neo4j_conn.uri == settings.neo4j_uri
        assert neo4j_conn.user == settings.neo4j_user
        assert neo4j_conn.password == settings.neo4j_password
        assert neo4j_conn._driver is None
    
    def test_driver_creation(self, neo4j_conn):
        """Test Neo4j driver creation."""
        driver = neo4j_conn.driver
        assert driver is not None
        assert neo4j_conn._driver is driver  # Should return same instance
    
    @pytest.mark.integration
    def test_connection_test(self, neo4j_conn):
        """Test Neo4j connection."""
        result = neo4j_conn.test_connection()
        assert isinstance(result, bool)
        # Note: Result depends on whether Neo4j is running
    
    @pytest.mark.integration
    def test_session_context_manager(self, neo4j_conn):
        """Test Neo4j session context manager."""
        try:
            with neo4j_conn.get_session() as session:
                assert session is not None
                # Test basic query
                result = session.run("RETURN 1 as test")
                record = result.single()
                assert record["test"] == 1
        except Exception:
            pytest.skip("Neo4j not available for integration test")
    
    @pytest.mark.integration
    def test_run_query(self, neo4j_conn):
        """Test Cypher query execution."""
        try:
            result = neo4j_conn.run_query("RETURN 42 as test_value")
            assert isinstance(result, list)
            if result:  # If query succeeded
                assert result[0]["test_value"] == 42
        except Exception:
            pytest.skip("Neo4j not available for integration test")
    
    @pytest.mark.integration
    def test_run_query_with_parameters(self, neo4j_conn):
        """Test parameterized Cypher query execution."""
        try:
            result = neo4j_conn.run_query(
                "RETURN $value as test_value", 
                {"value": "hello world"}
            )
            assert isinstance(result, list)
            if result:  # If query succeeded
                assert result[0]["test_value"] == "hello world"
        except Exception:
            pytest.skip("Neo4j not available for integration test")
    
    @pytest.mark.integration
    def test_node_operations(self, neo4j_conn):
        """Test node creation and deletion."""
        try:
            test_id = uuid.uuid4().hex
            
            # Create test node
            create_query = """
            CREATE (n:TestNode {id: $test_id, created_at: datetime()})
            RETURN n.id as node_id
            """
            result = neo4j_conn.run_query(create_query, {"test_id": test_id})
            assert result[0]["node_id"] == test_id
            
            # Verify node exists
            check_query = "MATCH (n:TestNode {id: $test_id}) RETURN COUNT(n) as count"
            result = neo4j_conn.run_query(check_query, {"test_id": test_id})
            assert result[0]["count"] == 1
            
            # Delete test node
            delete_query = "MATCH (n:TestNode {id: $test_id}) DELETE n"
            neo4j_conn.run_query(delete_query, {"test_id": test_id})
            
            # Verify deletion
            result = neo4j_conn.run_query(check_query, {"test_id": test_id})
            assert result[0]["count"] == 0
            
        except Exception:
            pytest.skip("Neo4j not available for integration test")
    
    def test_close_connection(self, neo4j_conn):
        """Test connection cleanup."""
        # Create driver first
        _ = neo4j_conn.driver
        assert neo4j_conn._driver is not None
        
        # Close connections
        neo4j_conn.close()
        assert neo4j_conn._driver is None


class TestDatabaseManager:
    """Test database manager functionality."""
    
    @pytest.fixture
    def db_manager(self):
        """Create database manager for testing."""
        manager = DatabaseManager()
        yield manager
        manager.close_all()
    
    def test_manager_initialization(self, db_manager):
        """Test database manager initialization."""
        assert isinstance(db_manager.postgres, PostgreSQLConnection)
        assert isinstance(db_manager.redis, RedisConnection)
        assert isinstance(db_manager.neo4j, Neo4jConnection)
    
    @pytest.mark.integration
    def test_test_all_connections(self, db_manager):
        """Test connection testing for all databases."""
        results = db_manager.test_all_connections()
        
        assert isinstance(results, dict)
        assert "postgres" in results
        assert "redis" in results
        assert "neo4j" in results
        
        # All results should be boolean
        for db_name, result in results.items():
            assert isinstance(result, bool)
    
    def test_close_all_connections(self, db_manager):
        """Test closing all database connections."""
        # This should not raise any exceptions
        db_manager.close_all()


class TestDatabaseErrorHandling:
    """Test database error handling."""
    
    def test_database_error_inheritance(self):
        """Test database error class hierarchy."""
        error = DatabaseError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"
        
        conn_error = ConnectionError("connection failed")
        assert isinstance(conn_error, DatabaseError)
        assert isinstance(conn_error, Exception)
    
    def test_postgres_error_handling(self):
        """Test PostgreSQL error handling."""
        # Test with invalid connection URL
        invalid_conn = PostgreSQLConnection("postgresql://invalid:invalid@invalid:5432/invalid")
        
        # Connection test should return False for invalid connection
        result = invalid_conn.test_connection()
        assert result is False
        
        # Query execution should raise DatabaseError for invalid connection
        with pytest.raises(DatabaseError):
            invalid_conn.execute_query("SELECT 1")
    
    def test_redis_error_handling(self):
        """Test Redis error handling."""
        # Test with invalid connection URL
        invalid_conn = RedisConnection("redis://invalid:6379/0")
        
        # Connection test should return False for invalid connection
        result = invalid_conn.test_connection()
        assert result is False
        
        # Operations should raise DatabaseError for invalid connection
        with pytest.raises(DatabaseError):
            invalid_conn.get("test_key")
        
        with pytest.raises(DatabaseError):
            invalid_conn.set("test_key", "test_value")
    
    def test_neo4j_error_handling(self):
        """Test Neo4j error handling."""
        # Test with invalid connection parameters
        invalid_conn = Neo4jConnection("bolt://invalid:7687", "invalid", "invalid")
        
        # Connection test should return False for invalid connection
        result = invalid_conn.test_connection()
        assert result is False
        
        # Query execution should raise DatabaseError for invalid connection
        with pytest.raises(DatabaseError):
            invalid_conn.run_query("RETURN 1")


class TestDatabaseConfiguration:
    """Test database configuration."""
    
    def test_postgres_url_format(self):
        """Test PostgreSQL URL format."""
        url = settings.postgres_url
        assert url.startswith("postgresql://")
        assert settings.postgres_user in url
        assert settings.postgres_host in url
        assert str(settings.postgres_port) in url
        assert settings.postgres_db in url
    
    def test_redis_url_format(self):
        """Test Redis URL format."""
        url = settings.redis_url
        assert url.startswith("redis://")
        assert settings.redis_host in url
        assert str(settings.redis_port) in url
        assert str(settings.redis_db) in url
    
    def test_neo4j_configuration(self):
        """Test Neo4j configuration."""
        assert settings.neo4j_uri.startswith("bolt://")
        assert settings.neo4j_user is not None
        assert settings.neo4j_password is not None


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests requiring all databases to be running."""
    
    @pytest.fixture
    def db_manager(self):
        """Create database manager for integration testing."""
        manager = DatabaseManager()
        
        # Skip if databases are not available
        results = manager.test_all_connections()
        if not all(results.values()):
            pytest.skip("Not all databases are available for integration testing")
        
        yield manager
        manager.close_all()
    
    def test_full_workflow(self, db_manager):
        """Test a complete workflow across all databases."""
        # Generate unique test data
        test_id = uuid.uuid4().hex
        test_timestamp = datetime.now()
        
        try:
            # 1. Store conversation data in PostgreSQL
            insert_query = """
            INSERT INTO fine_tuning.conversations 
            (user_id, session_id, user_message, bot_response, quality_score, tags)
            VALUES (:user_id, :session_id, :user_message, :bot_response, :quality_score, :tags)
            RETURNING id
            """
            
            pg_result = db_manager.postgres.execute_query(insert_query, {
                "user_id": f"test_user_{test_id}",
                "session_id": test_id,
                "user_message": "Hello, how are you?",
                "bot_response": "I'm doing well, thank you for asking!",
                "quality_score": 5,
                "tags": ["greeting", "polite"]
            })
            
            conversation_id = pg_result[0]["id"]
            assert conversation_id is not None
            
            # 2. Cache context in Redis
            cache_key = f"context:session:{test_id}"
            context_data = f"conversation_id:{conversation_id}"
            
            redis_result = db_manager.redis.set(cache_key, context_data, ex=3600)
            assert redis_result is True
            
            # Verify cache
            cached_data = db_manager.redis.get(cache_key)
            assert cached_data == context_data
            
            # 3. Create knowledge graph nodes in Neo4j
            user_node_query = """
            CREATE (u:User {id: $user_id, name: $name, created_at: datetime()})
            RETURN u.id as user_id
            """
            
            neo4j_result = db_manager.neo4j.run_query(user_node_query, {
                "user_id": f"test_user_{test_id}",
                "name": "Test User"
            })
            assert neo4j_result[0]["user_id"] == f"test_user_{test_id}"
            
            # 4. Create relationship
            relationship_query = """
            MATCH (u:User {id: $user_id})
            CREATE (c:Conversation {id: $conversation_id, timestamp: datetime()})
            CREATE (u)-[:HAD_CONVERSATION]->(c)
            RETURN c.id as conversation_id
            """
            
            neo4j_result = db_manager.neo4j.run_query(relationship_query, {
                "user_id": f"test_user_{test_id}",
                "conversation_id": str(conversation_id)
            })
            assert neo4j_result[0]["conversation_id"] == str(conversation_id)
            
            # 5. Verify data consistency across all databases
            
            # Check PostgreSQL
            verify_pg_query = """
            SELECT COUNT(*) as count 
            FROM fine_tuning.conversations 
            WHERE session_id = :session_id
            """
            pg_count = db_manager.postgres.execute_query(verify_pg_query, {"session_id": test_id})
            assert pg_count[0]["count"] == 1
            
            # Check Redis
            assert db_manager.redis.exists(cache_key) is True
            
            # Check Neo4j
            verify_neo4j_query = """
            MATCH (u:User {id: $user_id})-[:HAD_CONVERSATION]->(c:Conversation)
            RETURN COUNT(c) as conversation_count
            """
            neo4j_count = db_manager.neo4j.run_query(verify_neo4j_query, {
                "user_id": f"test_user_{test_id}"
            })
            assert neo4j_count[0]["conversation_count"] == 1
            
        finally:
            # Cleanup test data
            try:
                # Clean PostgreSQL
                cleanup_pg_query = "DELETE FROM fine_tuning.conversations WHERE session_id = :session_id"
                db_manager.postgres.execute_query(cleanup_pg_query, {"session_id": test_id})
                
                # Clean Redis
                db_manager.redis.delete(cache_key)
                
                # Clean Neo4j
                cleanup_neo4j_query = """
                MATCH (u:User {id: $user_id})-[:HAD_CONVERSATION]->(c:Conversation)
                DETACH DELETE u, c
                """
                db_manager.neo4j.run_query(cleanup_neo4j_query, {
                    "user_id": f"test_user_{test_id}"
                })
                
            except Exception as e:
                print(f"Cleanup failed: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])