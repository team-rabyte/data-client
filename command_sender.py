import json
import time
import logging
import os
from socket import socket, AF_INET, SOCK_DGRAM
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CommandHandler(FileSystemEventHandler):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.last_modified = 0
        self.cooldown = 0.1
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
                # Prepare command data
                command_to_send = {
                    "roll": latest_command["roll"],
                    "pitch": latest_command["pitch"],
                    "throttle": latest_command["throttle"],
                    "yaw": latest_command["yaw"],
                    "pid_x": latest_command["pid_x"],
                    "pid_y": latest_command["pid_y"],
                    "pid_z": latest_command["pid_z"],
                    "pid_yaw": latest_command["pid_yaw"]
                }
                
                # Send the command
                command_bytes = json.dumps(command_to_send).encode()
                self.sock.sendto(command_bytes, (self.host, self.port))
                logging.info(f"Sent command: {command_to_send}")
                
                # Wait for confirmation
                try:
                    response, addr = self.sock.recvfrom(1024)
                    response_data = json.loads(response.decode())
                    logging.info(f"Received confirmation from {addr}: {response_data}")
                except socket.timeout:
                    logging.warning("No confirmation received from server")
                
                self.last_sent_command = latest_command

        except Exception as e:
            logging.error(f"Error sending command: {e}")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return

    command_handler = CommandHandler(config['host'], config['port'])
    observer = Observer()
    observer.schedule(command_handler, path='.', recursive=False)
    observer.start()

    logging.info(f"Started command sender. Watching for changes in commands.txt")
    logging.info(f"Sending to {config['host']}:{config['port']}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        command_handler.sock.close()
        logging.info("Shutting down command sender...")

    observer.join()

if __name__ == "__main__":
    main()