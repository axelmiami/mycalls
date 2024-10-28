import os
from pydub import AudioSegment
import logging
from config_manager import ConfigManager

# Setting up logging
logger = logging.getLogger(__name__)
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

def _create_directories_if_not_exist(mp3_path):
    """
    Creates all non-existent directories for a given file.

    :param mp3_path: Path to the file.
    """
    # Get the path to the directory
    directory = os.path.dirname(mp3_path)

    # Create directories if they don't exist
    os.makedirs(directory, exist_ok=True)
    logger.debug(f"Ensured directories exist: {directory}")

def _ensure_mp3_dir_exists(mp3_dir):
    """
    Checks the existence of a directory for storing MP3 files and creates it if necessary.
    """
    try:
        # Check if directory exists
        if not os.path.exists(mp3_dir):
            # Create a directory and all necessary subdirectories
            os.makedirs(mp3_dir)
            logger.debug(f"Directory for MP3 files created: {mp3_dir}")
        else:
            logger.debug(f"The directory for MP3 files already exists: {mp3_dir}")
    except Exception as e:
        logger.error(f"Error creating directory for MP3 files: {e}")

class AudioFileManager:
    """
    Class for working with audio files.
    """

    def __init__(self):
        config = ConfigManager()
        self.mp3_dir = config.get_records()['mp3_dir']
        _ensure_mp3_dir_exists(self.mp3_dir)

    def convert_wav_to_mp3(self, wav_path):
        """
        Converts an audio file from WAV format to MP3 format.
        :param wav_path: Path to the source WAV file.
        :return: Path to the converted MP3 file, or None on failure.
        """
        try:
            # Checking the existence of the original WAV file
            if not os.path.exists(wav_path):
                logger.error(f"WAV file not found: {wav_path}")
                return None

            # Forming the name and path for the MP3 file
            wav_filename = os.path.basename(wav_path)
            mp3_filename = os.path.splitext(wav_filename)[0] + '.mp3'

            # Break the original path into parts
            parts = wav_path.split(os.sep)

            # Extract parts of the path for year, month, and day
            year, month, day = parts[-4], parts[-3], parts[-2]
            mp3_path = os.path.join(self.mp3_dir, year, month, day, mp3_filename)
            _create_directories_if_not_exist(mp3_path)

            # File conversion
            sound = AudioSegment.from_wav(wav_path)
            sound.export(mp3_path, format="mp3")
            logger.debug(f"File successfully converted from WAV to MP3: {mp3_path}")

            # Deleting the original WAV file
            # os.remove(wav_path)
            # logger.debug(f"WAV source file deleted: {wav_path}")

            return mp3_path
        except Exception as e:
            logger.error(f"Error converting file: {e}")
            return None

    def find_file(self, file_path):
        """
        Checks the existence of a file at the specified path.
        :param file_path: Path to the file.
        :return: True if the file exists, otherwise False.
        """
        if os.path.exists(file_path):
            logger.debug(f"File found: {file_path}")
            return True
        else:
            logger.debug(f"File not found: {file_path}")
            return False

    def delete_file(self, file_path):
        """
        Deletes a file at the specified path.
        :param file_path: Path to the file to be deleted.
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"File deleted: {file_path}")
            else:
                logger.error(f"File to delete not found: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
        except Exception as e:
            logger.error(f"Error deleting file: {e}")

