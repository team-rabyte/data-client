import json
import time
import logging
import os
from socket import socket, AF_INET, SOCK_DGRAM, timeout
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommandHandler(FileSystemEventHandler):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.last_modified = 0
        self.cooldown = 0.1  # 100ms cooldown between sends
        self.last_sent_command = None
        
        # Enable receiving responses
        self.sock.settimeout(1.0)  # 1 second timeout for responses

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('commands.txt'):
            current_time = time.time()
            if current_time - self.last_modified < self.cooldown:
                return
            self.last_modified = current_time
            self.send_latest_command()

    def send_latest_command(self):
        try:
            if not os.path.exists('commands.txt') or os.path.getsize('commands.txt') == 0:
                return

            with open('commands.txt', 'r') as f:
                commands = json.load(f)

            if not commands:
                return

            # Get the latest command
            latest_command = commands[-1]
            
            if self.last_sent_command != latest_command:
                # Send the complete command including PID values
                command_to_send = {
                    "pid_values": {
                        "P": {
                            "roll": latest_command["roll"]["p"],
                            "pitch": latest_command["pitch"]["p"],
                            "throttle": latest_command["throttle"]["p"],
                            "yaw": latest_command["yaw"]["p"],
                        },
                        "I": {
                            "roll": latest_command["roll"]["i"],
                            "pitch": latest_command["pitch"]["i"],
                            "throttle": latest_command["throttle"]["i"],
                            "yaw": latest_command["yaw"]["i"],
                        },
                        "D": {
                            "roll": latest_command["roll"]["d"],
                            "pitch": latest_command["pitch"]["d"],
                            "throttle": latest_command["throttle"]["d"],
                            "yaw": latest_command["yaw"]["d"],
                        },
                    }
                }

                
                # Send the command
                command_bytes = json.dumps(command_to_send).encode()
                self.sock.sendto(command_bytes, (self.host, self.port))
                print(f"\nSent command to {self.host}:{self.port}:")
                print(json.dumps(command_to_send, indent=2))
                logger.info(f"Sent command: {command_to_send}")
                
                # Wait for confirmation
                try:
                    response, addr = self.sock.recvfrom(1024)
                    response_data = json.loads(response.decode())
                    logger.info(f"Received confirmation from {addr}: {response_data}")
                except timeout:
                    logger.warning("No confirmation received from server")
                
                self.last_sent_command = latest_command

        except Exception as e:
            logger.error(f"Error sending command: {e}")

def flush_to_file(data, use_json: bool = True):
    """Function from original main.py to handle data flushing"""
    global config, columns

    data = data.decode()

    if type(data) is not str:
        logging.error(
            "Provided data is not string type. type = {}".format(type(data)))
        return

    try:
        data = dict(json.loads(data))
        print("Received data:", data)
    except Exception as e:
        logging.error(
            "Error while loading string to json: {}\ndata={}".format(e, data))
        return

    if not use_json:
        write_cols = False
        if columns is None and os.path.isfile(config['path_to_save']):
            f = open(config['path_to_save'], 'r')
            line = f.readline()
            columns = line.split(',')
            logging.warning(
                "File already exists. Using columns found in the file: {}",
                columns)
            write_cols = True
        elif columns is None:
            columns = [c for c in data]
            write_cols = True

        if write_cols:
            with open(config['path_to_save'], 'a') as f:
                f.write(','.join(['timestamp'] + columns) + '\n')

        for key in data:
            if key not in columns:
                logging.warning("{} column doesn't exist".format(key))

        temp = []
        for c in columns:
            val = data.get(c, '')
            if val == '':
                logging.warning("{} not found in sent data".format(c))
            temp.append(val)
        temp = [time.time()] + temp
        temp = [str(x) for x in temp]

    with open(config['path_to_save'], 'a') as f:
        if use_json:
            f.write(json.dumps(data))
        else:
            f.write(','.join(temp) + '\n')

def main():
    global config, columns
    columns = None

    # Load configuration
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            print(config)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return

    # Create command handler
    command_handler = CommandHandler(config['host'], config['port'])

    # Set up file system observer
    observer = Observer()
    observer.schedule(command_handler, path='.', recursive=False)
    observer.start()

    logger.info(f"Started command sender. Watching for changes in commands.txt")
    logger.info(f"Sending to {config['host']}:{config['port']}")

    try:
        while True:
            try:
                # Try to receive data (from original main.py)
                data, addr = command_handler.sock.recvfrom(1024 * 4)
                flush_to_file(data)
            except timeout:
                # Timeout is expected, continue the loop
                continue
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                continue

    except KeyboardInterrupt:
        observer.stop()
        command_handler.sock.close()
        logger.info("Shutting down command sender...")
    finally:
        observer.join()

if __name__ == "__main__":
    main()
