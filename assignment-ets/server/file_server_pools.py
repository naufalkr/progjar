import socket
import threading
import logging
import time
import sys
import shlex
import json
import struct
import os
import multiprocessing
import argparse
import signal
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps
from contextlib import contextmanager

from file_protocol import FileProtocol

# Socket configuration
SOCKET_CONFIG = {
    'buffer_size': 256 * 1024 * 1024,  # 256MB buffer
    'chunk_size': 256 * 1024 * 1024,   # 256MB chunks
    'backlog': 100,                    # Connection backlog
    'keepalive': {
        'idle': 60,                    # Seconds before sending keepalive probes
        'interval': 10,                # Interval between keepalives
        'count': 6                     # Number of keepalives before dropping
    }
}

# Helper decorators and context managers
def with_error_handling(func):
    """Decorator to handle exceptions and log errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

class ProcessTheClient:
    """Handles client connections and processes requests"""
    def __init__(self, connection, address):
        self.connection = optimize_socket(connection)
        self.address = address
        self.protocol = FileProtocol()
        self.running = True
        logger.info(f"New client handler for {address}")

    def receive_data(self, length):
        """Receive exact amount of data"""
        chunks = []
        bytes_received = 0
        
        while bytes_received < length:
            chunk = self.connection.recv(min(length - bytes_received, 
                                            SOCKET_CONFIG['chunk_size']))
            if not chunk:
                return None
                
            chunks.append(chunk)
            bytes_received += len(chunk)
            
        return b''.join(chunks)

    @with_error_handling
    def handle_client(self):
        """Main client handling loop"""
        while self.running:
            # Read message length
            length_data = self.connection.recv(4)
            if not length_data:
                break
                
            # Parse command length and read command
            cmd_length = struct.unpack('!I', length_data)[0]
            command_data = self.receive_data(cmd_length)
            
            if not command_data:
                break
                
            # Parse command
            command_str = command_data.decode()
            parts = shlex.split(command_str)
            
            if not parts:
                continue
                
            # Extract command components
            command = parts[0].lower()
            filename = parts[1] if len(parts) > 1 else ''
            
            # Handle file upload
            content = None
            if command == 'upload':
                length_data = self.connection.recv(4)
                if length_data:
                    file_length = struct.unpack('!I', length_data)[0]
                    content = self.receive_data(file_length)
            
            # Process command and send response
            result = self.protocol.proses_string(command, filename, content)
            response = json.dumps(result) + "\r\n\r\n"
            self.connection.sendall(response.encode())
        
        # Clean up connection
        self.connection.close()
        logger.info(f"Connection closed for {self.address}")

class Server(threading.Thread):
    """Server that handles client connections using a worker pool"""
    def __init__(self, ipaddress='0.0.0.0', port=8889, max_workers=50, use_process_pool=False):
        threading.Thread.__init__(self)
        self.ipaddress = ipaddress
        self.port = port
        self.max_workers = max_workers
        self.use_process_pool = use_process_pool
        self.running = False
        self.socket = None
        self.pool = None
        self.daemon = True  # Allow the thread to terminate with the program
    
    def initialize(self):
        """Initialize server socket and worker pool"""
        # Create and configure socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        optimize_socket(self.socket)
        
        # Bind socket
        self.socket.bind((self.ipaddress, self.port))
        self.socket.listen(SOCKET_CONFIG['backlog'])
        
        # Create appropriate worker pool
        if self.use_process_pool:
            self.pool = ProcessPoolExecutor(max_workers=self.max_workers)
            pool_type = "Process"
        else:
            self.pool = ThreadPoolExecutor(max_workers=self.max_workers)
            pool_type = "Thread"
            
        logger.info(f"Server initialized with {self.max_workers} {pool_type} workers")
        logger.info(f"Server listening on {self.ipaddress}:{self.port}")
    
    def stop(self):
        """Gracefully shut down the server"""
        self.running = False
        
        # Close the socket to interrupt accept()
        if self.socket:
            self.socket.close()
            
        # Shutdown the pool
        if self.pool:
            self.pool.shutdown(wait=True)
            
        logger.info("Server stopped")
    
    def run(self):
        """Main server loop"""
        self.initialize()
        self.running = True
        
        try:
            while self.running:
                try:
                    # Accept connection with timeout
                    self.socket.settimeout(1.0)  # 1 second timeout
                    client_socket, client_address = self.socket.accept()
                    
                    # Create client handler and submit to pool
                    handler = ProcessTheClient(client_socket, client_address)
                    self.pool.submit(handler.handle_client)
                    
                except socket.timeout:
                    # This allows checking self.running periodically
                    continue
                except socket.error as e:
                    if self.running:  # Only log if not shutdown
                        logger.error(f"Socket error: {e}")
                    break
                    
        finally:
            self.stop()

@contextmanager
def managed_socket(sock_type=socket.SOCK_STREAM):
    """Context manager for socket creation and cleanup"""
    sock = socket.socket(socket.AF_INET, sock_type)
    try:
        yield sock
    finally:
        sock.close()


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def optimize_socket(sock):
    """Apply performance optimizations to a socket"""
    # Set buffer sizes
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 
                    struct.pack('i', SOCKET_CONFIG['buffer_size']))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 
                    struct.pack('i', SOCKET_CONFIG['buffer_size']))
    
    # Set TCP options
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    
    # Set reuse address
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Enable keepalive
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 
                    SOCKET_CONFIG['keepalive']['idle'])
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 
                    SOCKET_CONFIG['keepalive']['interval'])
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 
                    SOCKET_CONFIG['keepalive']['count'])
    
    return sock

def get_user_input(prompt, options, default=None):
    """Get user input with validation"""
    while True:
        if default is not None:
            user_input = input(f"{prompt} [{default}]: ").strip() or str(default)
        else:
            user_input = input(f"{prompt}: ").strip()
            
        try:
            value = int(user_input)
            if value in options:
                return value
            print(f"Please enter one of: {', '.join(map(str, options))}")
        except ValueError:
            print("Please enter a number")

def main():
    """Main program entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="File Server with configurable worker pool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Define arguments
    parser.add_argument('--mode', type=int, choices=[1, 2], 
                       help='Pool mode: 1=ThreadPool, 2=ProcessPool')
    parser.add_argument('--workers', type=int, choices=[1, 5, 50], 
                       help='Number of workers')
    parser.add_argument('--port', type=int, default=8889, 
                       help='Port to listen on')
    parser.add_argument('--non-interactive', action='store_true',
                       help='Run in non-interactive mode')
    
    args = parser.parse_args()
    
    # Determine if we should use interactive mode
    use_interactive = (
        len(sys.argv) == 1 or  # No arguments provided
        (not args.non_interactive and args.mode is None and args.workers is None)
    )
    
    # Get configuration
    if use_interactive:
        print("\n=== File Server Configuration ===")
        print("Select execution mode:")
        print("  1. MultiThread Pool")
        print("  2. MultiProcess Pool")
        
        mode = get_user_input("\nMode [1, 2]", [1, 2])
        workers = get_user_input("Server Workers [1, 5, 50]" , [1, 5, 50])
    else:
        # Use command line arguments or defaults
        mode = args.mode if args.mode is not None else 1
        workers = args.workers if args.workers is not None else 50
    
    # Create and start server
    use_process_pool = (mode == 2)
    
    # For process pool, set multiprocessing start method
    if use_process_pool and sys.platform != 'win32':
        multiprocessing.set_start_method('spawn')
    
    # Print configuration
    pool_type = "Process Pool" if use_process_pool else "Thread Pool"
    print(f"\nStarting server with {pool_type} and {workers} workers")
    
    # Create server instance
    server = Server(
        ipaddress='0.0.0.0',
        port=args.port,
        max_workers=workers,
        use_process_pool=use_process_pool
    )
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down server...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start server
    server.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        server.join(timeout=5)

if __name__ == "__main__":
    main()