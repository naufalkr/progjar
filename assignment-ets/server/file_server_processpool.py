from socket import *
import socket
import threading
import logging
import sys
import time
import multiprocessing
from functools import partial
from file_protocol import FileProtocol

# Global protocol instance
fp = FileProtocol()

def handle_client_connection(connection_fd, client_address):
    """Process a client connection using the file descriptor"""
    # Create socket from file descriptor
    connection = socket.fromfd(connection_fd, socket.AF_INET, socket.SOCK_STREAM)
    connection_fd = None  # Close the duplicate file descriptor
    
    logging.warning(f"Process handling connection from {client_address}")
    buffer = ""
    try:
        while True:
            data = connection.recv(8192)
            if data:
                buffer += data.decode()
                logging.warning(f"Received request: {buffer[:100]}...")

                if "UPLOAD" in buffer and len(buffer) > 1000:
                    time.sleep(0.5)
                    more_data = connection.recv(8192)
                    if more_data:
                        buffer += more_data.decode()
                    
                    response = fp.proses_string(buffer) + "\r\n\r\n"
                    connection.sendall(response.encode())
                    break
                elif buffer.strip() and not "UPLOAD" in buffer:
                    response = fp.proses_string(buffer) + "\r\n\r\n"
                    connection.sendall(response.encode())
                    break
            else:
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
        logging.warning(f"Server running on {self.ipinfo} with process pool size: {self.pool_size}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(5)
        
        # Create process pool
        with multiprocessing.Pool(processes=self.pool_size) as pool:
            while True:
                try:
                    connection, client_address = self.my_socket.accept()
                    # We need to pass the file descriptor, not the socket itself
                    connection_fd = connection.fileno()
                    # Ensure the socket doesn't close when we pass the fd to another process
                    connection._sock.detach()
                    
                    # Apply partial to fix client_address argument
                    pool.apply_async(handle_client_connection, args=(connection_fd, client_address))
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logging.error(f"Error accepting connections: {str(e)}")
        
        self.my_socket.close()
        logging.warning("Server stopped")

def main():
    # Default pool size, can be overridden with command line argument
    pool_size = 5
    if len(sys.argv) > 1:
        pool_size = int(sys.argv[1])
        
    svr = Server(ipaddress='0.0.0.0', port=6667, pool_size=pool_size)
    svr.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')  # Use spawn method for better cross-platform compatibility
    main()