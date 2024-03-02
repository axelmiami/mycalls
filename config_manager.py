from configobj import ConfigObj
import logging
import os

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
logger = logging.getLogger(__name__)


def _parse_list(value):
    # Check if value is a string
    if isinstance(value, str):
        logger.debug(f"Parsing list from string value: {value}")
        # Remove quotes and separate values
        return [item.strip().strip("'") for item in value.split(',')]
    elif isinstance(value, list):
        logger.debug(f"Value is already a list: {value}")
        # If value is already a list, return it as is
        return value
    else:
        logger.error(f"Unsupported type for value: {type(value)}")
        return []


class ConfigManager:
    def __init__(self, config_path=script_dir + '/config.ini'):
        """
        Initializing the configuration manager.

        :param config_path: Path to the configuration file.
        """
        try:
            self.config = ConfigObj(config_path, encoding='utf-8')
            logger.debug("Configuration file loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
            raise

    def get_logging_sections(self):
        """
        Getting all sections starting with 'Logger_' in the configuration file.

        :return: A dictionary, where the keys are the names of the sections, and the values are the contents of the sections.
        """
        try:
            logging_sections = {section: self.config[section] for section in self.config if
                                section.startswith('Logger_')}
            logging.debug(f"Logging sections found: {logging_sections.keys()}")
            return logging_sections
        except Exception as e:
            logging.error(f"Error retrieving logging sections: {e}")
            return {}

    def get_ami(self):
        """
        Getting AMI settings.

        :return: Dictionary of AMI settings.
        """
        try:
            ami_config = self.config['AMI']
            # Data validation
            if not (ami_config.get('host') and ami_config.get('port').isdigit()):
                raise ValueError("Invalid AMI settings")
            return ami_config
        except Exception as e:
            logger.error(f"Error while retrieving AMI settings: {e}")
            return None

    def get_records(self):
        """
        Getting settings for Records.

        :return: Dictionary of event processing settings.
        """
        try:
            records = self.config['Records']
            return records
        except Exception as e:
            logger.error(f"Error while retrieving Records settings: {e}")
            return {}

    def get_allowed_extens(self):
        """
        Retrieving a list of valid Exten numbers from a configuration file.
        Returns a list of numbers if they are specified correctly in the configuration.
        In case of error, returns an empty list and logs the error.
        """
        try:
            # Get a list of numbers
            allowed_extens = self.config['Allowed_Extens']['extens']

            # Make sure this is a list
            if not isinstance(allowed_extens, list):
                allowed_extens = [allowed_extens]

            # Remove spaces around each number
            allowed_extens = [exten.strip() for exten in allowed_extens]

            # Logging received data at the debug level
            logger.debug(f"Received allowed Exten numbers: {allowed_extens}")
            return allowed_extens
        except Exception as e:
            # Logging an error at the error level
            logger.error(f"Error retrieving valid Exten numbers: {e}")
            return []  # Return an empty list in case of error

    def get_event_handling(self):
        """
        Getting event processing settings.

        :return: Dictionary of event processing settings.
        """
        try:
            event_handling = self.config['EventHandling']
            return event_handling
        except Exception as e:
            logger.error(f"Error while retrieving event processing settings: {e}")
            return {}

    def get_queue_names(self):
        """
        Retrieving queue names.

        :return: Dictionary of queue names.
        """
        try:
            queue_names = self.config['QueueNames']
            return queue_names
        except Exception as e:
            logger.error(f"Error while retrieving queue names: {e}")
            return {}

    def get_queue_b24_deal_categories(self):
        """
        Obtaining correspondence Queue - categories in Bitrix24.

        :return: Matching dictionary Queue - categories in Bitrix24.
        """
        try:
            # Getting values from the 'QueueB24DealCategories' section
            queue_b24_deal_categories = self.config['QueueB24DealCategories']
            logger.debug(f"Raw data from config: {queue_b24_deal_categories}")

            parsed_data = {key: _parse_list(value) for key, value in queue_b24_deal_categories.items()}
            logger.debug(f"Parsed data: {parsed_data}")

            return parsed_data
        except Exception as e:
            logger.error(f"Error when obtaining correspondence Queue - categories in Bitrix24: {e}")
            return {}

    def get_queue_b24_lead_target(self):
        """
        Obtaining correspondence Queue - Lead directions in Bitrix24.

        :return: Matching dictionary Queue - Lead direction in Bitrix24.
        """
        try:
            # Getting values from the 'QueueB24LeadTarget' section
            queue_b24_lead_target = self.config['QueueB24LeadTarget']
            logger.debug(f"Raw data from config: {queue_b24_lead_target}")

            parsed_data = {key: _parse_list(value) for key, value in queue_b24_lead_target.items()}
            logger.debug(f"Parsed data: {parsed_data}")

            return parsed_data
        except Exception as e:
            logger.error(f"Error when receiving correspondence Queue - Lead direction to Bitrix24: {e}")
            return {}

    def get_logging(self):
        """
        Getting logging settings.

        :return: Dictionary of logging settings.
        """
        try:
            logging_settings = self.config['Logging']
            return logging_settings
        except Exception as e:
            logger.error(f"Error while retrieving logging settings: {e}")
            return {}

    def get_logging_incoming_calls(self):
        """
        Getting logging settings.

        :return: Dictionary of logging settings.
        """
        try:
            logging_settings = self.config['Logging_Incoming_Calls']
            return logging_settings
        except Exception as e:
            logger.error(f"Error while retrieving Incoming call logging settings: {e}")
            return {}

    def get_logging_bitrix24(self):
        """
        Getting logging settings.

        :return: Dictionary of logging settings.
        """
        try:
            logging_settings = self.config['Logging_Bitrix24']
            return logging_settings
        except Exception as e:
            logger.error(f"Error when receiving Bitrix24 integration logging settings: {e}")
            return {}

    def get_bitrix24(self):
        """
        Receiving integration settings with Bitrix24.

        :return: Dictionary of Bitrix24 settings.
        """
        try:
            bitrix24_settings = self.config['Bitrix24']
            return bitrix24_settings
        except Exception as e:
            logger.error(f"Error while retrieving Bitrix24 settings: {e}")
            return {}

    def get_bitrix24_binding_call(self):
        """
        Receiving settings for linking a call to Bitrix24 entities.
        :return: Setting values by type.
        """
        try:
            bitrix24_binding_call = self.config['Bitrix24_Binding_Call']
            return bitrix24_binding_call
        except Exception as e:
            logger.error(f"Error while retrieving Bitrix24_Binding_Call settings: {e}")
            return {}

    def get_bitrix24_lead_target_ids(self):
        """
        Receiving integration settings with Bitrix24_lead_Target_IDs.

        :return: Bitrix24_lead_Target_IDs settings dictionary.
        """
        try:
            bitrix24_lead_target_ids_settings = self.config['Bitrix24_lead_Target_IDs']
            return bitrix24_lead_target_ids_settings
        except Exception as e:
            logger.error(f"Error while retrieving BiBitrix24_lead_Target_IDs settings: {e}")
            return {}

    def get_entity_types(self):
        """
        Retrieving entity type settings.

        :return: Dictionary of entity type settings.
        """
        try:
            entity_types = self.config['EntityTypes']
            return entity_types
        except Exception as e:
            logger.error(f"Error while retrieving entity type settings: {e}")
            return {}

    def get_bitrix24_entity_types(self):
        """
        Getting settings for Bitrix24 entity types.

        :return: Dictionary of Bitrix24 entity type settings.
        """
        try:
            bitrix24_entity_types = {}
            if 'Bitrix24EntityTypes' in self.config:
                for entity_name, entity_data in self.config['Bitrix24EntityTypes'].items():
                    bitrix24_entity_types[entity_name] = entity_data
            return bitrix24_entity_types
        except Exception as e:
            logger.error(f"Error while retrieving Bitrix24 entity type settings: {e}")
            return {}
