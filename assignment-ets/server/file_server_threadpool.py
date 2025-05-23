from socket import *
import socket
import threading
import logging
import sys
import time
import concurrent.futures
from file_protocol import FileProtocol

fp = FileProtocol()

def handle_client(connection, address):
    logging.warning(f"Connection from {address}")
    buffer = ""
    try:
        while True:
            # Receive data in a buffer
            data = connection.recv(8192)
            if data:
                buffer += data.decode()
                logging.warning(f"Received request: {buffer[:100]}...")

                # Check if we have a complete command
                if "UPLOAD" in buffer and len(buffer) > 1000:
                    # For upload commands, wait a bit to ensure all data is received
                    time.sleep(0.5)
                    more_data = connection.recv(8192)
                    if more_data:
                        buffer += more_data.decode()
                    
                    # Process the complete upload command
                    response = fp.proses_string(buffer) + "\r\n\r\n"
                    connection.sendall(response.encode())
                    break
                elif buffer.strip() and not "UPLOAD" in buffer:
                    # For other commands, process immediately
                    response = fp.proses_string(buffer) + "\r\n\r\n"
                    connection.sendall(response.encode())
                    break
            else:
                # If no more data and we have something in buffer, process it
                if buffer:
                    response = fp.proses_string(buffer) + "\r\n\r\n"
                    connection.sendall(response.encode())
                break
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    finally:
        connection.close()

class Server(threading.Thread):
    def __init__(self, ipaddress='0.0.0.0', port=6667, pool_size=5):
        self.ipinfo = (ipaddress, port)
        self.pool_size = pool_size
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        threading.Thread.__init__(self)

    def run(self):
        logging.warning(f"Server running on {self.ipinfo} with thread pool size: {self.pool_size}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(5)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.pool_size) as executor:
            while True:
                try:
                    connection, client_address = self.my_socket.accept()
                    executor.submit(handle_client, connection, client_address)
                except KeyboardInterrupt:
                    break
        
        self.my_socket.close()
        logging.warning("Server stopped")

def main():
    # Default pool size, can be overridden with command line argument
    pool_size = 5
    if len(sys.argv) > 1:
        pool_size = int(sys.argv[1])
        
    svr = Server(ipaddress='0.0.0.0', port=6667, pool_size=pool_size)
    svr.start()

if __name__ == "__main__":
    main()