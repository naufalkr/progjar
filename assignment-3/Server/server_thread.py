from socket import *
import socket
import threading
import logging
import sys
import time
import json
import base64
from file_protocol import FileProtocol

fp = FileProtocol()

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        buffer = ""
        while True:
            try:
                data = self.connection.recv(8192)
                if data:
                    buffer += data.decode()
                    logging.warning(f"Received data: {buffer[:50]}...")  # Log first 50 chars

                    if "\r\n" in buffer:
                        # Extract command and parameters
                        command_line = buffer.strip()
                        parts = command_line.split(" ", 2)  # Split into at most 3 parts
                        
                        # Parse command
                        command = parts[0].lower() if parts else ""
                        filename = parts[1] if len(parts) > 1 else ""
                        content = parts[2] if len(parts) > 2 else None
                        
                        # Special handling for UPLOAD which contains base64 data
                        if command == "upload" and content:
                            # Content is already base64 encoded from client
                            pass
                            
                        # Process the command with the new protocol interface
                        result = fp.proses_string(command, filename, content)
                        response = json.dumps(result) + "\r\n\r\n"
                        self.connection.sendall(response.encode())
                        break
                else:
                    break
            except Exception as e:
                logging.error(f"Error: {str(e)}")
                break
        self.connection.close()

class Server(threading.Thread):
    def __init__(self, ipaddress='0.0.0.0', port=8889):
        self.ipinfo = (ipaddress, port)
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        threading.Thread.__init__(self)

    def run(self):
        logging.warning(f"Server running on {self.ipinfo}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(5)
        while True:
            try:
                connection, client_address = self.my_socket.accept()
                logging.warning(f"Connection from {client_address}")
                clt = ProcessTheClient(connection, client_address)
                clt.start()
                self.the_clients.append(clt)
            except KeyboardInterrupt:
                self.my_socket.close()
                sys.exit(0)

def main():
    svr = Server(ipaddress='0.0.0.0', port=8889)
    svr.start()

if __name__ == "__main__":
    main()