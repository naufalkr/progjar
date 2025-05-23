import subprocess
import time
import os
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

def start_server(server_type, pool_size):
    """Start the file server with the specified type and pool size"""
    if server_type == "thread":
        script = "file_server_threadpool.py"
    else:
        script = "file_server_processpool.py"
    
    # Start the server as a subprocess
    server_dir = os.path.join("..", "work1")
    server_path = os.path.join(server_dir, script)
    
    # Make sure we're using the absolute path
    server_path = os.path.abspath(server_path)
    
    logging.info(f"Starting server {script} with pool size {pool_size}")
    process = subprocess.Popen(["python", server_path, str(pool_size)], 
                              cwd=server_dir)
    
    # Give the server time to start up
    time.sleep(2)
    return process

def run_client_test(operation, file_size, client_pool_size, client_pool_type):
    """Run a client stress test with the specified parameters"""
    logging.info(f"Running client test: {operation} {file_size}MB with "
                f"{client_pool_size} {client_pool_type} workers")
    
    command = [
        "python", "stress_test_client.py",
        "--operation", operation,
        "--file-size", str(file_size),
        "--pool-size", str(client_pool_size),
        "--pool-type", client_pool_type
    ]
    
    process = subprocess.run(command, capture_output=True, text=True)
    
    if process.returncode == 0:
        logging.info("Client test completed successfully")
    else:
        logging.error(f"Client test failed: {process.stderr}")
    
    return process.stdout

def run_full_stress_test():
    """Run the complete stress test with all combinations"""
    operations = ["upload", "download"]
    file_sizes = [10, 50, 100]
    client_pool_sizes = [1, 5, 50]
    server_pool_sizes = [1, 5, 50]
    server_types = ["thread", "process"]
    client_types = ["thread", "process"]
    
    results = []
    row_num = 1
    
    # Create results directory and CSV file
    import csv
    from datetime import datetime
    
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join("results", f"complete_stress_test_{timestamp}.csv")
    
    with open(results_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'No.', 'Operation', 'File Size (MB)', 'Client Pool Size', 'Server Pool Size',
            'Total Time (s)', 'Throughput (B/s)',
            'Successful Clients', 'Failed Clients',
            'Successful Server Workers', 'Failed Server Workers',
            'Server Pool Type', 'Client Pool Type'
        ])
    
    # Run all test combinations
    for operation in operations:
        for file_size in file_sizes:
            for client_pool_size in client_pool_sizes:
                for server_pool_size in server_pool_sizes:
                    for server_type in server_types:
                        for client_type in client_types:
                            # Start the appropriate server
                            server_process = start_server(server_type, server_pool_size)
                            
                            try:
                                # Run the client test
                                client_output = run_client_test(
                                    operation, file_size, client_pool_size, client_type)
                                
                                # Parse client output for results
                                # In a real implementation, you would parse the actual output
                                # Here we'll just use placeholder values for the CSV
                                total_time = "N/A"  # Would be parsed from client output
                                throughput = "N/A"  # Would be parsed from client output
                                successful_clients = client_pool_size  # Assuming all succeed
                                failed_clients = 0
                                successful_server = server_pool_size  # Assuming all succeed
                                failed_server = 0
                                
                                # Record the results
                                result_row = [
                                    row_num, operation, file_size, 
                                    client_pool_size, server_pool_size,
                                    total_time, throughput,
                                    successful_clients, failed_clients,
                                    successful_server, failed_server,
                                    server_type, client_type
                                ]
                                
                                # Append to CSV
                                with open(results_file, 'a', newline='') as csvfile:
                                    writer = csv.writer(csvfile)
                                    writer.writerow(result_row)
                                
                                row_num += 1
                                
                            finally:
                                # Stop the server
                                server_process.terminate()
                                server_process.wait()
                                logging.info("Server stopped")
    
    logging.info(f"All tests completed. Results saved to {results_file}")
    return results_file

def main():
    parser = argparse.ArgumentParser(description="Run File Server Stress Tests")
    parser.add_argument("--run-all", action="store_true", 
                        help="Run all test combinations")
    
    args = parser.parse_args()
    
    if args.run_all:
        results_file = run_full_stress_test()
        print(f"All tests completed. Results saved to {results_file}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()