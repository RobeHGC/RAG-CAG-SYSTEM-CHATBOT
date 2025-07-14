"""
Sentry integration for comprehensive error tracking and performance monitoring.
Provides automatic exception capture, performance monitoring, and custom context.
"""

import logging
import os
import socket
from typing import Any, Dict, Optional, Union

import sentry_sdk
from sentry_sdk import configure_scope, capture_exception, capture_message, set_user, set_tag, set_context
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

logger = logging.getLogger(__name__)


class SentryConfig:
    """Configuration and setup for Sentry error tracking."""
    
    def __init__(self, 
                 dsn: Optional[str] = None,
                 environment: str = "development",
                 release: Optional[str] = None,
                 sample_rate: float = 1.0,
                 traces_sample_rate: float = 0.1,
                 enable_performance: bool = True):
        """
        Initialize Sentry configuration.
        
        Args:
            dsn: Sentry DSN URL
            environment: Environment name (development, staging, production)
            release: Release version
            sample_rate: Error sampling rate (0.0 to 1.0)
            traces_sample_rate: Performance tracing sample rate (0.0 to 1.0)
            enable_performance: Whether to enable performance monitoring
        """
        self.dsn = dsn or os.getenv("SENTRY_DSN")
        self.environment = environment
        self.release = release or os.getenv("SENTRY_RELEASE", "unknown")
        self.sample_rate = sample_rate
        self.traces_sample_rate = traces_sample_rate
        self.enable_performance = enable_performance
        
    def initialize(self):
        """Initialize Sentry with comprehensive configuration."""
        if not self.dsn:
            logger.warning("Sentry DSN not provided. Error tracking disabled.")
            return
        
        # Configure logging integration
        logging_integration = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        # Configure integrations
        integrations = [
            logging_integration,
            FastApiIntegration(auto_session_tracking=True),
            AsyncioIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            SqlalchemyIntegration()
        ]
        
        # Initialize Sentry
        sentry_sdk.init(
            dsn=self.dsn,
            environment=self.environment,
            release=self.release,
            sample_rate=self.sample_rate,
            traces_sample_rate=self.traces_sample_rate if self.enable_performance else 0.0,
            integrations=integrations,
            send_default_pii=False,  # Don't send personally identifiable information
            attach_stacktrace=True,
            before_send=self._before_send_filter,
            before_send_transaction=self._before_send_transaction_filter
        )
        
        # Set initial context
        self._set_initial_context()
        
        logger.info(f"Sentry initialized for environment: {self.environment}")
    
    def _before_send_filter(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Filter events before sending to Sentry.
        
        Args:
            event: Sentry event data
            hint: Additional context
            
        Returns:
            Modified event or None to drop
        """
        # Filter out known non-critical errors
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            
            # Filter out connection errors that are expected
            if exc_type.__name__ in ['ConnectionError', 'TimeoutError']:
                # Only send if it's a repeated pattern (add custom logic)
                return None
        
        # Add custom tags based on error type
        if event.get('exception'):
            exception_type = event['exception']['values'][0]['type']
            set_tag("error_type", exception_type)
        
        return event
    
    def _before_send_transaction_filter(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Filter performance transactions before sending.
        
        Args:
            event: Sentry transaction event
            hint: Additional context
            
        Returns:
            Modified event or None to drop
        """
        # Filter out health check transactions
        if event.get('transaction') == '/health':
            return None
        
        # Filter out very fast transactions (< 100ms) to reduce noise
        if event.get('start_timestamp') and event.get('timestamp'):
            duration = event['timestamp'] - event['start_timestamp']
            if duration < 0.1:  # 100ms
                return None
        
        return event
    
    def _set_initial_context(self):
        """Set initial context information."""
        with configure_scope() as scope:
            # Set server information
            scope.set_tag("server_name", socket.gethostname())
            scope.set_tag("service", "ai-companion")
            
            # Set context
            scope.set_context("runtime", {
                "name": "python",
                "version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
            })


class SentryContextManager:
    """Manages Sentry context for requests and operations."""
    
    @staticmethod
    def set_user_context(user_id: str, **additional_data):
        """
        Set user context for error tracking.
        
        Args:
            user_id: User identifier
            **additional_data: Additional user data
        """
        set_user({
            "id": user_id,
            **additional_data
        })
    
    @staticmethod
    def set_memory_context(operation: str, memory_count: int, user_id: str = None):
        """
        Set memory system context.
        
        Args:
            operation: Memory operation type
            memory_count: Number of memories involved
            user_id: Optional user ID
        """
        set_context("memory_system", {
            "operation": operation,
            "memory_count": memory_count,
            "user_id": user_id
        })
    
    @staticmethod
    def set_llm_context(model: str, tokens_used: int = None, response_time: float = None):
        """
        Set LLM request context.
        
        Args:
            model: LLM model name
            tokens_used: Number of tokens used
            response_time: Response time in seconds
        """
        context = {"model": model}
        if tokens_used is not None:
            context["tokens_used"] = tokens_used
        if response_time is not None:
            context["response_time"] = response_time
        
        set_context("llm_request", context)
    
    @staticmethod
    def set_database_context(database: str, operation: str, duration: float = None):
        """
        Set database operation context.
        
        Args:
            database: Database type (postgres, redis, neo4j)
            operation: Operation type
            duration: Operation duration in seconds
        """
        context = {
            "database": database,
            "operation": operation
        }
        if duration is not None:
            context["duration"] = duration
        
        set_context("database_operation", context)
    
    @staticmethod
    def add_breadcrumb(message: str, category: str = "custom", level: str = "info", data: Dict[str, Any] = None):
        """
        Add a breadcrumb for debugging.
        
        Args:
            message: Breadcrumb message
            category: Breadcrumb category
            level: Log level
            data: Additional data
        """
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
    
    @staticmethod
    def clear_context():
        """Clear all Sentry context."""
        with configure_scope() as scope:
            scope.clear()


class SentryPerformanceMonitor:
    """Performance monitoring with Sentry transactions."""
    
    @staticmethod
    def start_transaction(name: str, op: str = "function") -> Any:
        """
        Start a performance transaction.
        
        Args:
            name: Transaction name
            op: Operation type
            
        Returns:
            Transaction object
        """
        return sentry_sdk.start_transaction(name=name, op=op)
    
    @staticmethod
    def start_span(op: str, description: str = None) -> Any:
        """
        Start a performance span.
        
        Args:
            op: Operation type
            description: Span description
            
        Returns:
            Span object
        """
        return sentry_sdk.start_span(op=op, description=description)


def capture_memory_error(error: Exception, user_id: str = None, operation: str = None, **context):
    """
    Capture memory system error with context.
    
    Args:
        error: Exception to capture
        user_id: User ID involved in the error
        operation: Memory operation that failed
        **context: Additional context data
    """
    with configure_scope() as scope:
        if user_id:
            SentryContextManager.set_user_context(user_id)
        
        if operation:
            scope.set_tag("memory_operation", operation)
        
        for key, value in context.items():
            scope.set_extra(key, value)
        
        capture_exception(error)


def capture_llm_error(error: Exception, model: str = None, user_id: str = None, **context):
    """
    Capture LLM-related error with context.
    
    Args:
        error: Exception to capture
        model: LLM model involved
        user_id: User ID for the request
        **context: Additional context data
    """
    with configure_scope() as scope:
        if user_id:
            SentryContextManager.set_user_context(user_id)
        
        if model:
            scope.set_tag("llm_model", model)
        
        for key, value in context.items():
            scope.set_extra(key, value)
        
        capture_exception(error)


def capture_database_error(error: Exception, database: str, operation: str = None, **context):
    """
    Capture database error with context.
    
    Args:
        error: Exception to capture
        database: Database type (postgres, redis, neo4j)
        operation: Database operation that failed
        **context: Additional context data
    """
    with configure_scope() as scope:
        scope.set_tag("database", database)
        
        if operation:
            scope.set_tag("database_operation", operation)
        
        for key, value in context.items():
            scope.set_extra(key, value)
        
        capture_exception(error)


def track_memory_performance(func):
    """
    Decorator to track memory operation performance in Sentry.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        transaction_name = f"memory.{func.__name__}"
        
        with sentry_sdk.start_transaction(name=transaction_name, op="memory_operation"):
            # Extract user_id if available
            user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
            
            if user_id:
                SentryContextManager.set_user_context(user_id)
            
            SentryContextManager.add_breadcrumb(
                message=f"Starting memory operation: {func.__name__}",
                category="memory",
                data={"args_count": len(args), "kwargs": list(kwargs.keys())}
            )
            
            try:
                result = func(*args, **kwargs)
                
                SentryContextManager.add_breadcrumb(
                    message=f"Memory operation completed: {func.__name__}",
                    category="memory",
                    level="info"
                )
                
                return result
                
            except Exception as e:
                capture_memory_error(
                    e, 
                    user_id=user_id, 
                    operation=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
                raise
    
    return wrapper


def track_llm_performance(model: str = None):
    """
    Decorator to track LLM performance in Sentry.
    
    Args:
        model: LLM model name
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            transaction_name = f"llm.{func.__name__}"
            
            with sentry_sdk.start_transaction(name=transaction_name, op="llm_request"):
                # Extract model from args or kwargs if not provided
                model_name = model or kwargs.get('model') or 'unknown'
                
                SentryContextManager.set_llm_context(model_name)
                
                SentryContextManager.add_breadcrumb(
                    message=f"Starting LLM request: {func.__name__}",
                    category="llm",
                    data={"model": model_name}
                )
                
                try:
                    result = func(*args, **kwargs)
                    
                    SentryContextManager.add_breadcrumb(
                        message=f"LLM request completed: {func.__name__}",
                        category="llm",
                        level="info"
                    )
                    
                    return result
                    
                except Exception as e:
                    capture_llm_error(
                        e,
                        model=model_name,
                        operation=func.__name__
                    )
                    raise
        
        return wrapper
    return decorator


# Global Sentry configuration instance
sentry_config = SentryConfig()

# Convenience aliases
set_user_context = SentryContextManager.set_user_context
set_memory_context = SentryContextManager.set_memory_context
set_llm_context = SentryContextManager.set_llm_context
set_database_context = SentryContextManager.set_database_context
add_breadcrumb = SentryContextManager.add_breadcrumb
clear_context = SentryContextManager.clear_context