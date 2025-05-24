import socket
import json
import base64
import logging
import time
import struct
import os

server_address=('172.16.16.101', 8889)

# Configure socket buffer sizes
SOCKET_BUFFER_SIZE = 256 * 1024 * 1024  # 256MB buffer (balanced size)
CHUNK_SIZE = 256 * 1024 * 1024  # 256MB chunks for file transfer

def send_command(command_str="", binary_data=None):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Optimize socket settings
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, struct.pack('i', SOCKET_BUFFER_SIZE))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, struct.pack('i', SOCKET_BUFFER_SIZE))
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    # Enable TCP keepalive
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    # Set TCP keepalive parameters
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
    
    sock.connect(server_address)
    logging.warning(f"connecting to {server_address}")
    try:
        # Send command length first (4 bytes)
        command_bytes = command_str.encode()
        command_length = len(command_bytes)
        sock.sendall(struct.pack('!I', command_length))
        
        # Send command
        sock.sendall(command_bytes)
        
        # If there's binary data to send
        if binary_data:
            # Send binary data length
            data_length = len(binary_data)
            sock.sendall(struct.pack('!I', data_length))
            # Send binary data in chunks
            total_sent = 0
            while total_sent < data_length:
                sent = sock.send(binary_data[total_sent:total_sent + CHUNK_SIZE])
                if sent == 0:
                    raise RuntimeError("Socket connection broken")
                total_sent += sent
            
        # Look for the response
        data_received = b""
        while True:
            chunk = sock.recv(SOCKET_BUFFER_SIZE)
            if chunk:
                data_received += chunk
                if b"\r\n\r\n" in data_received:
                    break
            else:
                break
                
        hasil = json.loads(data_received.decode())
        logging.warning("data received from server:")
        return hasil
    except Exception as e:
        logging.warning(f"error during data receiving: {str(e)}")
        return False
    finally:
        sock.close()

def remote_list():
    command_str = "LIST"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print("daftar file : ")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print("Gagal")
        return False

def remote_get(filename=""):
    command_str = f"GET {filename}"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        namafile = hasil['data_namafile']
        # Decode base64 string back to binary
        isifile = base64.b64decode(hasil['data_file'])
        with open(namafile, 'wb') as fp:
            fp.write(isifile)
        return True
    else:
        print("Gagal")
        return False

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
            # Encode to base64 in chunks to reduce memory usage
            file_content_b64 = base64.b64encode(file_content).decode()
        
        # Convert base64 string back to binary for sending
        binary_data = file_content_b64.encode()
        
        # Send command and binary data
        command_str = f"UPLOAD {filename}"
        hasil = send_command(command_str, binary_data)
        if (hasil['status']=='OK'):
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
    if (hasil['status']=='OK'):
        print(f"File {filename} berhasil dihapus")
        return True
    else:
        print(f"Gagal menghapus: {hasil['data']}")
        return False

if __name__=='__main__':
    server_address=('172.16.16.101', 8889)
    remote_list()
    remote_upload('test.txt')
    remote_list()