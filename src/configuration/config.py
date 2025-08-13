"""
Configuration management for Smart News application.
Uses Pydantic v2 for configuration validation and loading.
"""

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field

class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    format: str = Field(default="%(asctime)s | %(levelname)s | %(name)s:%(filename)s:%(lineno)d - %(message)s")
    console_output: bool = Field(default=True)
    file_output: bool = Field(default=False)
    log_file: str = Field(default="logs/smart-news.log")


class AppConfig(BaseModel):
    """Application configuration settings."""
    name: str = Field(default="Smart News")
    version: str = Field(default="0.1.0")


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    host: str = Field(default="localhost")
    port: int = Field(ge=1, le=65535, default=5432)
    database: str = Field(default="smart_news")
    user: str = Field(default="postgres")
    password: str = Field(default="")
    min_size: int = Field(default=5, ge=1)
    max_size: int = Field(default=10, ge=1)


class MinIOConfig(BaseModel):
    """MinIO configuration settings."""
    host: str = Field(default="localhost")
    port: int = Field(ge=1, le=65535, default=9000)
    access_key: str = Field(default="root")
    secret_key: str = Field(default="password")
    bucket: str = Field(default="news-reports")
    secure: bool = Field(default=False)


class Config(BaseModel):
    """Main configuration class that combines all configuration sections."""
    logging: LoggingConfig = LoggingConfig()
    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    minio: MinIOConfig = MinIOConfig()

    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file. If None, uses default location.
            
        Returns:
            Config instance with loaded settings.
            
        Raises:
            FileNotFoundError: If config file doesn't exist.
            yaml.YAMLError: If config file has invalid YAML syntax.
            ValidationError: If config values don't match expected types.
        """
        if config_path is None:
            raise ValueError("Configuration file path must be provided")

        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            print(f"Configuration loaded from: {config_path}")
            return cls(**config_data)
            
        except yaml.YAMLError as e:
            print(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            print(f"Error loading configuration: {e}")
            raise

    def save_to_file(self, config_path: str) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            config_path: Path where to save configuration.
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.model_dump(), f, default_flow_style=False, indent=2)
            
            print(f"Configuration saved to: {config_path}")
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
            raise

    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self.logging

    def get_app_config(self) -> AppConfig:
        """Get application configuration."""
        return self.app

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.database

    def get_minio_config(self) -> MinIOConfig:
        """Get MinIO configuration."""
        return self.minio
