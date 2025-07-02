"""
Database connection utilities for PostgreSQL, Redis, and Neo4j.
Provides connection classes with proper pooling, error handling, and retry logic.
"""

import asyncio
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Union

import redis
from neo4j import GraphDatabase, Driver, Session
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session as SQLSession

from .config import settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class PostgreSQLConnection:
    """PostgreSQL connection manager using SQLAlchemy."""
    
    def __init__(self, connection_url: Optional[str] = None):
        """
        Initialize PostgreSQL connection.
        
        Args:
            connection_url: Optional custom connection URL. Uses settings if not provided.
        """
        self.connection_url = connection_url or settings.postgres_url
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        
    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine, creating it if necessary."""
        if self._engine is None:
            self._engine = create_engine(
                self.connection_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=settings.debug
            )
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get session factory, creating it if necessary."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory
    
    @contextmanager
    def get_session(self) -> Generator[SQLSession, None, None]:
        """
        Get a database session with automatic cleanup.
        
        Yields:
            SQLAlchemy session
            
        Raises:
            ConnectionError: If database connection fails
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                logger.info("PostgreSQL connection test successful")
                return True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of result dictionaries
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_session() as session:
                result = session.execute(text(query), params or {})
                if result.returns_rows:
                    return [dict(row._mapping) for row in result]
                return []
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
    
    def close(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("PostgreSQL connections closed")


class RedisConnection:
    """Redis connection manager with connection pooling."""
    
    def __init__(self, connection_url: Optional[str] = None):
        """
        Initialize Redis connection.
        
        Args:
            connection_url: Optional custom connection URL. Uses settings if not provided.
        """
        self.connection_url = connection_url or settings.redis_url
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        
    @property
    def pool(self) -> redis.ConnectionPool:
        """Get Redis connection pool, creating it if necessary."""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                self.connection_url,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=True
            )
        return self._pool
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client, creating it if necessary."""
        if self._client is None:
            self._client = redis.Redis(connection_pool=self.pool)
        return self._client
    
    def test_connection(self) -> bool:
        """
        Test Redis connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.client.ping()
            if response:
                logger.info("Redis connection test successful")
                return True
            return False
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            return False
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Value if exists, None otherwise
            
        Raises:
            DatabaseError: If Redis operation fails
        """
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET operation failed: {e}")
            raise DatabaseError(f"Redis GET operation failed: {e}")
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set value in Redis.
        
        Args:
            key: Redis key
            value: Value to set
            ex: Optional expiration time in seconds
            
        Returns:
            True if successful
            
        Raises:
            DatabaseError: If Redis operation fails
        """
        try:
            return self.client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis SET operation failed: {e}")
            raise DatabaseError(f"Redis SET operation failed: {e}")
    
    def delete(self, *keys: str) -> int:
        """
        Delete keys from Redis.
        
        Args:
            keys: Keys to delete
            
        Returns:
            Number of keys deleted
            
        Raises:
            DatabaseError: If Redis operation fails
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE operation failed: {e}")
            raise DatabaseError(f"Redis DELETE operation failed: {e}")
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS operation failed: {e}")
            raise DatabaseError(f"Redis EXISTS operation failed: {e}")
    
    def close(self):
        """Close Redis connections."""
        if self._client:
            self._client.close()
            self._client = None
        if self._pool:
            self._pool.disconnect()
            self._pool = None
        logger.info("Redis connections closed")


class Neo4jConnection:
    """Neo4j connection manager with session management."""
    
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Optional custom URI. Uses settings if not provided.
            user: Optional custom user. Uses settings if not provided.
            password: Optional custom password. Uses settings if not provided.
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self._driver: Optional[Driver] = None
        
    @property
    def driver(self) -> Driver:
        """Get Neo4j driver, creating it if necessary."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
        return self._driver
    
    @contextmanager
    def get_session(self, database: Optional[str] = None) -> Generator[Session, None, None]:
        """
        Get a Neo4j session with automatic cleanup.
        
        Args:
            database: Optional database name
            
        Yields:
            Neo4j session
            
        Raises:
            ConnectionError: If database connection fails
        """
        session = self.driver.session(database=database)
        try:
            yield session
        except Exception as e:
            logger.error(f"Neo4j session error: {e}")
            raise DatabaseError(f"Neo4j operation failed: {e}")
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """
        Test Neo4j connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                if record and record["test"] == 1:
                    logger.info("Neo4j connection test successful")
                    return True
                return False
        except Exception as e:
            logger.error(f"Neo4j connection test failed: {e}")
            return False
    
    def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None, database: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Run a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            database: Optional database name
            
        Returns:
            List of result dictionaries
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_session(database=database) as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Neo4j query execution failed: {e}")
            raise DatabaseError(f"Neo4j query execution failed: {e}")
    
    def run_transaction(self, transaction_function, database: Optional[str] = None, **kwargs):
        """
        Run a transaction function.
        
        Args:
            transaction_function: Function to execute in transaction
            database: Optional database name
            **kwargs: Additional arguments for transaction function
            
        Returns:
            Result of transaction function
            
        Raises:
            DatabaseError: If transaction fails
        """
        try:
            with self.get_session(database=database) as session:
                return session.execute_write(transaction_function, **kwargs)
        except Exception as e:
            logger.error(f"Neo4j transaction failed: {e}")
            raise DatabaseError(f"Neo4j transaction failed: {e}")
    
    def close(self):
        """Close Neo4j connections."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connections closed")


class DatabaseManager:
    """Manager for all database connections."""
    
    def __init__(self):
        """Initialize database manager."""
        self.postgres = PostgreSQLConnection()
        self.redis = RedisConnection()
        self.neo4j = Neo4jConnection()
        
    def test_all_connections(self) -> Dict[str, bool]:
        """
        Test all database connections.
        
        Returns:
            Dictionary with connection test results
        """
        results = {
            "postgres": self.postgres.test_connection(),
            "redis": self.redis.test_connection(),
            "neo4j": self.neo4j.test_connection()
        }
        
        all_connected = all(results.values())
        if all_connected:
            logger.info("All database connections successful")
        else:
            failed_dbs = [db for db, success in results.items() if not success]
            logger.error(f"Failed database connections: {failed_dbs}")
            
        return results
    
    def close_all(self):
        """Close all database connections."""
        self.postgres.close()
        self.redis.close()
        self.neo4j.close()
        logger.info("All database connections closed")


# Global database manager instance
db_manager = DatabaseManager()