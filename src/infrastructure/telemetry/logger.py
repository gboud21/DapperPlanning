import logging
import os
from datetime import datetime
from typing import Optional
from src.utils.paths import get_logs_dir, get_audit_dir

class AppLogger:
    _instance = None
    _logger = None

    @classmethod
    def get_logger(cls):
        if cls._logger is None:
            cls.setup_logger()
        return cls._logger

    @classmethod
    def setup_logger(cls, log_level_str: str = "INFO"):
        """
        Configures the Python standard logging module.
        """
        log_dir = get_logs_dir()
        log_file = log_dir / "dapperplanning.log"

        # Create logger
        cls._logger = logging.getLogger("DapperPlanning")
        
        # Clear existing handlers if any (to avoid duplicates on re-setup)
        if cls._logger.hasHandlers():
            cls._logger.handlers.clear()

        # Set level
        level = getattr(logging, log_level_str.upper(), logging.INFO)
        cls._logger.setLevel(level)

        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(log_file)
        
        # Create formatters and add it to handlers
        # Format: timestamp, level, thread name, message
        format_str = '%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
        c_format = logging.Formatter(format_str)
        f_format = logging.Formatter(format_str)
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        # Add handlers to the logger
        cls._logger.addHandler(c_handler)
        cls._logger.addHandler(f_handler)
        
        cls._logger.info(f"Logger initialized at level {log_level_str}")

    @classmethod
    def update_log_level(cls, log_level_str: str):
        if cls._logger:
            level = getattr(logging, log_level_str.upper(), logging.INFO)
            cls._logger.setLevel(level)
            cls._logger.info(f"Log level updated to {log_level_str}")

def audit_payload(action: str, payload: dict):
    """
    Writes raw JSON payload to the audit/ directory.
    """
    audit_dir = get_audit_dir()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gitlab_{action}_{timestamp}.json"
    filepath = audit_dir / filename
    
    try:
        import json
        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=4)
        logging.getLogger("DapperPlanning").debug(f"Audit payload written to {filepath}")
    except Exception as e:
        logging.getLogger("DapperPlanning").error(f"Failed to write audit payload: {e}")

# Helper to get logger easily
logger = AppLogger.get_logger()
