"""
Configuration management for the chatbot project.
Handles environment variables and application settings.
"""

import logging
import logging.config
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Project info
    project_name: str = "Bot Provisional"
    version: str = "0.1.0"
    debug: bool = Field(default=False, description="Debug mode")
    
    # Telegram settings
    telegram_api_id: int = Field(..., description="Telegram API ID")
    telegram_api_hash: str = Field(..., description="Telegram API Hash")
    telegram_session_name: str = Field(default="userbot", description="Session name for Telegram")
    
    # Database settings - PostgreSQL
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(..., description="PostgreSQL password")
    postgres_db: str = Field(default="bot_provisional", description="PostgreSQL database name")
    
    # Redis settings
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    
    # Neo4j settings
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j user")
    neo4j_password: str = Field(..., description="Neo4j password")
    
    # LLM settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    default_llm_provider: str = Field(default="gemini", description="Default LLM provider")
    
    # Dashboard settings
    dashboard_host: str = Field(default="0.0.0.0", description="Dashboard host")
    dashboard_port: int = Field(default=8000, description="Dashboard port")
    dashboard_reload: bool = Field(default=True, description="Auto-reload dashboard")
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    logs_dir: Optional[Path] = Field(default=None, description="Logs directory")
    data_dir: Optional[Path] = Field(default=None, description="Data directory")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    @field_validator("logs_dir", mode="before")
    @classmethod
    def set_logs_dir(cls, v, info):
        if v is None:
            return Path(__file__).parent.parent.parent / "logs"
        return Path(v)
    
    @field_validator("data_dir", mode="before")
    @classmethod
    def set_data_dir(cls, v, info):
        if v is None:
            return Path(__file__).parent.parent.parent / "data"
        return Path(v)
    
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields in .env
    )


def setup_logging(config_path: Optional[Path] = None) -> None:
    """
    Setup logging configuration from YAML file.
    
    Args:
        config_path: Path to logging configuration file. 
                    Defaults to config/logging.yaml
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "logging.yaml"
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Update file paths to be absolute
        for handler in config.get('handlers', {}).values():
            if 'filename' in handler:
                handler['filename'] = str(logs_dir / Path(handler['filename']).name)
        
        logging.config.dictConfig(config)
        logging.info(f"Logging configured from {config_path}")
    else:
        # Fallback to basic configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(logs_dir / 'bot_provisional.log')
            ]
        )
        logging.warning(f"Logging config not found at {config_path}, using basic configuration")


# Global settings instance
settings = Settings()

# Setup logging on module import
setup_logging()