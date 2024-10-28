import os
import logging
from logging.handlers import RotatingFileHandler
from config_manager import ConfigManager

# Setting up logging
logger = logging.getLogger(__name__)
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))  # Path to the project root
logs_dir = os.path.join(project_root, 'logs')  # Directory for logs


class LevelFilter(logging.Filter):
    """
    Custom filter class to filter log records based on a specified logging level.
    """

    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno >= self.level


class LoggerConfig:
    """
    Class for setting up logging configuration.
    """

    def __init__(self):
        self.config_manager = ConfigManager()

    def setup_logging(self):
        """
        Sets up logging based on the configuration retrieved from ConfigManager.
        Creates necessary directories for logs if they do not exist.
        """
        logging_config = self.config_manager.get_logging()

        # Using the directory from the configuration
        log_dir = os.path.join(project_root, logging_config.get('dir', 'logs'))  # Directory for logs
        default_level = logging_config.get('level', 'ERROR').upper()
        default_file = logging_config.get('file', 'mycalls.log')
        default_file_path = os.path.join(log_dir, default_file)
        default_max_size = int(logging_config.get('max_size', 10 * 1024 * 1024))
        default_backup_count = int(logging_config.get('backup_count', 5))

        # Check and create directory if it does not exist
        os.makedirs(log_dir, exist_ok=True)

        # Setting up the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.getLevelName(default_level))
        root_handler = RotatingFileHandler(default_file_path, maxBytes=default_max_size,
                                           backupCount=default_backup_count)
        root_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        root_handler.setFormatter(root_formatter)
        root_logger.addHandler(root_handler)

        # Setting up additional loggers
        logging_sections = self.config_manager.get_logging_sections()
        for section_name, section in logging_sections.items():
            logger_name = section_name.split('_', 1)[1]
            section_logger = logging.getLogger(logger_name)

            level = section.get('level', default_level).upper()
            file = section.get('file', default_file)
            file_path = os.path.join(log_dir, file)  # Log file path for the section
            max_size = int(section.get('max_size', default_max_size))
            backup_count = int(section.get('backup_count', default_backup_count))

            # Check and create directory for section logs if it does not exist
            os.makedirs(log_dir, exist_ok=True)

            handler = RotatingFileHandler(file_path, maxBytes=max_size, backupCount=backup_count)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            section_logger.setLevel(logging.getLevelName(level))
            section_logger.addHandler(handler)

            # Add a filter to additional loggers
            filter = LevelFilter(logging.getLevelName(default_level))
            section_logger.addFilter(filter)

            # Logging information about the section logger settings
            logger.debug(
                f"Configured logger {logger_name} with file {file_path}, level {level}, maximum size {max_size} and number of rotation files {backup_count}")


# Debugging output to verify paths
if __name__ == "__main__":
    print(f"Script path: {script_path}")
    print(f"Project root: {project_root}")
    print(f"Logs directory: {logs_dir}")
