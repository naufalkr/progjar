from socket import *
import socket
import threading
import logging
import sys
import time
from n_file_protocol import FileProtocol

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
                # Receive data in a buffer
                data = self.connection.recv(8192)
                if data:
                    buffer += data.decode()
                    logging.warning(f"Received request: {buffer[:100]}...")

                    # Check if we have a complete command (for uploads, we'll assume data is complete after a short delay)
                    if "UPLOAD" in buffer and len(buffer) > 1000:
                        # For upload commands, wait a bit to ensure all data is received
                        time.sleep(0.5)
                        more_data = self.connection.recv(8192)
                        if more_data:
                            buffer += more_data.decode()
                        
                        # Process the complete upload command
                        response = fp.proses_string(buffer) + "\r\n\r\n"
                        self.connection.sendall(response.encode())
                        break
                    elif buffer.strip() and not "UPLOAD" in buffer:
                        # For other commands, process immediately
                        response = fp.proses_string(buffer) + "\r\n\r\n"
                        self.connection.sendall(response.encode())
                        break
                else:
                    # If no more data and we have something in buffer, process it
                    if buffer:
                        response = fp.proses_string(buffer) + "\r\n\r\n"
                        self.connection.sendall(response.encode())
                    break
            except Exception as e:
                logging.error(f"Error: {str(e)}")
                break
        self.connection.close()

class Server(threading.Thread):
    def __init__(self, ipaddress='0.0.0.0', port=6667):
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
    svr = Server(ipaddress='0.0.0.0', port=6667)
    svr.start()

if __name__ == "__main__":
    main()