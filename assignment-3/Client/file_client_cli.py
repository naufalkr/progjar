import socket
import json
import base64
import logging
import os

server_address = ('172.16.16.101', 8889)  # Default server address

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logging.warning(f"connecting to {server_address}")
    try:
        # Make sure command ends with \r\n
        if not command_str.endswith("\r\n"):
            command_str += "\r\n"
            
        logging.warning(f"Sending command: {command_str.strip()}")
        sock.sendall(command_str.encode())
        
        # Wait for response
        data_received = ""
        while True:
            data = sock.recv(8192)
            if data:
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
        
        # Extract JSON response before the end marker
        if data_received:
            clean_data = data_received.split("\r\n\r\n")[0]
            hasil = json.loads(clean_data)
            logging.warning("data received from server:")
            return hasil
        else:
            return dict(status='ERROR', data='No data received from server')
    except Exception as e:
        logging.warning(f"error during data receiving: {str(e)}")
        return False
    finally:
        sock.close()

def remote_upload(filename=""):
    try:
        # Get full path of the file in the files directory
        filepath = os.path.join("./files", filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            print(f"File {filename} tidak ditemukan di direktori files")
            return False
            
        # Read file content in binary mode and encode to base64
        with open(filepath, 'rb') as fp:
            file_content = fp.read()
            file_content_b64 = base64.b64encode(file_content).decode()
        
        command_str = f"UPLOAD {filename} {file_content_b64}"
        hasil = send_command(command_str)
        
        if hasil['status'] == 'OK':
            print(f"File {filename} berhasil diupload")
            return True
        else:
            print(f"Gagal upload: {hasil['data']}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def remote_delete(filename=""):
    command_str = f"DELETE {filename}"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print(f"File {filename} berhasil dihapus")
        return True
    else:
        print(f"Gagal menghapus: {hasil['data']}")
        return False

def show_menu():
    print("\n===== File Server Client =====")
    print("1. Upload file")
    print("2. Delete file")
    print("3. Exit")
    print("4. Change server address")
    return input("Select option (1-4): ")

def change_server_address():
    global server_address
    ip = input("Enter server IP (default 172.16.16.101): ") or "172.16.16.101"
    try:
        port = int(input("Enter server port (default 8889): ") or "8889")
        server_address = (ip, port)
        print(f"Server address changed to {server_address}")
    except ValueError:
        print("Invalid port number. Using default 8889")
        server_address = (ip, 8889)

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    print("File Client CLI started")
    print(f"Default server: {server_address}")
    
    while True:
        choice = show_menu()
        if choice == '1':
            filepath = input("Enter local file path: ")
            filename = os.path.basename(filepath)
            remote_upload(filename)
        elif choice == '2':
            filename = input("Enter filename to delete: ")
            remote_delete(filename)
        elif choice == '3':
            print("Exiting...")
            break
        elif choice == '4':
            change_server_address()
        else:
            print("Invalid option")