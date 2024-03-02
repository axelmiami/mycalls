import os
import logging
from logging.handlers import RotatingFileHandler
from config_manager import ConfigManager

# Setting up logging
logger = logging.getLogger(__name__)
script_path = os.path.abspath(__file__)
logs_dir = os.path.dirname(script_path) + '/logs'


class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno >= self.level


class LoggerConfig:
    def __init__(self):
        self.config_manager = ConfigManager()

    def setup_logging(self):
        logging_config = self.config_manager.get_logging()
        log_dir = logging_config.get('dir', logs_dir)
        default_level = logging_config.get('level', 'ERROR').upper()
        default_file = logging_config.get('file', 'mycalls.log')
        default_file_path = os.path.join(log_dir, default_file)
        default_max_size = int(logging_config.get('max_size', 10 * 1024 * 1024))
        default_backup_count = int(logging_config.get('backup_count', 5))

        # Setting up the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.getLevelName(default_level))
        root_handler = RotatingFileHandler(default_file_path, maxBytes=default_max_size, backupCount=default_backup_count)
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
            file_path = os.path.join(log_dir, file)
            max_size = int(section.get('max_size', default_max_size))
            backup_count = int(section.get('backup_count', default_backup_count))

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
