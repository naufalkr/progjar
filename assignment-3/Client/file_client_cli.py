import socket
import json
import base64
import logging
import os

server_address = ('172.16.16.101', 6667)

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logging.warning(f"Connecting to {server_address}")
    try:
        logging.warning(f"Sending command: {command_str[:50]}...")  # Log truncated command
        # Send the command in chunks to handle large data
        chunk_size = 8192
        for i in range(0, len(command_str), chunk_size):
            chunk = command_str[i:i+chunk_size]
            sock.sendall(chunk.encode())
        
        # Add a small delay to ensure all data is sent
        import time
        time.sleep(0.1)
        
        data_received = ""
        while True:
            data = sock.recv(8192)
            if data:
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
        
        # Remove the end marker
        clean_data = data_received.split("\r\n\r\n")[0]
        return json.loads(clean_data)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return dict(status='ERROR', data=str(e))
    finally:
        sock.close()

def remote_list():
    result = send_command("LIST")
    if result['status'] == 'OK':
        print("\nFile list:")
        for idx, filename in enumerate(result['data'], 1):
            print(f"{idx}. {filename}")
    else:
        print(f"Error: {result['data']}")

def remote_get():
    filename = input("Enter filename to download: ")
    result = send_command(f"GET {filename}")
    if result['status'] == 'OK':
        file_data = base64.b64decode(result['data_file'])
        with open(filename, 'wb') as f:
            f.write(file_data)
        print(f"File {filename} downloaded successfully")
    else:
        print(f"Error: {result['data']}")

def remote_upload():
    local_file = input("Enter local file path: ")
    remote_name = input("Enter remote filename: ")
    try:
        with open(local_file, 'rb') as f:
            file_data = base64.b64encode(f.read()).decode()
        # Make sure the file_data has proper padding
        padding_needed = len(file_data) % 4
        if padding_needed:
            file_data += '=' * (4 - padding_needed)
            
        command = f"UPLOAD {remote_name} {file_data}"
        result = send_command(command)
        print(result['data'])
    except Exception as e:
        print(f"Error: {str(e)}")

def remote_delete():
    filename = input("Enter filename to delete: ")
    result = send_command(f"DELETE {filename}")
    print(result['data'])

def show_menu():
    print("\n===== File Server Client =====")
    print("1. List files")
    print("2. Download file")
    print("3. Upload file")
    print("4. Delete file")
    print("5. Exit")
    return input("Select option (1-5): ")

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    while True:
        choice = show_menu()
        if choice == '1':
            remote_list()
        elif choice == '2':
            remote_get()
        elif choice == '3':
            remote_upload()
        elif choice == '4':
            remote_delete()
        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("Invalid option")