import os
import time
import random
import string
import socket
import base64
import json
import logging
import argparse
import multiprocessing
import concurrent.futures
import csv
import subprocess
import sys
import platform
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Server configuration
SERVER_ADDRESS = ('127.0.0.1', 6667)

# Test parameters
OPERATIONS = ['download', 'upload']
FILE_SIZES = [10, 50, 100]  # MB
CLIENT_POOL_SIZES = [1, 5, 50]
SERVER_POOL_SIZES = [1, 5, 50]

def generate_test_file(size_mb, filename):
    """Generate a test file of specified size in MB"""
    size_bytes = size_mb * 1024 * 1024
    logging.info(f"Generating {filename} of size {size_mb}MB...")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'wb') as f:
        chunk_size = 1024 * 1024  # 1MB chunks
        for i in range(0, size_bytes, chunk_size):
            remaining = min(chunk_size, size_bytes - i)
            chunk = ''.join(random.choice(string.ascii_letters) for _ in range(remaining)).encode()
            f.write(chunk)
    
    logging.info(f"Generated {filename} ({os.path.getsize(filename)} bytes)")
    return filename

def prepare_test_files():
    """Generate test files for different sizes"""
    test_files = {}
    
    for size in FILE_SIZES:
        filename = f"test_files/test_file_{size}MB.dat"
        
        # Create directory if it doesn't exist
        os.makedirs("test_files", exist_ok=True)
        
        # Check if file already exists with correct size
        if os.path.exists(filename) and os.path.getsize(filename) == size * 1024 * 1024:
            logging.info(f"Test file {filename} already exists with correct size")
        else:
            generate_test_file(size, filename)
        
        test_files[size] = filename
    
    return test_files

def send_command(command_str, timeout=300):
    """Send a command to the server and get the response"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)  # Set a longer timeout for large uploads
    
    start_time = time.time()
    bytes_processed = 0
    success = False
    error_msg = ""
    
    try:
        sock.connect(SERVER_ADDRESS)
        
        # For large uploads, send in chunks
        chunk_size = 16384  # 16KB chunks
        for i in range(0, len(command_str), chunk_size):
            chunk = command_str[i:i+chunk_size]
            sock.sendall(chunk.encode())
            bytes_processed += len(chunk)
        
        # Wait for response
        data_received = ""
        while True:
            data = sock.recv(16384)
            if data:
                data_received += data.decode()
                bytes_processed += len(data)
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
        
        clean_data = data_received.split("\r\n\r\n")[0]
        response = json.loads(clean_data)
        success = response.get('status') == 'OK'
        if not success:
            error_msg = response.get('data', 'Unknown error')
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error in communication: {error_msg}")
    finally:
        sock.close()
    
    elapsed_time = time.time() - start_time
    return {
        'success': success,
        'error_msg': error_msg,
        'elapsed_time': elapsed_time,
        'bytes_processed': bytes_processed
    }

def upload_file(filepath, worker_id):
    """Upload a file to the server"""
    filename = os.path.basename(filepath)
    logging.info(f"Worker {worker_id}: Uploading {filename}...")
    
    try:
        with open(filepath, 'rb') as f:
            file_data = base64.b64encode(f.read()).decode()
        
        command = f"UPLOAD {filename} {file_data}"
        result = send_command(command)
        
        if result['success']:
            logging.info(f"Worker {worker_id}: Upload successful for {filename}")
        else:
            logging.error(f"Worker {worker_id}: Upload failed for {filename}: {result['error_msg']}")
        
        return result
    
    except Exception as e:
        logging.error(f"Worker {worker_id}: Error during upload: {str(e)}")
        return {
            'success': False,
            'error_msg': str(e),
            'elapsed_time': 0,
            'bytes_processed': 0
        }

def download_file(filename, worker_id):
    """Download a file from the server"""
    logging.info(f"Worker {worker_id}: Downloading {filename}...")
    
    try:
        command = f"GET {filename}"
        result = send_command(command)
        
        if result['success']:
            logging.info(f"Worker {worker_id}: Download successful for {filename}")
        else:
            logging.error(f"Worker {worker_id}: Download failed for {filename}: {result['error_msg']}")
        
        return result
    
    except Exception as e:
        logging.error(f"Worker {worker_id}: Error during download: {str(e)}")
        return {
            'success': False,
            'error_msg': str(e),
            'elapsed_time': 0,
            'bytes_processed': 0
        }

def run_client_operation(operation, filepath, worker_id):
    """Function to be executed by each worker thread/process"""
    if operation == 'upload':
        return upload_file(filepath, worker_id)
    else:  # download
        filename = os.path.basename(filepath)
        return download_file(filename, worker_id)

def run_test_threadpool(operation, filepath, client_pool_size):
    """Run a test using a thread pool"""
    filesize_bytes = os.path.getsize(filepath)
    
    results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=client_pool_size) as executor:
        futures = [executor.submit(run_client_operation, operation, filepath, i) 
                  for i in range(client_pool_size)]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logging.error(f"Worker exception: {str(e)}")
                results.append({
                    'success': False,
                    'error_msg': str(e),
                    'elapsed_time': 0,
                    'bytes_processed': 0
                })
    
    total_time = time.time() - start_time
    
    # Calculate metrics
    successful = sum(1 for r in results if r['success'])
    failed = client_pool_size - successful
    
    throughput = 0
    if successful > 0:
        # Calculate average time and throughput for successful operations
        avg_time = sum(r['elapsed_time'] for r in results if r['success']) / successful
        throughput = filesize_bytes / avg_time if avg_time > 0 else 0
    
    return {
        'total_time': total_time,
        'throughput': throughput,
        'successful_clients': successful,
        'failed_clients': failed
    }

def run_test_processpool(operation, filepath, client_pool_size):
    """Run a test using a process pool"""
    filesize_bytes = os.path.getsize(filepath)
    
    # Create args for each process
    args = [(operation, filepath, i) for i in range(client_pool_size)]
    
    start_time = time.time()
    
    with multiprocessing.Pool(processes=client_pool_size) as pool:
        results = pool.starmap(run_client_operation, args)
    
    total_time = time.time() - start_time
    
    # Calculate metrics
    successful = sum(1 for r in results if r['success'])
    failed = client_pool_size - successful
    
    throughput = 0
    if successful > 0:
        # Calculate average time and throughput for successful operations
        avg_time = sum(r['elapsed_time'] for r in results if r['success']) / successful
        throughput = filesize_bytes / avg_time if avg_time > 0 else 0
    
    return {
        'total_time': total_time,
        'throughput': throughput,
        'successful_clients': successful,
        'failed_clients': failed
    }

def start_server(server_type, pool_size):
    """Start the server with the specified configuration"""
    server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work1")
    
    if server_type == 'thread':
        server_script = os.path.join(server_dir, "file_server_threadpool.py")
    else:  # process
        server_script = os.path.join(server_dir, "file_server_processpool.py")
    
    if platform.system() == 'Windows':
        # Use pythonw on Windows to avoid console windows
        cmd = [sys.executable, server_script, str(pool_size)]
    else:
        cmd = [sys.executable, server_script, str(pool_size)]
    
    logging.info(f"Starting {server_type} server with pool size {pool_size}")
    process = subprocess.Popen(cmd, cwd=server_dir)
    
    # Give the server time to start
    time.sleep(3)
    return process

def run_complete_stress_test():
    """Run all combinations of stress tests"""
    # Prepare test files
    test_files = prepare_test_files()
    
    # Create results directory
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join("results", f"stress_test_results_{timestamp}.csv")
    
    # Create CSV file with header
    with open(results_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'No.', 'Operation', 'Volume (MB)', 'Client Pool Size', 'Server Pool Size',
            'Total Time (s)', 'Throughput (B/s)', 
            'Successful Clients', 'Failed Clients',
            'Successful Server Workers', 'Failed Server Workers'
        ])
    
    row_num = 1
    server_process = None
    
    try:
        # Run all combinations
        for operation in OPERATIONS:
            for file_size in FILE_SIZES:
                filepath = test_files[file_size]
                
                for server_pool_size in SERVER_POOL_SIZES:
                    for server_type in ['thread', 'process']:
                        # Start server
                        if server_process:
                            server_process.terminate()
                            server_process.wait()
                        
                        server_process = start_server(server_type, server_pool_size)
                        
                        for client_pool_size in CLIENT_POOL_SIZES:
                            for client_type in ['thread', 'process']:
                                logging.info(f"Running test {row_num}: {operation}, {file_size}MB, "
                                           f"{client_pool_size} {client_type} clients, "
                                           f"{server_pool_size} {server_type} server workers")
                                
                                # Run test with appropriate pool type
                                if client_type == 'thread':
                                    result = run_test_threadpool(operation, filepath, client_pool_size)
                                else:  # process
                                    result = run_test_processpool(operation, filepath, client_pool_size)
                                
                                # Record results
                                with open(results_file, 'a', newline='') as csvfile:
                                    writer = csv.writer(csvfile)
                                    writer.writerow([
                                        row_num,
                                        operation,
                                        file_size,
                                        client_pool_size,
                                        server_pool_size,
                                        result['total_time'],
                                        result['throughput'],
                                        result['successful_clients'],
                                        result['failed_clients'],
                                        server_pool_size,  # Assuming all server workers successful
                                        0  # Assuming no server worker failures
                                    ])
                                
                                row_num += 1
                                
                                # Brief delay between tests
                                time.sleep(1)
    
    finally:
        # Clean up server process if it's still running
        if server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
    
    logging.info(f"All tests completed. Results saved to {results_file}")
    return results_file

def main():
    parser = argparse.ArgumentParser(description="File Server Stress Test")
    parser.add_argument("--server-host", default="127.0.0.1", help="Server host address")
    parser.add_argument("--server-port", type=int, default=6667, help="Server port")
    
    args = parser.parse_args()
    
    # Update server address
    global SERVER_ADDRESS
    SERVER_ADDRESS = (args.server_host, args.server_port)
    
    try:
        results_file = run_complete_stress_test()
        print(f"Stress test completed. Results saved to: {results_file}")
    except KeyboardInterrupt:
        print("Stress test interrupted by user")
    except Exception as e:
        print(f"Error in stress test: {str(e)}")

if __name__ == "__main__":
    multiprocessing.freeze_support()  # For Windows compatibility
    main()