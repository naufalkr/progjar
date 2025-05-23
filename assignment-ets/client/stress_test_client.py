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
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Server configuration
SERVER_ADDRESS = ('172.16.16.101', 6667)

# Test parameters
OPERATIONS = ['download', 'upload']
FILE_SIZES = [10, 50, 100]  # MB
CLIENT_POOL_SIZES = [1, 5, 50]
SERVER_POOL_SIZES = [1, 5, 50]

def generate_random_data(size_mb):
    """Generate a random file of specified size in MB"""
    size_bytes = size_mb * 1024 * 1024
    # Generate a more efficient way by creating chunks
    chunk_size = 1024 * 1024  # 1MB chunks
    data = b''
    for _ in range(0, size_bytes, chunk_size):
        remaining = min(chunk_size, size_bytes - len(data))
        data += ''.join(random.choice(string.ascii_letters) for _ in range(remaining)).encode()
    return data

def prepare_test_files():
    """Generate test files for different sizes"""
    test_files = {}
    
    for size in FILE_SIZES:
        filename = f"test_file_{size}MB.dat"
        filepath = os.path.join("test_files", filename)
        
        # Create directory if it doesn't exist
        os.makedirs("test_files", exist_ok=True)
        
        # Check if file already exists with correct size
        if os.path.exists(filepath) and os.path.getsize(filepath) == size * 1024 * 1024:
            logging.info(f"Test file {filename} already exists with correct size")
        else:
            logging.info(f"Generating test file of {size}MB...")
            data = generate_random_data(size)
            with open(filepath, 'wb') as f:
                f.write(data)
            logging.info(f"Generated {filename}")
        
        test_files[size] = filepath
    
    return test_files

def send_command(command_str, timeout=120):
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
    logging.info(f"Worker {worker_id}: Starting upload of {filename}")
    
    try:
        with open(filepath, 'rb') as f:
            file_data = base64.b64encode(f.read()).decode()
        
        command = f"UPLOAD {filename} {file_data}"
        result = send_command(command, timeout=300)
        
        if result['success']:
            logging.info(f"Worker {worker_id}: Successfully uploaded {filename}")
        else:
            logging.error(f"Worker {worker_id}: Failed to upload {filename}: {result['error_msg']}")
        
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
    logging.info(f"Worker {worker_id}: Starting download of {filename}")
    
    try:
        command = f"GET {filename}"
        result = send_command(command, timeout=300)
        
        if result['success']:
            logging.info(f"Worker {worker_id}: Successfully downloaded {filename}")
        else:
            logging.error(f"Worker {worker_id}: Failed to download {filename}: {result['error_msg']}")
        
        return result
    
    except Exception as e:
        logging.error(f"Worker {worker_id}: Error during download: {str(e)}")
        return {
            'success': False,
            'error_msg': str(e),
            'elapsed_time': 0,
            'bytes_processed': 0
        }

def run_worker_thread(operation, filepath, worker_id):
    """Function to be executed by each worker thread"""
    filename = os.path.basename(filepath)
    
    try:
        if operation == 'upload':
            return upload_file(filepath, worker_id)
        else:  # download
            return download_file(filename, worker_id)
    except Exception as e:
        logging.error(f"Worker {worker_id} failed: {str(e)}")
        return {
            'success': False,
            'error_msg': str(e),
            'elapsed_time': 0,
            'bytes_processed': 0
        }

def run_test_with_threadpool(operation, filepath, client_pool_size):
    """Run a test using a thread pool"""
    filename = os.path.basename(filepath)
    filesize_bytes = os.path.getsize(filepath)
    
    start_time = time.time()
    results = []
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=client_pool_size) as executor:
            # Submit tasks to the pool
            futures = [executor.submit(run_worker_thread, operation, filepath, i) 
                      for i in range(client_pool_size)]
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    
    except Exception as e:
        logging.error(f"Error in thread pool execution: {str(e)}")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate metrics
    successful = sum(1 for r in results if r['success'])
    failed = client_pool_size - successful
    
    if successful > 0:
        avg_time = sum(r['elapsed_time'] for r in results if r['success']) / successful
        avg_throughput = filesize_bytes / avg_time if avg_time > 0 else 0
    else:
        avg_time = 0
        avg_throughput = 0
    
    return {
        'total_time': total_time,
        'avg_client_time': avg_time,
        'throughput': avg_throughput,
        'successful_clients': successful,
        'failed_clients': failed,
    }

def run_test_with_processpool(operation, filepath, client_pool_size):
    """Run a test using a process pool"""
    filename = os.path.basename(filepath)
    filesize_bytes = os.path.getsize(filepath)
    
    start_time = time.time()
    
    # Prepare arguments for each worker
    args = [(operation, filepath, i) for i in range(client_pool_size)]
    
    try:
        with multiprocessing.Pool(processes=client_pool_size) as pool:
            # Map worker function to arguments
            results = pool.starmap(run_worker_thread, args)
    
    except Exception as e:
        logging.error(f"Error in process pool execution: {str(e)}")
        results = []
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate metrics
    successful = sum(1 for r in results if r['success'])
    failed = client_pool_size - successful
    
    if successful > 0:
        avg_time = sum(r['elapsed_time'] for r in results if r['success']) / successful
        avg_throughput = filesize_bytes / avg_time if avg_time > 0 else 0
    else:
        avg_time = 0
        avg_throughput = 0
    
    return {
        'total_time': total_time,
        'avg_client_time': avg_time,
        'throughput': avg_throughput,
        'successful_clients': successful,
        'failed_clients': failed,
    }

def run_complete_stress_test():
    """Run all combinations of stress tests and record results"""
    # Prepare test files
    test_files = prepare_test_files()
    results = []
    row_num = 1
    
    # Create results directory
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join("results", f"stress_test_results_{timestamp}.csv")
    
    # Write header to CSV
    with open(results_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'No.', 'Operation', 'File Size (MB)', 'Client Pool Size', 'Server Pool Size',
            'Total Time (s)', 'Avg Client Time (s)', 'Throughput (B/s)',
            'Successful Clients', 'Failed Clients',
            'Server Pool Type', 'Client Pool Type'
        ])
    
    # Test combinations
    for operation in OPERATIONS:
        for file_size in FILE_SIZES:
            filepath = test_files[file_size]
            
            for client_pool_size in CLIENT_POOL_SIZES:
                for server_pool_size in SERVER_POOL_SIZES:
                    for server_pool_type in ['thread', 'process']:
                        for client_pool_type in ['thread', 'process']:
                            logging.info(f"Running test: {operation}, {file_size}MB, "
                                        f"client_pool={client_pool_size} ({client_pool_type}), "
                                        f"server_pool={server_pool_size} ({server_pool_type})")
                            
                            # Setup the server with the appropriate type and size
                            # Note: In a real test, you would need to configure and start
                            # the appropriate server before running each test
                            
                            # Run the appropriate client test
                            if client_pool_type == 'thread':
                                test_result = run_test_with_threadpool(operation, filepath, client_pool_size)
                            else:
                                test_result = run_test_with_processpool(operation, filepath, client_pool_size)
                            
                            # Record the results
                            result_row = [
                                row_num,
                                operation,
                                file_size,
                                client_pool_size,
                                server_pool_size,
                                test_result['total_time'],
                                test_result['avg_client_time'],
                                test_result['throughput'],
                                test_result['successful_clients'],
                                test_result['failed_clients'],
                                server_pool_type,
                                client_pool_type
                            ]
                            
                            # Append to CSV
                            with open(results_file, 'a', newline='') as csvfile:
                                writer = csv.writer(csvfile)
                                writer.writerow(result_row)
                            
                            # Increment row number
                            row_num += 1
                            
                            # Log the result
                            logging.info(f"Test completed: {operation}, {file_size}MB, "
                                        f"client={client_pool_size}, server={server_pool_size}, "
                                        f"successful={test_result['successful_clients']}, "
                                        f"failed={test_result['failed_clients']}")
    
    logging.info(f"All tests completed. Results saved to {results_file}")
    return results_file

def main():
    parser = argparse.ArgumentParser(description="File Server Stress Test Client")
    parser.add_argument("--server", default="172.16.16.101", help="Server IP address")
    parser.add_argument("--port", type=int, default=6667, help="Server port")
    parser.add_argument("--run-all", action="store_true", help="Run all test combinations")
    
    args = parser.parse_args()
    
    # Update server address if provided
    global SERVER_ADDRESS
    SERVER_ADDRESS = (args.server, args.port)
    
    if args.run_all:
        results_file = run_complete_stress_test()
        print(f"All tests completed. Results saved to {results_file}")
    else:
        # If not running all tests, show usage
        parser.print_help()

if __name__ == "__main__":
    main()