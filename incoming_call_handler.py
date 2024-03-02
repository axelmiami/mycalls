import re
import logging
import pytz
import time
from config_manager import ConfigManager
from bitrix24_integration import Bitrix24
from call_info import CallInfo
from call_info import convert_to_array
from call_end_handler import CallEndHandler
from audio_file_manager import AudioFileManager
from datetime import datetime
from configobj import ConfigObj

logger = logging.getLogger(__name__)


class IncomingCallHandler:
    """
    Class for processing incoming calls via AMI and interacting with Bitrix24.
    """

    def __init__(self):
        """
        Initializing the incoming call handler.

        :param bitrix24: An instance of a class for working with Bitrix24.
        :param log_ami_events: Flag to enable detailed logging of AMI events.
        """

        # Create a configuration object
        self.config = ConfigManager()

        self.bitrix24 = Bitrix24()
        self.log_ami_events = self.config.get_logging().as_bool(
            'log_ami_events') if 'log_ami_events' in self.config.get_logging() else False
        self.call_infos = {}  # Dictionary to store CallInfo instances by Uniqueid

    def handle_event(self, event, manager):
        """
        Processing events from AMI.

        :param event: Event from AMI.
        :param manager: AMI manager instance.
        """
        # Log all event attributes if the corresponding option is enabled
        if self.log_ami_events:
            for attr in dir(event):
                if not attr.startswith("__") and not callable(getattr(event, attr)):
                    logger.debug(f"{attr}: {getattr(event, attr)}")

        uniqueid = event.headers.get('Uniqueid', 'Unknown')
        linkedid = event.headers.get('Linkedid', 'Unknown')
        event_name = event.name

        # Check whether processing of this event is enabled in the configuration
        if self.config.get_event_handling().get(event_name) != 'true':
            # If event processing is not enabled, skip it
            return

        uniqueid = event.headers.get('Uniqueid', 'Unknown')
        linkedid = event.headers.get('Linkedid', 'Unknown')
        event_name = event.name

        try:
            if linkedid in self.call_infos:
                # Take the CallInfo instance if it already exists
                call_info = self.call_infos[linkedid]
            else:
                call_info = None

            # Processing a new channel event (incoming call)
            if event.name == 'Newchannel':
                exten = event.headers.get('Exten', 'Unknown')
                logger.info(f"New {event.name} arrived with Uniqueid={uniqueid}")
                allowed_extens = self.config.get_allowed_extens()  # Load allowed values from a configuration file
                logger.info(
                    f"Checking the source {exten} among those available in the configuration file {allowed_extens}")
                if exten in allowed_extens:
                    # Check if there is already a CallInfo instance for this Uniqueid
                    if uniqueid not in self.call_infos:
                        # Create a new CallInfo instance if it doesn't exist
                        logger.debug(f"Creating a new CallInfo instance for Uniqueid: {uniqueid}")

                        # Create a CallInfo object for a call with a unique identifier
                        self.call_infos[uniqueid] = CallInfo(uniqueid)

                    call_info = self.call_infos[uniqueid]

                    self.handle_new_channel(event, manager, call_info)
                else:
                    logger.info(f"Call with source {exten} is not processed")

            elif call_info is not None and event_name == 'TimeRule':
                self.handle_time_rule_event(event, call_info)
            elif call_info is not None and event_name == 'TimeGroup':
                self.handle_time_group_event(event, call_info)
            elif call_info is not None and event_name == 'IVRchoose':
                self.handle_ivr_choose_event(event, call_info)
            elif call_info is not None and event_name == 'QueueCallerJoin':
                self.handle_queue_event(event, call_info)
            elif call_info is not None and event_name == 'VarSet':
                self.handle_varset_event(event, call_info)
            elif call_info is not None and event_name == 'AgentConnect':
                self.handle_agent_connect(event, call_info)
            elif call_info is not None and event_name == 'AgentComplete':
                self.handle_agent_complete(event, call_info)
            elif call_info is not None and event_name == 'DialBegin':
                self.handle_dial_begin_event(event, call_info)
            elif call_info is not None and event_name == 'DialEnd':
                self.handle_dial_end_event(event, call_info)
            elif call_info is not None and event_name == 'Hangup':
                self.handle_hangup_event(event, call_info)
        except Exception as e:
            logger.error(f"Error handling event: {e}")

    def handle_new_channel(self, event, manager, call_info):
        """
        Processing a new channel event (incoming call).

        :param event: New channel event from AMI.
        :param manager: AMI manager instance.
        :param call_info: A CallInfo object to track call information.
        """
        try:
            # Extract the necessary information about the call from the event
            caller_id_num = event.headers.get('CallerIDNum', 'Unknown')
            exten = event.headers.get('Exten', 'Unknown')
            uniqueid = event.headers.get('Uniqueid', 'Unknown')
            channel = event.headers.get('Channel', 'Unknown')

            caller_id_name = caller_id_num

            # Get the current time on the server (call start time)
            start_time = time.time()

            # Update information about the call in the CallInfo object
            call_info.update_call_info('call_type', "inbound")
            call_info.update_call_info('caller_id_num', caller_id_num)
            call_info.update_call_info('exten', exten)
            call_info.update_call_info('uniqueid', uniqueid)
            call_info.update_call_info('channel', channel)
            call_info.update_call_info('start_time', start_time)  # Save the start time of the call

            # Log information about the incoming call
            logger.info(f"New call from {caller_id_num} to number {exten}, Uniqueid: {uniqueid}, Channel: {channel}")

            # Search for a contact in Bitrix24 by phone number
            contact_info = self.bitrix24.find_contact_by_phone(caller_id_num)

            # Log information about the found contact
            logger.debug(f"Contact information (contact_info): {contact_info}")

            # Saving call information in a CallInfo object
            if contact_info:
                # Formatting CallerIDName with information about the contact and related entities
                caller_name = self.format_contact_fullname(contact_info)

                call_info.update_call_info('caller_b24_contact_id', contact_info.get('ID'))

                # Search for related entities by ID of the found contact
                entities_info = self.bitrix24.get_entities_info(contact_id=contact_info.get('ID'))

                # Log information about found related entities
                logger.debug(
                    f"Information about related entities (entities_info) for Contact with ID {contact_info.get('ID')}: {entities_info}")

                if entities_info:
                    call_info.update_call_info('caller_b24_entities', entities_info)
                    caller_id_name = self.format_caller_id_name(caller_name, entities_info)

                # Update CallerIDName in AMI
                self.update_caller_id_name(manager, uniqueid, channel, caller_id_name)
            else:
                call_info.update_call_info('caller_b24_contact_id', None)
                caller_name = caller_id_num

                # Search for related entities by phone number if the contact is not found
                entities_info = self.bitrix24.get_entities_info(phone_number=caller_id_num)

                # Log information about found related entities in the absence of contact
                logger.debug(
                    f"Information about related entities when there is no contact (entities_info): {entities_info}")

                if entities_info:
                    # Add an entities_info entry to the call_info object
                    call_info.update_call_info('caller_b24_entities', entities_info)
                    caller_id_name = self.format_caller_id_name(caller_name, entities_info)

                # Update CallerIDName in AMI
                self.update_caller_id_name(manager, uniqueid, channel, caller_id_name)

            call_info.update_call_info('caller_b24_contact_fullname', caller_name)

            # Log the final value of caller_b24_contact_fullname
            logger.debug(f"Final value caller_b24_contact_fullname (caller_name): {caller_name}")
            # Log the final value of CallerIDName
            logger.debug(f"Final value of CallerIDName (caller_id_name): {caller_id_name}")

            call_info.update_call_info('call_name', caller_id_name)
        except Exception as e:
            logger.error(f"Error handling new channel: {e}")

    def handle_agent_connect(self, event, call_info):
        """
        Handling the AgentConnect event in the Asterisk AMI.

        :param event: AMI event.
        :param call_info: An instance of a class for storing call information.
        """
        # Uniqueid compliance check
        if event.headers.get('Uniqueid') != call_info.uniqueid: # Assuming there is a uniqueid attribute
            logger.debug("Uniqueid does not match the current call.")
            return

        call_data = None

        try:

            # Retrieving data from an event
            call_data = {
                'Stetus': 'AgentConnect',
                'DestConnectedLineName': event.headers.get('DestConnectedLineName', 'Unknown'),
                'DestUniqueid': event.headers.get('DestUniqueid', 'Unknown'),
                'Queue': event.headers.get('Queue', 'Unknown'),
                'QueueName': self.config.get_queue_names().get(event.headers.get('Queue', 'Unknown'), 'Unknown'),
                'Interface': event.headers.get('Interface', 'Unknown'),
                'MemberName': event.headers.get('MemberName', 'Unknown'),
                'HoldTime': event.headers.get('HoldTime', 0),
                'RingTime': event.headers.get('RingTime', 0)
            }

        except Exception as e:
            logger.error(f"Error processing AgentConnect event: {e}")

        if call_data:
            # Extract agent number from Interface
            match = re.search(r'Local/(\d+)@from-queue/n', call_data['Interface'])
            if match:
                call_data['AgentNumber'] = match.group(1)
            else:
                call_data['AgentNumber'] = None

            logger.debug(f"Received call data: {call_data}")

            # Mark the window in Bitrix24 for the one who accepted it as answered and close it for the rest
            Bitrix24.b24call_window_close(call_info, call_data["AgentNumber"])

            # Saving data to call_info instance
            current_time = int(time.time())
            logger.debug(f"Call received time: {current_time}")

            call_info.update_call_info("call_statuses", {current_time: call_data})
            call_info.update_call_info("accepted_by_agent", call_data['AgentNumber'])
            call_info.update_call_info("answer_start_time", current_time)

            # Logging a full instance of call_info
            logger.debug(f"Updated call_info instance: {str(call_info)}")

        else:
            logger.error(f"Could not process call pickup call_info: {str(call_info)}")

    def handle_agent_complete(self, event, call_info):
        """
        Handling the AgentComplete event in the Asterisk AMI.

        :param event: AMI event.
        :param call_info: An instance of a class for storing call information.
        """
        try:
            # Uniqueid compliance check
            if event.headers.get('Uniqueid') != call_info.uniqueid:  # Assuming there is a uniqueid attribute
                logger.debug("Uniqueid does not match the current call.")
                return

            # Retrieving data from an event
            call_data = {
                'Status': 'AgentComplete',
                'Reason': event.headers.get('Reason', 'Unknown'),
                'Queue': event.headers.get('Queue', 'Unknown'),
                'QueueName': self.config.get_queue_names().get(event.headers.get('Queue', 'Unknown'), 'Unknown'),
                'Interface': event.headers.get('Interface', 'Unknown'),
                'MemberName': event.headers.get('MemberName', 'Unknown'),
                'HoldTime': event.headers.get('HoldTime', 0),
                'TalkTime': event.headers.get('TalkTime', 0)
            }

            # Extract agent number from Interface
            match = re.search(r'Local/(\d+)@from-queue/n', call_data['Interface'])
            if match:
                call_data['AgentNumber'] = match.group(1)
            else:
                call_data['AgentNumber'] = 'Unknown'

            # Saving data to call_info instance
            current_time = int(time.time())
            call_info.update_call_info("call_statuses", {current_time: call_data})

            call_info.call_end_reason = call_data['Reason']

        except Exception as e:
            logger.error(f"Error processing AgentComplete event: {e}")

    def get_queue_name(self, queue_number):
        """
        Getting the queue name from the configuration.

        :param queue_number: Queue number.
        :return: Queue name.
        """
        queue_names = self.config['QueueNames']
        return queue_names.get(queue_number, 'Unknown queue')

    def handle_dial_begin_event(self, event, call_info):
        """
        Processing the dialing start event (DialBegin).

        :param event: Event containing information about dialing.
        :param call_info: An instance of the CallInfo class for recording call information.
        """
        try:
            agent_info = {}
            # Check if the event is a dialing start event
            if event.headers.get('Event') == 'DialBegin':
                uniqueid = event.headers.get('Uniqueid')
                linkedid = event.headers.get('Linkedid')
                dest_caller_id_num = event.headers.get('DestCallerIDNum', None)
                dest_caller_name = event.headers.get('DestCallerIDName')
                dest_uniqueid = event.headers.get('DestUniqueid')
                dest_exten = event.headers.get('DestExten', None)
                current_time = int(time.time())

                # If Uniqueid matches Linkedid, the call is routed to an agent
                if uniqueid == linkedid and dest_exten:
                    # Record information about the agents who are calling available_agents
                    agent_info[current_time] = {
                        'AgentNumber': dest_exten,
                        "DateTime": current_time,
                        "DestCallerIDNum": dest_caller_id_num,
                        "DestCallerIDName": dest_caller_name,
                        "Uniqueid": uniqueid,
                        "Linkedid": linkedid,
                        "DestExten": dest_exten,
                        "DestUniqueid": dest_uniqueid
                    }
                    call_info.update_call_info("used_agents",
                                               {dest_exten: agent_info})
                elif dest_caller_id_num:
                    # Logging information about the direction of the call to the agent
                    logger.debug(f"Call sent to agent {dest_caller_id_num} ({dest_caller_name})")

                    # Open the Bitrix24 call window for the agents who are receiving the call
                    Bitrix24.b24call_window_open(call_info, [dest_caller_id_num])

                    # Record information about available agents used_agents
                    agent_info[current_time] = {
                        'AgentNumber': dest_caller_id_num,
                        "DateTime": current_time,
                        "DestCallerIDNum": dest_caller_id_num,
                        "DestCallerIDName": dest_caller_name,
                        "Uniqueid": uniqueid,
                        "Linkedid": linkedid,
                        "DestExten": dest_exten,
                        "DestUniqueid": dest_uniqueid
                    }
                    call_info.update_call_info("available_agents",
                                               {dest_caller_id_num: agent_info})

                    # Log information about available agents
                    logger.debug(f"Available agent: {dest_caller_id_num}, information: {agent_info}")
                else:
                    # Логирование информации о доступных агентах
                    logger.error(f"Номер агента для Uniqueid: {uniqueid} не определён!")

        except Exception as e:
            # Logging an error
            logger.error(f"Error in handle_dial_begin_event: {e}")

    def handle_dial_end_event(self, event, call_info):
        """
        Handling the call end event (DialEnd) in the AMI.

        :param event: Event containing information about the call.
        :param call_info: An instance of the CallInfo class for recording call information.
        """
        try:
            dest_caller_id_num = event.headers.get("DestCallerIDNum", None)
            dest_caller_name = event.headers.get("DestCallerIDName", None)
            dial_status = event.headers.get("DialStatus", None)
            current_time = int(time.time())
            dial_info = {}

            # Update the call status in the list of available agents
            if dest_caller_id_num != call_info.exten:
                dial_info[current_time] = {
                    'AgentNumber': dest_caller_id_num,
                    "DateTime": current_time,
                    "DestCallerIDNum": dest_caller_id_num,
                    "DestCallerIDName": dest_caller_name,
                    "STATUS": dial_status
                }
                call_info.update_call_info("available_agents",
                                           {dest_caller_id_num: dial_info})
            else:
                if dest_caller_id_num != call_info.exten:
                    logger.error(f'Agent {dest_caller_id_num} not found in available_agents')

        except Exception as e:
            logger.error(f'Error processing DialEnd event: {e}')

    def handle_time_rule_event(self, event, call_info):
        """
        Processing the receipt of the selected "Time Rule" TimeRule for a call

        :param event:
        :param call_info:
        :return:
        """
        # Process rule event by time
        time_rule = event.headers.get('TimeRule')
        call_info.update_call_info('time_rule', time_rule)

    def handle_time_group_event(self, event, call_info):
        """
        Processing of receiving the selected "Time Group" TimeGroup for a call

        :param event:
        :param call_info:
        :return:
        """
        # Process rule event by time
        time_group = event.headers.get('TimeGroup')
        call_info.update_call_info('time_group', time_group)

    def handle_ivr_choose_event(self, event, call_info):
        """
        Processing the receipt of the selected "Interactive Menu" IVRchoose for a call

        :param event:
        :param call_info:
        :return:
        """
        # Process rule event by time
        ivr_choose = event.headers.get('IVRchoose')
        call_info.update_call_info('interactive_menu', ivr_choose)

    def handle_queue_event(self, event, call_info):
        """
        Processing the event of a call entering a queue (QueueCallerJoin).

        :param event: An event containing information about the call and queue.
        :param call_info: An instance of the CallInfo class for recording call information.
        """
        try:
            # Get the queue number from the event
            queue_number = event.headers.get('Queue')

            # Check the availability of the queue number
            if not queue_number:
                logger.error("Error: Queue number is missing in QueueCallerJoin event")
                return

            # Get the human-readable name of the queue from config.ini
            queue_name = self.config.get_queue_names()[queue_number]

            # Logging queue number and name
            logger.debug(f"The call has entered the queue: number {queue_number}, name {queue_name}")

            call_info.update_call_info('queue', queue_number)
            call_info.update_call_info('queue_name', queue_name)

            # Register a call in Bitrix24
            Bitrix24.b24call_registration(call_info)

            logger.debug(f"Instance of call_info received after Bitrix24.b24call_registration: {str(call_info)}")

        except Exception as e:
            # Logging an error
            logger.error(f"Error processing QueueCallerJoin event: {e}")

    def handle_varset_event(self, event, call_info):
        """
        Processing the variable setting event (VarSet).

        :param event: An event containing information about the variable and its value.
        :param call_info: An instance of the CallInfo class for recording call information.
        """
        try:
            # Get the variable name and its value from the event
            variable_name = event.headers.get('Variable')
            variable_value = event.headers.get('Value')

            # Check that the correct MIXMONITOR_FILENAME variable is set
            if variable_name == 'MIXMONITOR_FILENAME':
                # Logging the received variable value
                logger.debug(f"MIXMONITOR_FILENAME value is set to: {variable_value}")

                # Update call recording information in the call_info instance
                call_info.update_call_info('call_record_wav', variable_value)

        except Exception as e:
            # Logging an error
            logger.error(f"Error processing VarSet event: {e}")

    def handle_hangup_event(self, event, call_info):
        """
        Handling the call completion event (Hangup) in the AMI.

        :param event: Event containing information about the call.
        :param call_info: An instance of the CallInfo class for recording call information.
        """
        try:
            # Checking whether the Uniqueid of the event matches the call ID
            event_uniqueid = event.headers.get('Uniqueid')
            if event_uniqueid != call_info.uniqueid:
                logger.debug('Event Uniqueid does not match the call ID in CallInfo')
                return

            # Fixing the current time and writing it to call_info.end_time
            current_time = int(time.time())
            logger.debug(f'Call end time: {current_time}')
            call_info.update_call_info('end_time', current_time)

            # Calculate the duration of the entire call and record it in call_info.duration
            if call_info.start_time:
                duration = int(current_time - call_info.start_time)
                call_info.update_call_info('duration', duration)
                logger.debug(f'Call duration: {call_info.duration} seconds')
            else:
                call_info.update_call_info('duration', 0)
                logger.error('Call start time is not set in CallInfo')

            # Calculate the duration of the answered call and record it in call_info.answer_duration
            if call_info.accepted_by_agent is not None and call_info.answer_start_time is not None:
                call_info.update_call_info('answer_end_time', current_time)
                answer_duration = int(current_time - call_info.answer_start_time)
                call_info.update_call_info('answer_duration', answer_duration)
                logger.debug(f'Duration of answered call: {call_info.answer_duration} seconds')
            else:
                call_info.update_call_info('answer_duration', 0)
                logger.debug(f'Call {event_uniqueid} was not answered')

            audio_manager = AudioFileManager()
            call_record_mp3 = audio_manager.convert_wav_to_mp3(call_info.call_record_wav)

            if call_record_mp3 is not None:
                logger.debug(f"Запись звонка с конвертирована в mp3 и находится по пути: {call_record_mp3}")
                call_info.update_call_info('call_record_mp3', call_record_mp3)

            # Ending a call to Bitrix24
            Bitrix24.cancel_b24call(call_info)

            # Record the reasons why the call ended
            cause = event.headers.get('Cause')
            call_info.update_call_info('cause', cause)
            cause_txt = event.headers.get('Cause-txt')
            call_info.update_call_info('cause_txt', cause_txt)
            logger.debug(f'Call end reason: {cause} - {cause_txt}')

            if CallEndHandler.finalize_call(call_info):
                unique_id = call_info.uniqueid
                # Removing a call_info instance from storage
                if unique_id in self.call_infos:
                    del call_info
                    del self.call_infos[unique_id]

        except Exception as e:
            logger.error(f'Error processing Hangup event: {e}')

    def get_queue_name_from_asterisk(self, queue_number):
        """
        Getting a human-readable queue name from Asterisk.

        :param queue_number: Queue number.
        :return: Human-readable name of the queue.
        """
        # There should be code here to query the queue name from Asterisk
        # This can be an HTTP API request or a database request
        # Example code:

        # If API is used
        # response = requests.get(f"http://asterisk.api/queues/{queue_number}")
        # if response.status_code == 200:
        # return response.json().get('queue_name')

        # If using direct database access
        # connection = get_database_connection() # Function for getting a connection to the database
        # cursor = connection.cursor()
        # cursor.execute("SELECT name FROM queues WHERE number = %s", (queue_number,))
        # result = cursor.fetchone()
        # if result:
        # return result[0]

        queue_real_name = self.config.get('QueueNames', {}).get(queue_number)
        if queue_real_name:
            return queue_real_name

        return queue_number

    def format_caller_id_name(self, contact_fullname=None, entities_info=None):
        """
        Formatting CallerIDName with information about the contact and related entities.

        :param contact_info: Contact information from Bitrix24.
        :param entities_info: Information about related entities (optional).
        :return: The formatted CallerIDName value.
        """
        caller_id_name = ""

        try:
            # If there is information about the contact, add it to CallerIDName
            if contact_fullname:
                caller_id_name = contact_fullname

            # If there is information about related entities, add it to CallerIDName
            if entities_info:
                formatted_entities_info = self.format_entities_info(entities_info)
                if formatted_entities_info:
                    caller_id_name += f" ({formatted_entities_info})"
        except Exception as e:
            # Log an error when formatting CallerIDName
            logger.error(f"Error formatting CallerIDName: {e}")

        # Log the final value of CallerIDName
        logger.debug(f"Final value of CallerIDName (format_caller_id_name->caller_id_name): {caller_id_name}")

        return caller_id_name

    def format_entities_info(self, entities_info):
        """
        Format information about related entities as a string.

        :param entities_info: Information about related entities.
        :return: A formatted string containing information about the entities.
        """
        formatted_info = []

        try:
            # For each entity type in the entity information
            for entity_type, entity_list in entities_info.items():
                # Get the number of entities of this type
                entity_count = len(entity_list)

                # If there is at least one entity of this type
                if entity_count > 0:
                    # Format a string indicating the type and quantity
                    entity_type_name = self.get_entity_type_name(entity_type, entity_count)
                    formatted_info.append(entity_type_name)

            # Concatenate formatted strings into one comma-separated line
            formatted_info_str = ", ".join(formatted_info)
        except Exception as e:
            # Log an error when formatting information about entities
            logger.error(f"Error formatting entities info: {e}")
            formatted_info_str = ""  # In case of error, set to an empty string

        # Log the final value of the formatted information about entities
        logger.debug(f"Formatted entity information: {formatted_info_str}")

        return formatted_info_str

    def get_entity_type_name(self, entity_type, entity_count):
        """
        Get the formatted name of the entity type and quantity.

        :param entity_type: The entity type (for example, 'deal', 'lead', 'invoice', 'quote').
        :param entity_count: The number of entities of this type.
        :return: A formatted string with the type name and quantity.
        """
        try:
            # Get mappings from the configuration file
            entity_type_names = self.config.get_entity_types()

            # Get the Russian name of the entity type from the configuration or use the original value
            entity_type_name = entity_type_names.get(entity_type, entity_type)

            formatted_name = f"{entity_type_name} - {entity_count}"
        except Exception as e:
            # Log an error when receiving mappings
            logger.error(f"Error getting entity type name: {e}")
            formatted_name = f"{entity_type} - {entity_count}"  # In case of error, use the original value

        return formatted_name

    def update_caller_id_name(self, manager, uniqueid, channel, caller_id_name):
        """
        Update CallerIDName for call to AMI.

        :param channel:
        :param manager: AMI manager instance.
        :param uniqueid: Unique call identifier.
        :param caller_id_name: New CallerIDName value.
        """
        try:
            # Form a command to update CallerIDName
            action = {
                'Action': 'Setvar',
                'ActionID': uniqueid,
                'Channel': channel,
                'Variable': 'CALLERID(name)',  # Specify the CallerIDName variable
                'Value': caller_id_name  # Set a new value for CallerIDName
            }

            # Send the command to the AMI
            response = manager.send_action(action)

            # Check the success of the command execution
            if isinstance(response.response, list) and any('Response: Success' in line for line in response.response):
                # Log successful CallerIDName update in your logger
                logger.info(f"CallerIDName updated for Uniqueid {uniqueid}: {caller_id_name}")
            else:
                # Log the error when updating CallerIDName in your logger
                logger.error(f"Failed to update CallerIDName for Uniqueid {uniqueid}")
        except Exception as e:
            # Log a general error when updating CallerIDName in your logger
            logger.error(f"General error while updating CallerIDName: {e}")

    def format_contact_fullname(self, contact_info):
        """
        Formatting the contact's full name.

        :param contact_info: Contact information from Bitrix24.
        :return: The contact's formatted full name.
        """
        full_name = f"{contact_info.get('NAME', '')} {contact_info.get('SECOND_NAME', '')} {contact_info.get('LAST_NAME', '')}"
        return full_name.strip()
