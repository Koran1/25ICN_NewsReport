"""
Logging configuration and setup for Smart News application.
Provides centralized logging functionality that can be used across the application.
"""

import inspect
import logging
import sys
from pathlib import Path
from typing import Optional

from configuration.config import Config


class LoggerManager:
    """
    Centralized logging manager for the Smart News application.
    Handles logging configuration, setup, and provides utility methods for logging.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the LoggerManager.
        
        Args:
            config: Configuration instance. If None, logging will not be configured.
        """
        self.config = config
        self._is_configured = False
        self.root_logger = None
        
        if config is not None:
            self.setup_logging()
    
    def setup_logging(self, config: Optional[Config] = None) -> None:
        """
        Initialize logging configuration based on loaded config.
        
        Args:
            config: Configuration instance with logging settings. 
                   If None, uses the config passed to constructor.
        """
        if config is not None:
            self.config = config
        
        if self.config is None:
            raise ValueError("Configuration is required to setup logging")

        try:
            log_config = self.config.get_logging_config()
            
            # Configure root logger
            self.root_logger = logging.getLogger()
            self.root_logger.setLevel(getattr(logging, log_config.level))
            
            # Clear existing handlers
            for handler in self.root_logger.handlers[:]:
                self.root_logger.removeHandler(handler)
            
            # Validate and create formatter
            try:
                formatter = logging.Formatter(log_config.format)
            except ValueError as e:
                # Fallback to a safe default format if the configured format is invalid
                print(f"Warning: Invalid log format '{log_config.format}'. Using default format. Error: {e}")
                formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s - %(message)s")
            
            # Add console handler if enabled
            if log_config.console_output:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(getattr(logging, log_config.level))
                console_handler.setFormatter(formatter)
                self.root_logger.addHandler(console_handler)
            
            # Add file handler if enabled
            if log_config.file_output:
                log_file_path = Path(log_config.log_file)
                log_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(log_file_path)
                file_handler.setLevel(getattr(logging, log_config.level))
                file_handler.setFormatter(formatter)
                self.root_logger.addHandler(file_handler)
            
            self._is_configured = True
            
            # Now it's safe to log
            self.root_logger.info("Logging system initialized successfully")
            
        except Exception as e:
            # Fallback to basic logging if configuration fails
            print(f"Error setting up logging: {e}")
            self._setup_basic_logging()
    
    def _setup_basic_logging(self):
        """Setup basic logging as fallback when configuration fails."""
        try:
            basic_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s - %(message)s")
            
            # Configure root logger with basic settings
            self.root_logger = logging.getLogger()
            self.root_logger.setLevel(logging.INFO)
            
            # Clear existing handlers
            for handler in self.root_logger.handlers[:]:
                self.root_logger.removeHandler(handler)
            
            # Add basic console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(basic_formatter)
            self.root_logger.addHandler(console_handler)
            
            self._is_configured = True
            print("Basic logging system initialized as fallback")
            
        except Exception as e:
            print(f"Failed to setup even basic logging: {e}")
            self._is_configured = False
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        Get a logger instance with the specified name.
        
        Args:
            name: Logger name. If None, returns the logger for the calling module.
            
        Returns:
            Logger instance configured according to the application settings.
        """
        if name is None:
            # Get the name of the calling module
            frame = inspect.currentframe()
            try:
                # Go up one frame to get the caller's module
                caller_frame = frame.f_back
                name = caller_frame.f_globals.get('__name__', __name__)
            finally:
                # Always clean up the frame reference
                del frame
        
        return logging.getLogger(name)
    
    def log_config_summary(self) -> None:
        """
        Log a summary of the current configuration.
        """
        if not self._is_configured or self.root_logger is None:
            print("Logging system not configured. Cannot log configuration summary.")
            return
            
        try:
            self.root_logger.info("Configuration summary:")
            self.root_logger.info(f"  - Log level: {self.config.get_logging_config().level}")
            self.root_logger.info(f"  - Console output: {self.config.get_logging_config().console_output}")
            self.root_logger.info(f"  - File output: {self.config.get_logging_config().file_output}")
            self.root_logger.info(f"  - Database host: {self.config.get_database_config().host}")
        except Exception as e:
            print(f"Error logging configuration summary: {e}")
    
    def log_app_startup(self) -> None:
        """
        Log application startup information.
        """
        if not self._is_configured or self.root_logger is None:
            print("Logging system not configured. Cannot log startup information.")
            return
            
        try:
            app_config = self.config.get_app_config()
            self.root_logger.info(f"Starting {app_config.name} v{app_config.version}")
        except Exception as e:
            print(f"Error logging startup information: {e}")
    

# Global logger manager instance
_logger_manager: Optional[LoggerManager] = None

def get_logger_manager(config: Optional[Config] = None) -> LoggerManager:
    """
    Get the global logger manager instance.
    
    Args:
        config: Configuration instance. If provided and no manager exists, creates a new one.
        
    Returns:
        LoggerManager instance.
    """
    global _logger_manager
    
    if _logger_manager is None and config is not None:
        _logger_manager = LoggerManager(config)
    elif _logger_manager is None:
        raise RuntimeError("LoggerManager not initialized. Call setup_logging() first.")
    
    return _logger_manager


def setup_logging(config: Config) -> LoggerManager:
    """
    Setup logging and return the logger manager.
    
    Args:
        config: Configuration instance.
        
    Returns:
        LoggerManager instance.
    """
    global _logger_manager
    _logger_manager = LoggerManager(config)
    return _logger_manager


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name. If None, returns the logger for the calling module.
        
    Returns:
        Logger instance configured according to the application settings.
    """
    return get_logger_manager().get_logger(name)
