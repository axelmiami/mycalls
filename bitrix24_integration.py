import os
import requests
import logging
from config_manager import ConfigManager
from audio_file_manager import AudioFileManager

logger = logging.getLogger(__name__)


def _check_entity_in_list(entity_list, entityTypeId, entityId):
    for entity in entity_list:
        if entity['entityTypeId'] == entityTypeId and entity['entityId'] == entityId:
            logger.debug(
                f"Found presence of {entityTypeId} and {entityId} in {entity} dictionary")
            return True
        logger.debug(
            f"Not found presence of {entityTypeId} and {entityId} in {entity} dictionary")
    return False


class Bitrix24:
    """
    Class for integration with Bitrix24 API.
    """

    config = ConfigManager()
    webhook_url = config.get_bitrix24()["webhook_url"]
    entity_types = config.get_bitrix24_entity_types()

    def __init__(self):
        """
        Initializing a class with the Bitrix24 webhook URL and a list of entity types to search.
        :param webhook_url: Bitrix24 webhook URL.
        :param entity_types: List of entity types to search for.
        """
        # Loading settings from config.ini
        # self.config = ConfigManager()

    @classmethod
    def _find_id_by_value_in_list(cls, value_to_find, this_list):
        for this_id, value in this_list.items():
            if value == value_to_find:
                return this_id
        return None

    @classmethod
    def _make_request(cls, method, endpoint, params=None, data=None, file_path=None):
        """
        Helper function for making requests to the Bitrix24 API.
        :param method: HTTP request method (for example, 'GET' or 'POST').
        :param endpoint: The API endpoint to which the request will be made.
        :param params: Request parameters for GET requests.
        :param data: Data for POST requests.
        :param file_path: Full path to the file on the system
        :return: Response from the API.
        """
        url = f"{cls.webhook_url}/{endpoint}"

        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params)
            elif method.upper() == 'POST':
                if file_path:
                    with open(file_path, 'rb') as file:
                        files = {'file': file}
                        file_response = requests.post(url, data=data, files=files)

                    logger.debug(
                        f"File_response received from Bitrix24 for file: {file_response}")

                    file_result = file_response.json().get('result', [])

                    if file_result and file_result['uploadUrl']:
                        upload_url = file_result['uploadUrl']
                        with open(file_path, 'rb') as file:
                            files = {'file': file}
                            response = requests.post(upload_url, files=files)
                    else:
                        logger.error(
                            f"Response does not contain uploadUrl: {file_response}")

                else:
                    response = requests.post(url, data=data)
            else:
                logger.error(f"Unsupported request method: {method}")
                return None

            logger.debug(f"Sent to Bitrix24 method: {method}")
            logger.debug(f"Sent to Bitrix24 endpoint: {endpoint}")
            logger.debug(f"Sent to Bitrix24 params: {params}")
            logger.debug(f"Sent to Bitrix24 data: {data}")
            logger.debug(f"Sent to Bitrix24 files: {file_path}")

            logger.debug(f"Response received from Bitrix24: {response.json()}")

            # Throws an exception for HTTP errors
            response.raise_for_status()

            if response.status_code == 200:
                return response.json().get('result', [])
            else:
                logger.error(f"Error processing request {endpoint}, server response: {response.status_code}")
                return None

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"Response received: {response}")
            logger.error(f"HTTP error occurred: {http_err}")
        except Exception as err:
            logger.error(f"Response received: {response}")
            logger.error(f"Other error occurred: {err}")

        return None

    @classmethod
    def _update_entity(cls, entity_type, update_data):
        """
        Updates an entity in Bitrix24.

        :param entity_type: Entity type (e.g. 'lead', 'deal').
        :param entity_id: ID of the entity to update.
        :param update_data: Dictionary with data to update.
        """
        try:
            # Formation of endpoint based on entity type
            endpoint = f"crm.{entity_type}.update"

            logger.debug(
                f"Data for updating entity {entity_type} with ID {update_data['id']} using {endpoint} method: {update_data}")

            # Execute the request
            response = cls._make_request('POST', endpoint, data=update_data)

            if response:
                logger.debug(
                    f"Entity {entity_type} with ID {update_data['id']} was successfully updated: {update_data}")
                return response
            else:
                logger.error(f"Failed to update entity {entity_type} with ID {update_data['id']}")
                return None

        except Exception as e:
            logger.error(f"Error updating entity {entity_type} with ID {update_data['id']}: {e}")
            return None

    @classmethod
    def _check_caller_b24_entities(cls, caller_b24_entities, entity_key, field_key, value=None):
        """
        Checks for the presence of a given value or list of values in a specific entity field in Bitrix24.

        :param caller_b24_entities: List of entities received from Bitrix24.
        :param entity_key: The key of the entity to test (for example, 'lead' or 'deal').
        :param field_key: The key of the field in the entity to check (for example, 'UF_CRM_1701504940069').
        :param value: The value or list of values to be found in the specified field.
        :return: True if the value or one of the values is found, otherwise False.
        """
        try:
            for entity in caller_b24_entities.get(entity_key, []):
                logger.debug(f"Checking field_key={field_key}, value={value} for entity: {entity}")

                # Check if value is a list or a single value
                if isinstance(value, list):
                    if entity.get(field_key) in value:
                        logger.debug(f"Found value {entity.get(field_key)} in field {field_key}")
                        return True
                else:
                    if entity.get(field_key) == value:
                        logger.debug(f"Found {value} in field {field_key}")
                        return True

            logger.debug(f"Value {value} in field {field_key} not found")
            return False
        except Exception as e:
            logger.error(f"Error while checking Bitrix24 entities: {e}")
            return False

    @classmethod
    def _get_list_field_values(cls, field_id):
        """
        Retrieving an array of matching IDs and text values of a custom list type field.

        :param field_id: Field ID.
        :return: Matching dictionary {ID: Text_Value}.
        """
        try:
            # Get a list of all field values
            response = cls._make_request('GET', 'userfield.enumeration.get', params={'FIELD_ID': field_id})

            if response:
                # Create a dictionary of matching IDs and text values
                value_dict = {value['ID']: value['VALUE'] for value in response}
                logging.debug(f"Received a list of fields with ID {field_id}: {value_dict}")
                return value_dict
            else:
                logging.error("Error retrieving field values")
                return None
        except Exception as e:
            logging.error(f"Error when requesting Bitrix24 API: {e}")
            return None

    def find_contact_by_phone(self, phone_number):
        """
        Search for a contact in Bitrix24 by phone number.
        :param phone_number: Phone number to search.
        :return: Information about the contact or None if the contact is not found.
        """
        try:
            params = {
                'filter[PHONE]': phone_number,
                'select[]': ['ID', 'NAME', 'LAST_NAME', 'SECOND_NAME']
            }
            contacts = self._make_request("GET",
                                          "crm.contact.list",
                                          params=params)
            if not contacts:
                logger.info(f"No contacts found for {phone_number}")
                return None

            logger.info(f"Contacts found for {phone_number}: {contacts}")

            # Find the contact with the largest number of filled attributes
            best_contact = max(contacts, key=lambda contact: sum(
                1 for attr in ['NAME', 'LAST_NAME', 'SECOND_NAME'] if contact.get(attr)))

            logger.info(f"The contact with the most attributes is selected: {best_contact}")
            return best_contact

        except Exception as e:
            logger.error(f"Exception in search_contact: {e}")
            return None

    def get_entities_info(self, contact_id=None, phone_number=None):
        """
        Retrieving information about related entities for a contact or phone number.
        :param contact_id: Contact ID.
        :param phone_number: Phone number.
        :return: A dictionary with information about related entities.
        """
        removing_leads = ['CONVERTED', 'JUNK']
        logger.debug(f"Looking for entities for contact_id={contact_id} and phone_number={phone_number}")

        entities_info = {}
        filter_params = {"filter[ACTIVE]": 'Y',
                         'select[]': ['ID', 'TITLE', 'STATUS_ID', 'CATEGORY_ID', 'ORDER_TOPIC', 'UF_CRM_1701504940069'],
                         'start': 0,
                         'order[DATE_CREATE]': 'DESC'
                         }

        if contact_id is not None:
            filter_params['filter[CONTACT_ID]'] = contact_id
        if phone_number is not None:
            filter_params['filter[PHONE]'] = phone_number

        for entity_type, entity_data in self.entity_types.items():
            # We do not search for transactions by phone number if there is no contact ID
            if entity_type == 'deal' and contact_id is None:
                logger.warning(f"We are not searching for {entity_type} by phone number: {phone_number}")
            else:
                if entity_type == 'deal':
                    filter_params["filter[CLOSED]"] = "N"
                elif entity_type == 'lead':
                    filter_params['filter[!STATUS_ID]'] = removing_leads

                try:
                    entities = self._make_request("GET",
                                                  entity_data['request'],
                                                  params=filter_params)

                    if entities:
                        # We check and filter converted and low-quality leads
                        if entity_type == 'lead':
                            entities = [entity for entity in entities if entity['STATUS_ID'] not in removing_leads]

                        if entities and len(entities) > 0:
                            entities_info[entity_type] = entities
                            logger.debug(f"Found entities of type {entity_data['name']}: {entities}")
                        else:
                            logger.warning(f"Entities of type {entity_data['name']} not found")
                    else:
                        logger.debug(f"Tap entities {entity_data['name']} not found")
                except Exception as e:
                    logger.error(f"Error in get_entities_info for {entity_data['name']}: {e}")

        return entities_info

    @classmethod
    def b24call_registration(cls, call_info):
        """
        Registers a call to Bitrix24 on behalf of a service user.

        :param call_info: Current instance of the CallInfo class with all data.
        """
        call_type_mapping = {
            'outbound': 1,
            'inbound': 2,
            'inbound_with_forwarding': 3,
            'callback': 3
        }
        call_name_mapping = {
            'outbound': 'Outbound call',
            'inbound': 'Incoming call',
            'inbound_with_forwarding': 'Inbound call with forwarding',
            'callback': 'Callback'
        }
        call_type = call_type_mapping.get(call_info.call_type)
        call_type_name = call_name_mapping.get(call_info.call_type)

        # Checking if the call type is correct
        if call_type is None:
            logger.error(f"Unknown call type: {call_info.call_type}")
            return

        # Get the service user ID in Bitrix24 from config.ini
        call_admin_id = cls.config.get_bitrix24()['call_admin_id']

        # Formation of a request to the API to initiate a call
        endpoint = 'telephony.externalcall.register'
        data = {
            'USER_ID': call_admin_id,
            'PHONE_NUMBER': call_info.caller_id_num,
            'TYPE': call_type,
            'CRM_CREATE': 1,
            'SHOW': 0,
            'LINE_NUMBER': call_info.exten
        }

        # We get the correspondence between the ID and Name of the list of the custom property Leads, if there is one
        lead_uf_list_id = cls.config.get_bitrix24()["lead_uf_list_id"]
        logger.debug(f"Value of lead_uf_list_id in Bitrix24: {lead_uf_list_id}")

        # Execute the request
        call_window = cls._make_request('POST', endpoint, data=data)

        if call_window and call_window['CALL_ID'] != '':
            registered_call = {
                'USER_ID': call_admin_id
            }
            for name, data in call_window.items():
                registered_call[name] = data

            logger.debug(
                f"The call is registered in Bitrix24: {registered_call}")

            list_field_values = cls.config.get_bitrix24_lead_target_ids()
            logger.debug(f"Possible directions of Leads in Bitrix24 list_field_values: {list_field_values}")

            list_field_value = call_info.queue_name
            logger.debug(f"List_field_value: {list_field_value}")

            list_field_id = cls._find_id_by_value_in_list(list_field_value, list_field_values)
            logger.debug(f"Value of list_field_id: {list_field_id}")

            logger.debug(f"Value of call_window['CRM_CREATED_LEAD']: {call_window['CRM_CREATED_LEAD']}")
            if call_window['CRM_CREATED_ENTITIES'] is not None:
                logger.debug(
                    f"Value of call_window['CRM_CREATED_ENTITIES'][0]['ENTITY_ID']: {call_window['CRM_CREATED_ENTITIES']}")
            else:
                logger.debug(
                    f"Value call_window['CRM_CREATED_ENTITIES'][0]['ENTITY_ID']: None")

            if call_window['CRM_CREATED_LEAD'] is not None \
                    and \
                    call_window['CRM_CREATED_ENTITIES'] is not None \
                    and \
                    call_window['CRM_CREATED_ENTITIES'][0] is not None \
                    and \
                    call_window['CRM_CREATED_ENTITIES'][0]['ENTITY_ID'] is not None \
                    and \
                    int(call_window['CRM_CREATED_LEAD']) == int(call_window['CRM_CREATED_ENTITIES'][0]['ENTITY_ID']):
                entity_type = call_window['CRM_CREATED_ENTITIES'][0]['ENTITY_TYPE']
                logger.debug(f"Entity_type value: {entity_type}")

                entity_id = int(call_window['CRM_CREATED_ENTITIES'][0]['ENTITY_ID'])
                logger.debug(f"Entity_id value: {entity_id}")

                logger.debug(
                    f"An entity {entity_type} with ID={entity_id} was created in Bitrix24")

                if entity_type.lower() == 'lead':
                    cls._change_lead_title(entity_id, call_info, list_field_id)

            else:
                logger.debug(
                    f"Start checking call entities in Bitrix24: {registered_call}")

                # I get the ratio Queue number - category ID in Bitrix24
                deal_uf_list_id = cls.config.get_bitrix24()["deal_uf_list_id"]
                logger.debug(f"Value of deal_uf_list_id in Bitrix24: {deal_uf_list_id}")

                b24_deal_categories = cls.config.get_queue_b24_deal_categories()
                logger.debug(f"The value of b24_deal_categories in Bitrix24: {b24_deal_categories}")

                logger.debug(
                    f"We check the entities existing in Bitrix24 for compliance with the direction {call_info.queue_name}: {call_info.caller_b24_entities}")

                if cls._check_caller_b24_entities(call_info.caller_b24_entities, 'lead', lead_uf_list_id,
                                                  list_field_id) is False \
                        and \
                        cls._check_caller_b24_entities(call_info.caller_b24_entities, 'deal', deal_uf_list_id,
                                                       b24_deal_categories[call_info.queue]) is False:

                    logger.debug(
                        f"In Bitrix24 there are no entities with the direction: {call_info.queue_name}")

                    # Preparing data for a new Lead
                    lead_data = {
                        'TITLE': call_info.queue_name + ' - ' + call_info.caller_b24_contact_fullname + ' - ' + call_type_name,
                        'PHONE': call_info.caller_id_num,
                        lead_uf_list_id: list_field_id,
                        'SOURCE_ID': 'CALL',
                        'SOURCE_DESCRIPTION': call_type_name + ' to number ' + call_info.exten
                    }
                    if call_info.caller_b24_contact_fullname is not None and call_info.caller_b24_contact_fullname != call_info.caller_id_num:
                        lead_data['CONTACT_ID'] = call_info.caller_b24_contact_id

                    new_lead_id = cls._create_lead(lead_data)

                    if new_lead_id is not None:
                        logger.debug(
                            f"A Lead has been created in Bitrix24 with ID: {new_lead_id}")
                        cls._change_lead_title(new_lead_id, call_info, list_field_id)
                        call_info.update_call_info('b24_new_lead_id', new_lead_id)
                    else:
                        logger.error(
                            f"Error creating Lead: {new_lead_id}")

                else:
                    logger.debug(
                        f"Entities with direction were found in Bitrix24 {call_info.queue_name}")

        else:
            registered_call = {'ERROR': True, "CALL_WINDOW": call_window}
            logger.debug(
                f"Error registering a call in Bitrix24: {registered_call}")

        logger.debug(f"Current registered_call: {str(registered_call)}")

        call_info.update_call_info("b24_call_id", registered_call)

        logger.debug(f"Current call_info instance: {str(call_info)}")

    @classmethod
    def _change_lead_title(cls, lead_id, call_info, list_field_id):
        old_title = ''
        lead_uf_list_id = cls.config.get_bitrix24()['lead_uf_list_id']

        try:
            response = cls._make_request('GET', 'crm.lead.get', params={'id': lead_id})
            if response:
                old_title = response['TITLE']
        except Exception as e:
            logger.error(
                f"Data from the Lead entity with ID={lead_id} was not received from Bitrix24: {e}")

        # Check whether there is a Lead in Bitrix24 and in what direction
        if not call_info.caller_b24_entities:
            # Formation of data for the request
            update_data = {
                'id': lead_id,
                'fields[TITLE]': call_info.queue_name + ' - ' + old_title,
                f"fields[{lead_uf_list_id}]": list_field_id
            }

            entity_update = cls._update_entity('lead', update_data)

            logger.debug(
                f"Lead entity with ID={lead_id} updated {entity_update}")

    @classmethod
    def _create_lead(cls, lead_data):
        """
        Creates a new Lead in Bitrix24.

        :param lead_data: Dictionary with data for creating a lead.
        :return: ID of the created lead or None in case of error.
        """
        try:
            logging.debug(
                f"Start creating a Lead with lead_data: {lead_data}")

            # Check if the required data is present in lead_data
            required_fields = [
                'TITLE',
                'PHONE',
                'SOURCE_ID',
                'SOURCE_DESCRIPTION'
            ]

            logging.debug(
                f"Check for the presence of {required_fields} in {lead_data}")

            if not all(key in lead_data for key in required_fields):
                logging.warning("The required data to create a lead is missing.")
                return None

            # Formation of data for the request
            post_data = {
                'fields[STATUS_ID]': 'NEW',
            }

            for key, data in lead_data.items():
                if key == 'PHONE' and data:
                    post_data[f"fields[{key}][][VALUE]"] = data
                    post_data[f"fields[{key}][][VALUE_TYPE]"] = 'MOBILE'
                elif data:
                    post_data[f"fields[{key}]"] = data

            # Call a helper function to complete the request
            response = cls._make_request('POST', 'crm.lead.add', data=post_data)

            logging.debug(
                f"Response received when creating a Lead: {response}")

            # Checking the response from the API
            if response:
                lead_id = response
                logging.debug(f"A new lead has been created with ID {lead_id}.")
                return lead_id
            else:
                logging.error("Error creating lead: Failed to get response from API.")
                return None

        except Exception as e:
            logging.error(f"Error when creating a lead: {e}")
            return None

    @classmethod
    def b24call_window_open(cls, call_info, internal_numbers):
        """
        Opens a call window for available employees in Bitrix24.

        :param call_info: Current instance of the CallInfo class with all data.
        :param internal_numbers: array of internal numbers to which the call is made.
        """
        logger.debug(f"Internal numbers internal_numbers: {internal_numbers}")

        if call_info.internal_b24ids is None:
            internal_b24ids = {}
        else:
            internal_b24ids = call_info.internal_b24ids

        for internal_number in internal_numbers:
            # Map the text representation of the call type to the numeric code
            if len(internal_b24ids) > 0 and internal_number in internal_b24ids:
                user_id = internal_b24ids[internal_number]['USER_ID']
            else:
                user_id = cls._get_user_id_by_internal_number(internal_number)
                if user_id:
                    internal_b24ids[internal_number] = {'USER_ID': user_id}
                else:
                    logger.debug(f"User with internal number {internal_number} not found")

            if user_id:
                logger.debug(f"User ID: {user_id}")

                # Formation of a request to the API to initiate a call
                endpoint = 'telephony.externalcall.show'
                data = {
                    'CALL_ID': call_info.b24_call_id['CALL_ID'],
                    'USER_ID': user_id
                }

                # Execute the request
                call_window = cls._make_request('POST', endpoint, data=data)

                if call_window:
                    logger.debug(
                        f"A call was initiated for a user with IDs {user_id} and call type {call_info.call_type}, window open: {call_window}")

                else:
                    logger.debug(
                        f"The call was not initialized for the user with IDs {user_id} and call type {call_info.call_type}, response from Bitrix24: {call_window}")

            else:
                logger.debug(f"User with internal number {internal_number} not found")

    @classmethod
    def b24call_window_close(cls, call_info, accepted_user_num=None):
        """
        Function for marking a call as accepted in Bitrix24 and hiding call windows for other users.

        :param call_info: An instance of the CallInfo class of the current call
        :param accepted_user_num: Number of the agent (user) who accepted the call.
        """
        logger.debug(
            f"We try to close windows b24call_window_close for everyone except the one who accepted accepted_user_num={accepted_user_num} with call_info: {call_info}")

        for internal_number, b24_data in call_info.internal_b24ids.items():
            if internal_number != accepted_user_num or accepted_user_num is None:
                data = {
                    'USER_ID': b24_data['USER_ID'],
                    'CALL_ID': call_info.b24_call_id['CALL_ID']
                }
                # Formation of a request to the API for an unanswered number
                endpoint = 'telephony.externalcall.hide'

                # Execute the request
                call_window = cls._make_request('POST', endpoint, data=data)

                logger.debug(
                    f"Call_window of the sent request for the user with ID {b24_data['USER_ID']}: {call_window}")

                if call_window:
                    logger.debug(f"Call status and call window changed for user {b24_data['USER_ID']}")
                else:
                    logger.warning(
                        f"The current call window was already closed or was not opened for user {b24_data['USER_ID']}")

    @classmethod
    def cancel_b24call(cls, call_info):
        """
        Ending a call to Bitrix24.

        :param call_info: An instance of the CallInfo class of the current call.
        """
        if call_info.accepted_by_agent is not None:
            user_id = call_info.internal_b24ids[call_info.accepted_by_agent]['USER_ID']
        else:
            user_id = cls.config.get_bitrix24()['call_admin_id']

        logger.debug(
            f"user_id of user: {user_id}")

        # Hiding call windows in Bitrix24
        cls.b24call_window_close(call_info)

        # Formation of a request to the API to close the call window
        endpoint = 'telephony.externalcall.finish'
        data = {
            'USER_ID': user_id,
            'CALL_ID': call_info.b24_call_id['CALL_ID'],
            'DURATION': call_info.answer_duration
        }

        logger.debug(
            f"Request to endpoint: {endpoint} with data: {data}")

        try:
            # Execute the request
            response = cls._make_request('POST', endpoint, data=data)

            logger.debug(
                f"Response for completing a call to Bitrix24 on behalf of the user {user_id}: {response}")

            if response:
                logger.debug(f"Call {call_info.b24_call_id['CALL_ID']} completed in Bitrix24")

                call_info.update_call_info('crm_activity_id', response['CRM_ACTIVITY_ID'])
            else:
                logger.warning(f"Call failed to complete call {call_info.b24_call_id['CALL_ID']}")

            # Attach the call to the necessary entities and remove from unnecessary ones
            cls._call_binding(call_info)
            audio_attached = cls._attach_call_record(call_info.b24_call_id["CALL_ID"], call_info.call_record_mp3)

            if audio_attached:
                update_data = {
                    'COMPLETED': 'Y'
                }
                cls._update_bindined_call(call_info.crm_activity_id, update_data)
                logger.debug(
                    f"Call to Bitrix24 has been transferred to Processed status - activity:{call_info.crm_activity_id}")
            else:
                logger.error(
                    f"The call to Bitrix24 was not transferred to the status Processed - activity: {call_info.crm_activity_id}")

        except Exception as e:
            logger.error(f"Error completing call {call_info.b24_call_id['CALL_ID']}: {e}")

    @classmethod
    def _attach_call_record(cls, call_id, mp3_file):
        """
        Attaches a call recording to a call to Bitrix24.

        :param call_id: Call ID in Bitrix24.
        :param mp3_file: Path to the call recording file in MP3 format.
        """
        logger.debug(
            f"We are trying to transfer the recording file to Bitrix24 and attach it to the call with ID: {call_id}, "
            f"file path: {mp3_file}")
        if (mp3_file
                is None or not os.path.exists(mp3_file)):
            logger.error(f"Call recording file not found or path not specified: {mp3_file}")
            return False
        try:
            # Check if MP3 file exists
            if not os.path.exists(mp3_file):
                logger.error(f"Call recording file not found: {mp3_file}")
                return False

            # Get file name from full path
            file_name = os.path.basename(mp3_file)

            # Formation of data for the request
            endpoint = 'telephony.externalCall.attachRecord'
            data = {
                'CALL_ID': call_id,
                'FILENAME': file_name
            }

            # Sending a request
            response = cls._make_request('POST', endpoint, data=data, file_path=mp3_file)

            if response:
                logger.debug(f"Call recording successfully attached: {mp3_file}")
                return True
            else:
                logger.error("Could not attach call recording")
                return False
        except Exception as e:
            logger.error(f"Error attaching call recording: {e}")
            return False

    @classmethod
    def _call_binding(cls, call_info):
        """
        Attaching a call to the necessary entities in Bitrix24.

        :param call_info: An instance of the CallInfo class containing information about the call.
        """
        bindings_entities = []
        binding_settings = cls.config.get_bitrix24_binding_call()
        bindings_entities_mapping = {
            'lead': 1,
            'deal': 2,
            'contact': 3,
            'company': 4,
            'invoice': 31,
            'quote': 7,
            'requisite': 8
        }

        # Retrieving existing call bindings to entities
        if call_info.crm_activity_id is not None:
            bindings_entities = cls._make_request('GET', 'crm.activity.binding.list',
                                                  params={'activityId': call_info.crm_activity_id})
            logger.debug(f"Retrieved existing call bindings: {bindings_entities}")

        # Handle binding settings for each entity type
        for entity_type, setting in binding_settings.items():
            entity_type_id = bindings_entities_mapping.get(entity_type)
            entities = {}

            if entity_type in call_info.caller_b24_entities:
                entities = call_info.caller_b24_entities[entity_type]
                # Adding a new lead to the list if it is created
                if entity_type == 'lead' and call_info.b24_new_lead_id is not None:
                    logger.debug(f"Checking for adding a new lead: {call_info.b24_new_lead_id}")
                    if not any(ent['ID'] == call_info.b24_new_lead_id for ent in entities):
                        entities.insert(0, {'ID': call_info.b24_new_lead_id,
                                            cls.config.get_bitrix24()['lead_uf_list_id']:
                                                cls.config.get_queue_b24_lead_target()[call_info.queue][0]})
                        logger.debug(f"New leads added to the list ID={call_info.b24_new_lead_id}")
                        logger.debug(f"Updated list: {entities}")

            elif entity_type == 'lead' and call_info.b24_new_lead_id is not None:
                entities = [
                    {'ID': call_info.b24_new_lead_id,
                     cls.config.get_bitrix24()['lead_uf_list_id']:
                         cls.config.get_queue_b24_lead_target()[call_info.queue][0]}
                ]
                logger.debug(f"Adding a new Lead with ID={call_info.b24_new_lead_id} created a list of Leads {entities}")

            else:
                logger.debug(f"No entities found in Bitrix24: {entity_type}")
                continue

            if entities and len(entities) > 0:
                # Process each entity in the list
                for item in entities:
                    endpoint = ''
                    data = {}
                    response = None

                    # Handle binding settings for each entity type
                    if setting == 'ALL':
                        logger.debug(f"Processing 'ALL' setting for entity {entity_type} with ID {item['ID']}")
                        if len(bindings_entities) > 0 and _check_entity_in_list(bindings_entities, entity_type_id,
                                                                                item['ID']):
                            logger.debug(f"Entity {entity_type} with ID {item['ID']} is already bound")
                            continue
                        endpoint = 'crm.activity.binding.add'
                        data = {
                            'activityId': call_info.crm_activity_id,
                            'entityTypeId': entity_type_id,
                            'entityId': item['ID']
                        }

                    elif setting == 'FILTERED':
                        logger.debug(f"Processing 'FILTERED' setting for entity {entity_type} with ID {item['ID']}")
                        uf_list_ids = []
                        uf_list_id = cls.config.get_bitrix24()[f"{entity_type}_uf_list_id"]
                        if entity_type == 'lead':
                            uf_list_ids = cls.config.get_queue_b24_lead_target()[call_info.queue]
                        elif entity_type == 'deal':
                            uf_list_ids = cls.config.get_queue_b24_deal_categories()[call_info.queue]

                        if item[uf_list_id] in uf_list_ids and _check_entity_in_list(bindings_entities, entity_type_id,
                                                                                     item['ID']):
                            logger.debug(
                                f"Entity {entity_type} with ID {item['ID']} is already bound and matches the filter")
                            continue
                        elif item[uf_list_id] in uf_list_ids:
                            endpoint = 'crm.activity.binding.add'
                            data = {
                                'activityId': call_info.crm_activity_id,
                                'entityTypeId': entity_type_id,
                                'entityId': item['ID']
                            }
                            logger.debug(
                                f"Add a call to entity {entity_type} with ID {item['ID']}")
                        else:
                            endpoint = 'crm.activity.binding.delete'
                            data = {
                                'activityId': call_info.crm_activity_id,
                                'entityTypeId': entity_type_id,
                                'entityId': item['ID']
                            }
                            logger.debug(
                                f"Delete a call from entity {entity_type} with ID {item['ID']}")

                    elif setting == 'NONE':
                        logger.debug(f"Processing 'NONE' setting for entity {entity_type} with ID {item['ID']}")
                        endpoint = 'crm.activity.binding.delete'
                        data = {
                            'activityId': call_info.crm_activity_id,
                            'entityTypeId': entity_type_id,
                            'entityId': item['ID']
                        }

                    # Execute the request to API
                    if endpoint != '' and len(data) > 0:
                        response = cls._make_request("POST", endpoint, data=data)
                        if response:
                            logger.debug(f"Call processed for entity {entity_type}={item['ID']}: {response}")
                        else:
                            logger.error(f"Error processing call for entity {entity_type}={item['ID']}: {response}")
                    else:
                        logger.debug(f"Call was not processed for entity {entity_type}={item['ID']}")

                else:
                    logger.warning(f"No entities for type: {entity_type}")

    @classmethod
    def _get_user_id_by_internal_number(cls, internal_number):
        """
        Gets the user ID in Bitrix24 by internal number.

        :param internal_number: User's internal number.
        :return: User ID or None if user not found.
        """
        try:
            # Formation of a request to the API to search for a user by internal number
            endpoint = 'user.get'
            params = {
                'filter[UF_PHONE_INNER]': internal_number
            }

            # Execute the request
            user_ids = cls._make_request('GET', endpoint, params=params)

            if user_ids and len(user_ids) > 0:
                # Return the ID of the first found user
                user_id = user_ids[0]['ID']
                logger.debug(f"Found user with ID {user_id} for internal number {internal_number}")
                return user_id
            else:
                logger.warning(f"User with internal number {internal_number} not found.")
                return None

        except Exception as e:
            logger.error(f"Error getting user ID from internal number {internal_number}: {e}")
            return None

    @classmethod
    def _make_call(cls, call_type, user_id, phone_number):
        """
        Initiates a call for a list of users in Bitrix24.

        :param call_type: Call type (1 - Incoming, 2 - Outgoing, 3 - Outgoing with redirection).
        :param user_id: User ID in Bitrix24
        :param phone_number: External phone number.
        """
        try:
            # Formation of a request to the API to initiate a call
            endpoint = 'telephony.externalcall.register'
            data = {
                'USER_ID': user_id,
                'PHONE_NUMBER': phone_number,
                'TYPE': call_type
            }

            # Execute the request
            call_window = cls._make_request('POST', endpoint, data=data)

            if call_window:
                logger.debug(
                    f"A call window is open for user {user_id} to number {phone_number}, call type: {call_type}")
            else:
                logger.warning(
                    f"Call window could not be opened for user {user_id} to number {phone_number}, call type: {call_type}")

            return call_window

        except Exception as e:
            logger.error(f"Error initiating a call for user {user_id}: {e}")
            return None

    @classmethod
    def _update_bindined_call(cls, crm_activity_id, update_data):
        endpoint = 'crm.activity.update'
        data = {
            'id': crm_activity_id,
        }
        for key, value in update_data.items():
            data[f'fields[{key}]'] = value

        call_window = cls._make_request('POST', endpoint, data=data)

        if call_window:
            logger.debug(
                f"Updated activity with ID {crm_activity_id} values {data} - response: {call_window}")
        else:
            logger.warning(
                f"Failed to update activity with ID {crm_activity_id} values {data} - response: {call_window}")

        return call_window
