import socket
import logging
from argparse import ArgumentParser
from pathlib import Path

class HTTPClient:
    # Thread pool
    # def __init__(self, host='172.16.16.101', port=8885):
    #     self.server_location = (host, port)
    #     logging.basicConfig(level=logging.WARNING)

    # # Process pool        
    def __init__(self, host='172.16.16.101', port=8889):
        self.server_location = (host, port)
        logging.basicConfig(level=logging.WARNING)

    def create_connection(self):
        try:
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.connect(self.server_location)
            return connection
        except Exception as err:
            logging.warning(f"Connection error: {err}")
            return None

    def execute_request(self, request_data):
        with self.create_connection() as conn:
            if not conn:
                return None
                
            try:
                conn.sendall(request_data.encode())
                
                response = []
                while True:
                    chunk = conn.recv(2048)
                    if not chunk:
                        break
                    response.append(chunk.decode())
                    if "\r\n\r\n" in response[-1]:
                        break
                        
                return ''.join(response)
            except Exception as err:
                return None

class FileOperations(HTTPClient):
    def fetch_file_list(self):
        request = "GET /list HTTP/1.1\r\nHost: 172.16.16.101\r\n\r\n"
        result = self.execute_request(request)
        print("Server response:")
        print(result)

    def send_file(self, file_path):
        try:
            file_content = Path(file_path).read_bytes()
            file_name = Path(file_path).name
            
            request_headers = (
                "POST /upload HTTP/1.1\r\n"
                "Host: localhost\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
                f"Content-Length: {len(file_content)}\r\n"
                "\r\n"
            )
            
            with self.create_connection() as conn:
                if not conn:
                    return
                    
                conn.sendall(request_headers.encode())
                conn.sendall(file_content)
                
                response = []
                while True:
                    data = conn.recv(2048)
                    if not data:
                        break
                    response.append(data.decode())
                    if "\r\n\r\n" in response[-1]:
                        break
                
                print("File upload response:", ''.join(response))
                
        except Exception as err:
            print(f"Server response:")

    def remove_file(self, file_name):
        payload = file_name + "\r\n"
        
        request = (
            "POST /delete HTTP/1.1\r\n"
            "Host: localhost\r\n"
            f"Content-Length: {len(payload)}\r\n"
            "\r\n"
            f"{payload}"
        )
        
        result = self.execute_request(request)
        print(f"Server response:")
        print(result)

def main():
    parser = ArgumentParser(description="HTTP Client for file operations")
    parser.add_argument("operation", choices=["list", "upload", "delete"])
    parser.add_argument("--file")

    args = parser.parse_args()
    client = FileOperations()
    
    if args.operation == "list":
        client.fetch_file_list()
    elif args.operation == "upload":
        if args.file:
            client.send_file(args.file)
    elif args.operation == "delete":
        if args.file:
            client.remove_file(args.file)
        
if __name__ == "__main__":
    main()