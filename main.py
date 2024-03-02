import daemon
import daemon.pidfile
import logging
import asterisk.manager
from config_manager import ConfigManager
from incoming_call_handler import IncomingCallHandler
from logger_config import LoggerConfig
import time

# Load configuration from file
config = ConfigManager()


def run_daemon():
    """
    A function to run the main daemon logic.
    """

    # Initialization and configuration of logging
    logger_config = LoggerConfig()
    logger_config.setup_logging()

    # Getting a logger for main.py
    logger = logging.getLogger('main')

    # Параметры подключения к AMI
    config_ami = config.get_ami()
    host = config_ami['host']
    port = int(config_ami['port'])
    username = config_ami['username']
    secret = config_ami['secret']

    # Создание экземпляров классов для работы с AMI и Bitrix24
    manager = asterisk.manager.Manager()
    incoming_call_handler = IncomingCallHandler()

    try:
        manager.connect(host, port)
        logger.info("Connection to AMI established.")
        manager.login(username, secret)
        logger.info("AMI logged in.")

        manager.register_event('*', incoming_call_handler.handle_event)

        while True:
            time.sleep(1)
            manager.ping()

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        try:
            manager.logoff()
            logger.info("AMI Manager exited.")
        except Exception as e:
            logger.error(f"Error when exiting AMI Manager: {e}")


def main():
    """
    The main function for running a script as a daemon.
    """
    run_daemon()


if __name__ == '__main__':
    main()
