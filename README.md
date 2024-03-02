
# MyCalls for Asterisk & Bitrix24

## Description
This application interfaces with Asterisk Manager Interface (AMI) to handle incoming calls, manage call logs, and integrate with Bitrix24 CRM. It is designed to run as a daemon, continuously listening for events from AMI, handling incoming calls, and logging call information.

## Features
- Connection to Asterisk Manager Interface (AMI)
- Handling incoming calls
- Audio file management
- Integration with Bitrix24 CRM
- Logging and configuration management

## Dependencies
- Python 3
- asterisk.manager (Asterisk Manager Interface library for Python)
- daemon (For running the script as a daemon)
- logging (For logging purposes)

## Installation
1. Clone the repository to your local machine.
2. Install the required Python packages using `pip install -r requirements.txt` (You will need to create this file based on the dependencies listed above).
3. Configure the `config.ini` file based on the `config.ini.template` provided.
4. Adjust logging configurations in `logger_config.py` as needed.

## Configuration
The application requires configuration through a `config.ini` file. Use the provided `config.ini.template` as a base for your configuration. The configuration includes:
- AMI connection details (host, port, username, secret)
- Bitrix24 integration parameters (if used)

## Usage
To run the application, execute:
```
python main.py
```
This will start the application as a daemon.

## Contributing
Contributions are welcome. Please open an issue or submit a pull request for any bugs, features, or improvements.

## License
GNU AFFERO GENERAL PUBLIC LICENSE Version 3
