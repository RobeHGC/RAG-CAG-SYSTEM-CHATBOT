"""
Enhanced logging system using Loguru with structured data and correlation IDs.
Provides comprehensive logging for production monitoring and debugging.
"""

import contextvars
import json
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional, Union

from loguru import logger
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

# Context variables for request tracking
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')
user_context: ContextVar[Dict[str, Any]] = ContextVar('user_context', default={})
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class CorrelationIDFilter:
    """Custom filter to add correlation ID to log records."""
    
    def __call__(self, record):
        """Add correlation ID and context to log record."""
        record["extra"]["correlation_id"] = correlation_id.get('')
        record["extra"]["user_context"] = user_context.get({})
        record["extra"]["request_context"] = request_context.get({})
        return True


class ElasticsearchHandler:
    """Custom Loguru handler for sending logs to Elasticsearch."""
    
    def __init__(self, elasticsearch_url: str = "http://localhost:9200", 
                 index_pattern: str = "ai-companion-logs-{time:YYYY.MM.DD}"):
        """
        Initialize Elasticsearch handler.
        
        Args:
            elasticsearch_url: Elasticsearch cluster URL
            index_pattern: Index pattern for log storage
        """
        self.elasticsearch_url = elasticsearch_url
        self.index_pattern = index_pattern
        self.es_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Elasticsearch client."""
        try:
            self.es_client = Elasticsearch([self.elasticsearch_url])
            # Test connection
            self.es_client.ping()
            logger.info("Elasticsearch connection established")
        except (ESConnectionError, Exception) as e:
            logger.warning(f"Failed to connect to Elasticsearch: {e}")
            self.es_client = None
    
    def __call__(self, message):
        """Send log message to Elasticsearch."""
        if not self.es_client:
            return
        
        try:
            # Parse the log record
            record = message.record
            
            # Create structured log document
            log_doc = {
                "@timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "logger": record["name"],
                "message": record["message"],
                "module": record["module"],
                "function": record["function"],
                "line": record["line"],
                "file": record["file"].name,
                "process": record["process"].id,
                "thread": record["thread"].id,
                "correlation_id": record["extra"].get("correlation_id", ""),
                "user_context": record["extra"].get("user_context", {}),
                "request_context": record["extra"].get("request_context", {}),
                "exception": None,
                "service": "ai-companion"
            }
            
            # Add exception information if present
            if record["exception"]:
                log_doc["exception"] = {
                    "type": record["exception"].type.__name__,
                    "value": str(record["exception"].value),
                    "traceback": record["exception"].traceback
                }
            
            # Send to Elasticsearch
            index_name = datetime.now().strftime(self.index_pattern.replace("{time:", "").replace("}", ""))
            self.es_client.index(
                index=index_name,
                body=log_doc
            )
            
        except Exception as e:
            # Avoid infinite recursion by using print instead of logger
            print(f"Failed to send log to Elasticsearch: {e}")


class EnhancedLogger:
    """Enhanced logging system with structured data and context management."""
    
    def __init__(self, service_name: str = "ai-companion", 
                 enable_elasticsearch: bool = False,
                 elasticsearch_url: str = "http://localhost:9200"):
        """
        Initialize enhanced logger.
        
        Args:
            service_name: Name of the service
            enable_elasticsearch: Whether to enable Elasticsearch logging
            elasticsearch_url: Elasticsearch cluster URL
        """
        self.service_name = service_name
        self.enable_elasticsearch = enable_elasticsearch
        self.elasticsearch_url = elasticsearch_url
        
        # Remove default logger
        logger.remove()
        
        # Configure enhanced logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging handlers and formatters."""
        
        # Console handler with colorization
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{extra[correlation_id]}</cyan> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            filter=CorrelationIDFilter(),
            colorize=True
        )
        
        # File handler with detailed information
        logger.add(
            "logs/enhanced.log",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[correlation_id]} | "
                   "{name}:{function}:{line} | {message}",
            filter=CorrelationIDFilter(),
            rotation="100 MB",
            retention="30 days",
            compression="gz"
        )
        
        # JSON handler for structured logging
        logger.add(
            "logs/enhanced.json",
            level="INFO",
            format=lambda record: json.dumps({
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "service": self.service_name,
                "logger": record["name"],
                "message": record["message"],
                "module": record["module"],
                "function": record["function"],
                "line": record["line"],
                "file": record["file"].name,
                "correlation_id": record["extra"].get("correlation_id", ""),
                "user_context": record["extra"].get("user_context", {}),
                "request_context": record["extra"].get("request_context", {}),
                "exception": {
                    "type": record["exception"].type.__name__,
                    "value": str(record["exception"].value),
                    "traceback": record["exception"].traceback
                } if record["exception"] else None
            }) + "\n",
            filter=CorrelationIDFilter(),
            rotation="100 MB",
            retention="30 days",
            compression="gz"
        )
        
        # Error-only handler
        logger.add(
            "logs/errors_enhanced.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[correlation_id]} | "
                   "{name}:{function}:{line} | {message} | {exception}",
            filter=CorrelationIDFilter(),
            rotation="50 MB",
            retention="90 days",
            compression="gz"
        )
        
        # Elasticsearch handler if enabled
        if self.enable_elasticsearch:
            logger.add(
                ElasticsearchHandler(self.elasticsearch_url),
                level="INFO",
                filter=CorrelationIDFilter(),
                format="{message}"  # ElasticsearchHandler handles formatting
            )
    
    def generate_correlation_id(self) -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())
    
    def set_correlation_id(self, correlation_id_value: str):
        """Set correlation ID for current context."""
        correlation_id.set(correlation_id_value)
    
    def set_user_context(self, user_id: str, **kwargs):
        """Set user context for logging."""
        context = {"user_id": user_id, **kwargs}
        user_context.set(context)
    
    def set_request_context(self, endpoint: str, method: str = "GET", **kwargs):
        """Set request context for logging."""
        context = {
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        request_context.set(context)
    
    def clear_context(self):
        """Clear all context variables."""
        correlation_id.set('')
        user_context.set({})
        request_context.set({})
    
    def get_logger(self, name: str = None):
        """Get logger instance with context."""
        if name:
            return logger.bind(service=self.service_name, component=name)
        return logger.bind(service=self.service_name)


def with_logging_context(correlation_id_value: str = None, 
                        user_id: str = None,
                        endpoint: str = None,
                        **kwargs):
    """
    Decorator to set logging context for a function.
    
    Args:
        correlation_id_value: Optional correlation ID
        user_id: Optional user ID
        endpoint: Optional endpoint name
        **kwargs: Additional context data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **func_kwargs):
            # Generate correlation ID if not provided
            cid = correlation_id_value or enhanced_logger.generate_correlation_id()
            
            # Set context
            enhanced_logger.set_correlation_id(cid)
            
            if user_id:
                enhanced_logger.set_user_context(user_id, **kwargs)
            
            if endpoint:
                enhanced_logger.set_request_context(endpoint, **kwargs)
            
            try:
                return func(*args, **func_kwargs)
            finally:
                # Clear context after function execution
                enhanced_logger.clear_context()
        
        return wrapper
    return decorator


def log_performance(operation: str, threshold_ms: float = 1000.0):
    """
    Decorator to log function performance.
    
    Args:
        operation: Name of the operation being performed
        threshold_ms: Threshold in milliseconds to log warning
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger_instance = enhanced_logger.get_logger(func.__module__)
            
            try:
                logger_instance.debug(f"Starting {operation}")
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                
                if duration_ms > threshold_ms:
                    logger_instance.warning(
                        f"{operation} took {duration_ms:.2f}ms (threshold: {threshold_ms}ms)",
                        extra={"operation": operation, "duration_ms": duration_ms}
                    )
                else:
                    logger_instance.debug(
                        f"{operation} completed in {duration_ms:.2f}ms",
                        extra={"operation": operation, "duration_ms": duration_ms}
                    )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger_instance.error(
                    f"{operation} failed after {duration_ms:.2f}ms: {e}",
                    extra={"operation": operation, "duration_ms": duration_ms, "error": str(e)}
                )
                raise
        
        return wrapper
    return decorator


def log_memory_operation(operation_type: str, user_id: str = None):
    """
    Decorator specifically for memory system operations.
    
    Args:
        operation_type: Type of memory operation
        user_id: Optional user ID
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger_instance = enhanced_logger.get_logger("memory_system")
            
            # Extract user_id from kwargs if not provided
            uid = user_id or kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
            
            if uid:
                enhanced_logger.set_user_context(uid)
            
            logger_instance.info(
                f"Memory operation started: {operation_type}",
                extra={
                    "operation_type": operation_type,
                    "user_id": uid,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
            )
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger_instance.info(
                    f"Memory operation completed: {operation_type} in {duration_ms:.2f}ms",
                    extra={
                        "operation_type": operation_type,
                        "user_id": uid,
                        "duration_ms": duration_ms,
                        "status": "success"
                    }
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger_instance.error(
                    f"Memory operation failed: {operation_type} after {duration_ms:.2f}ms",
                    extra={
                        "operation_type": operation_type,
                        "user_id": uid,
                        "duration_ms": duration_ms,
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise
        
        return wrapper
    return decorator


def setup_logging_for_service(service_name: str, 
                             enable_elasticsearch: bool = False,
                             elasticsearch_url: str = "http://localhost:9200"):
    """
    Set up enhanced logging for a service.
    
    Args:
        service_name: Name of the service
        enable_elasticsearch: Whether to enable Elasticsearch logging
        elasticsearch_url: Elasticsearch cluster URL
        
    Returns:
        Enhanced logger instance
    """
    global enhanced_logger
    enhanced_logger = EnhancedLogger(
        service_name=service_name,
        enable_elasticsearch=enable_elasticsearch,
        elasticsearch_url=elasticsearch_url
    )
    return enhanced_logger


# Global enhanced logger instance
enhanced_logger = EnhancedLogger()

# Export commonly used logger instance
log = enhanced_logger.get_logger()