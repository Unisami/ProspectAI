"""Logging configuration for the job prospect automation system."""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, uses default location
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Default log file name with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = logs_dir / f"prospect_automation_{timestamp}.log"
    
    # Configure root logger
    logger = logging.getLogger("prospect_automation")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # File gets all messages
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name, typically __name__ from calling module
        
    Returns:
        Logger instance
    """
    if name is None:
        return logging.getLogger("prospect_automation")
    
    # Create child logger
    return logging.getLogger(f"prospect_automation.{name}")


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)


# Configure logging for external libraries
def configure_external_loggers():
    """Configure logging levels for external libraries to reduce noise."""
    # Reduce noise from HTTP libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Reduce noise from scraping libraries
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("crawl4ai").setLevel(logging.WARNING)
    
    # Reduce noise from API libraries
    logging.getLogger("notion_client").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)