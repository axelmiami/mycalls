import logging

logger = logging.getLogger(__name__)


class CallInfo:
    def __init__(self, uniqueid):
        """
        Initialize an object to track call information.

        :param uniqueid: Unique call identifier.
        """
        self.uniqueid = uniqueid
        self.call_type = None
        self.call_name = None
        self.caller_id_num = None
        self.caller_b24_contact_id = None
        self.caller_b24_contact_fullname = None
        self.caller_b24_entities = {}
        self.b24_new_lead_id = None
        self.exten = None
        self.channel = None
        self.linked_id = []
        self.start_time = None
        self.answer_start_time = None
        self.time_group = None
        self.time_rule = None
        self.recording_started = None
        self.recording_path = None
        self.interactive_menu = []
        self.queue = None
        self.queue_name = None
        self.used_agents = {}
        self.available_agents = {}
        self.accepted_by_agent = None
        self.internal_b24ids = {}
        self.b24_call_id = {}
        self.end_time = None
        self.answer_end_time = None
        self.duration = None
        self.answer_duration = None
        self.call_statuses = {}
        self.call_end_reason = None
        self.cause = None
        self.cause_txt = None
        self.crm_activity_id = None
        self.call_record_wav = None
        self.call_record_mp3 = None

    def __str__(self):
        """
        Returns a string representation of a CallInfo object.
        """
        info_str = "CallInfo:\n"
        for key, value in self.__dict__.items():
            info_str += f" {key}: {value}\n"
        return info_str

    def update_call_info(self, key, value):
        """
        Update call information.

        :param key: Key (attribute name) to update.
        :param value: New value.
        """
        # Check if the attribute exists in the class instance
        if hasattr(self, key):
            current_value = getattr(self, key)

            # Logging current and new values
            logger.debug(f"Updating attribute '{key}' from '{current_value}' to '{value}'")

            # If the current value is None and the new value is an integer, update the value
            if current_value is None and isinstance(value, int):
                setattr(self, key, value)
                logger.debug(f"Attribute '{key}' updated with new integer value")
            # If the current value is a dictionary, update it recursively
            elif isinstance(current_value, dict):
                self._recursive_update(current_value, value)
                logger.debug(f"Attribute '{key}' updated as dictionary")
            # If the current value is a list, add the element to the end
            elif isinstance(current_value, list):
                current_value.append(value)
                logger.debug(f"Element added to attribute list '{key}'")
            # In other cases, just set a new value
            else:
                setattr(self, key, value)
                logger.debug(f"Attribute '{key}' updated with new value")
        else:
            # Print an error if the attribute does not exist
            logger.error(f"Error: attribute '{key}' does not exist in class CallInfo.")

    def _recursive_update(self, current_dict, new_dict):
        """
        Recursive dictionary update.

        :param current_dict: Current dictionary.
        :param new_dict: New dictionary with updates.
        """
        for key, value in new_dict.items():
            if key in current_dict and isinstance(current_dict[key], dict) and isinstance(value, dict):
                self._recursive_update(current_dict[key], value)
            else:
                current_dict[key] = value


def convert_to_array(call_info):
    array = []
    for attribute_name in dir(call_info):
        # Exclude special methods and attributes (starting and ending with __)
        if not attribute_name.startswith('__') and not attribute_name.endswith('__'):
            attribute_value = getattr(call_info, attribute_name)
            array.append([attribute_name, attribute_value])
    return array
