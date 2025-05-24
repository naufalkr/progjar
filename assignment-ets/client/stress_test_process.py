import argparse
import logging
import time
import os
import csv
import gc
import multiprocessing
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple, Callable, Any
from functools import partial
from file_client_cli_pool import remote_get, remote_upload

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OPERATIONS = ['upload', 'download']
CLIENT_WORKERS = [1, 5, 50]
SERVER_WORKERS = [1, 5, 50]
FILE_SIZES = {
    'test_10mb.bin': 10 * 1024 * 1024,
    'test_50mb.bin': 50 * 1024 * 1024,
    'test_100mb.bin': 100 * 1024 * 1024
}

def create_directory_if_not_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        logging.info(f"Created directory: {directory_path}")

def generate_test_file(filename: str, size: int) -> None:
    """Generate a test file with random data"""
    filepath = os.path.join("./files", filename)
    if not os.path.exists(filepath):
        with open(filepath, 'wb') as f:
            f.write(os.urandom(size))
        logging.info(f"Created test file: {filename}")

def prepare_test_files() -> None:
    """Prepare all test files"""
    create_directory_if_not_exists("./files")
    for filename, size in FILE_SIZES.items():
        generate_test_file(filename, size)

def get_file_size(filename: str) -> int:
    """Get the size of a file in bytes"""
    filepath = os.path.join("./files", filename)
    if not os.path.exists(filepath):
        logging.error(f"File not found: {filepath}")
        return 0
    return os.path.getsize(filepath)

# Worker function
def execute_operation(operation: str, filename: str, worker_id: int) -> Tuple[bool, float, int]:
    """Execute a file operation and measure performance"""
    start_time = time.time()
    try:
        logging.info(f"Worker {worker_id} starting {operation} of {filename}")
        
        # Execute the actual operation
        if operation == 'download':
            success = remote_get(filename)
        else:  # upload
            success = remote_upload(filename)
            
        # Get file size
        file_size = get_file_size(filename)
                
        # Calculate time and log completion
        time_taken = time.time() - start_time
        logging.info(f"Worker {worker_id} completed {operation} in {time_taken:.2f} seconds")
        
        # Force garbage collection
        gc.collect()
        
        return success, time_taken, file_size
            
    except Exception as e:
        logging.error(f"Worker {worker_id} error during {operation}: {str(e)}")
        return False, time.time() - start_time, 0

# Test execution functions
def execute_concurrent_test(operation: str, filename: str, num_clients: int, server_workers: int) -> Dict:
    """Run concurrent test with process pool executor"""
    start_time = time.time()
    results = []
    
    try:
        operation_func = partial(execute_operation, operation, filename)
        
        with ProcessPoolExecutor(max_workers=num_clients) as executor:
            futures = [executor.submit(operation_func, i) for i in range(num_clients)]
            
            results = [future.result() for future in futures]
    
    finally:
        if operation == 'download':
            try:
                os.remove(filename)
            except:
                pass
        
        gc.collect()
    
    total_time = time.time() - start_time
    successful_workers = sum(1 for success, _, _ in results if success)
    failed_workers = num_clients - successful_workers
    total_bytes = sum(bytes_transferred for _, _, bytes_transferred in results)
    
    time_per_client = total_time / num_clients
    throughput = total_bytes / total_time if total_time > 0 else 0
    
    return {
        "operation": operation,
        "filename": filename,
        "num_clients": num_clients,
        "server_workers": server_workers,
        "total_time": total_time,
        "total_time_per_client": time_per_client,
        "throughput_per_client": throughput,
        "successful_workers": successful_workers,
        "failed_workers": failed_workers,
        "total_bytes_transferred": total_bytes
    }

def format_result_for_display(result: Dict) -> str:
    """Format a result for display"""
    lines = []
    lines.append(f"\nProcess Results for {result['operation']} {result['filename']}:")
    lines.append(f"Client Workers: {result['num_clients']}")
    lines.append(f"Server Workers: {result['server_workers']}")
    lines.append(f"Total Time per Client: {result['total_time_per_client']:.2f} seconds")
    lines.append(f"Throughput per Client: {result['throughput_per_client']/1024/1024:.2f} MB/s")
    lines.append(f"Successful Workers: {result['successful_workers']}")
    lines.append(f"Failed Workers: {result['failed_workers']}")
    lines.append("-" * 80)
    return "\n".join(lines)

def display_result(result: Dict) -> None:
    """Display a test result"""
    print(format_result_for_display(result))

def write_results_to_csv(results: List[Dict], filename: str = None) -> None:
    """Write results to CSV file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_process_results_{timestamp}.csv"
    
    headers = [
        "Nomor",
        "Operasi",
        "Volume",
        "Jumlah Client Worker",
        "Jumlah Server Worker Pool",
        "Waktu Total per Client (seconds)",
        "Throughput per Client (bytes/second)",
        "Client Workers Sukses",
        "Client Workers Gagal"
    ]
    
    try:
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            
            if not file_exists:
                writer.writeheader()
            
            start_idx = 1
            if file_exists:
                with open(filename, 'r') as f:
                    start_idx = sum(1 for _ in f)  # Count existing rows
            
            for idx, result in enumerate(results, start_idx):
                row = {
                    "Nomor": idx,
                    "Operasi": result['operation'],
                    "Volume": result['filename'],
                    "Jumlah Client Worker": result['num_clients'],
                    "Jumlah Server Worker Pool": result['server_workers'],
                    "Waktu Total per Client (seconds)": f"{result['total_time_per_client']:.2f}",
                    "Throughput per Client (bytes/second)": f"{result['throughput_per_client']:.2f}",
                    "Client Workers Sukses": result['successful_workers'],
                    "Client Workers Gagal": result['failed_workers']
                }
                writer.writerow(row)
                
        logging.info(f"Results appended to {filename}")
        
    except Exception as e:
        logging.error(f"Error saving results to CSV: {str(e)}")

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Process-based stress test')
    parser.add_argument('--server-workers', type=int, choices=[1, 5, 50], 
                       help='Number of server worker processes')
    return parser.parse_args()

def run_test_matrix(server_workers_list: List[int]) -> List[Dict]:
    """Run all combinations of tests"""
    results = []
    
    for server_workers in server_workers_list:
        for operation in OPERATIONS:
            for filename in FILE_SIZES.keys():
                for num_clients in CLIENT_WORKERS:
                    logging.info(f"Testing {operation} of {filename} with {num_clients} client workers and {server_workers} server workers")                    
                    result = execute_concurrent_test(
                        operation, 
                        filename, 
                        num_clients,
                        server_workers
                    )
                    display_result(result)
                    results.append(result)                    
                    gc.collect()
    
    return results

def main() -> None:
    """Main entry point"""
    multiprocessing.set_start_method('spawn')
    args = parse_arguments()
    server_workers_to_test = [args.server_workers] if args.server_workers else SERVER_WORKERS
    prepare_test_files()
    results = run_test_matrix(server_workers_to_test)
    write_results_to_csv(results)

if __name__ == "__main__":
    main()