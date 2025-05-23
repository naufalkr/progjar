import socket
import json
import base64
import logging
import os
import random
import time

server_address = ('172.16.16.101', 6667)

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logging.warning(f"Connecting to {server_address}")
    try:
        logging.warning(f"Sending command: {command_str[:50]}...") 
        chunk_size = 8192
        for i in range(0, len(command_str), chunk_size):
            chunk = command_str[i:i+chunk_size]
            sock.sendall(chunk.encode())
        
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
        
        clean_data = data_received.split("\r\n\r\n")[0]
        return json.loads(clean_data)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return dict(status='ERROR', data=str(e))
    finally:
        sock.close()

def remote_list():
    print(f"{Colors.BLUE}[*] Retrieving file listing...{Colors.ENDC}")
    result = send_command("LIST")
    if result['status'] == 'OK':
        if not result['data']:
            print(f"\n{Colors.YELLOW}No files found on server{Colors.ENDC}")
            return
            
        print(f"{Colors.GREEN}┌{'─' * 50}┐")
        print(f"│ {Colors.BOLD}{'SERVER FILE REPOSITORY':^48}{Colors.ENDC}{Colors.GREEN} │")
        print(f"├{'─' * 50}┤")
        
        for idx, filename in enumerate(result['data'], 1):
            print(f"│ {Colors.YELLOW}{idx:3d}{Colors.ENDC} - {filename:<42} {Colors.GREEN}│")
            
        print(f"└{'─' * 50}┘{Colors.ENDC}")
        print(f"{Colors.BLUE}Total: {len(result['data'])} files{Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] Error: {result['data']}{Colors.ENDC}")

def remote_get():
    filename = input(f"{Colors.YELLOW}┌─[DOWNLOAD]─[Enter filename]\n└─➤ {Colors.ENDC}")
    if not filename:
        print(f"{Colors.RED}[!] No filename provided{Colors.ENDC}")
        return
        
    print(f"{Colors.BLUE}[*] Requesting file {filename}...{Colors.ENDC}")
    result = send_command(f"GET {filename}")
    
    if result['status'] == 'OK':
        file_data = base64.b64decode(result['data_file'])
        
        save_as = input(f"{Colors.YELLOW}┌─[SAVE AS (default: {filename})]\n└─➤ {Colors.ENDC}") or filename
        
        with open(save_as, 'wb') as f:
            f.write(file_data)
        
        file_size = len(file_data)
        if file_size < 1024:
            size_str = f"{file_size} bytes"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size/1024:.1f} KB"
        else:
            size_str = f"{file_size/(1024*1024):.1f} MB"
            
        print(f"\n{Colors.GREEN}[✓] Download complete:")
        print(f"    - Saved as: {save_as}")
        print(f"    - Size: {size_str}{Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] Download failed: {result['data']}{Colors.ENDC}")

def remote_upload():
    local_file = input(f"{Colors.YELLOW}┌─[UPLOAD]─[Local file path]\n└─➤ {Colors.ENDC}")
    
    if not os.path.exists(local_file):
        print(f"{Colors.RED}[!] File not found: {local_file}{Colors.ENDC}")
        return
        
    file_size = os.path.getsize(local_file)
    if file_size < 1024:
        size_str = f"{file_size} bytes"
    elif file_size < 1024 * 1024:
        size_str = f"{file_size/1024:.1f} KB"
    else:
        size_str = f"{file_size/(1024*1024):.1f} MB"
    
    print(f"{Colors.BLUE}[*] File size: {size_str}{Colors.ENDC}")
    
    remote_name = input(f"{Colors.YELLOW}┌─[Remote filename (default: {os.path.basename(local_file)})]\n└─➤ {Colors.ENDC}") or os.path.basename(local_file)
    
    try:
        print(f"{Colors.BLUE}[*] Uploading to server... Please wait{Colors.ENDC}")
        progress_chars = ['|', '/', '-', '\\']
        
        with open(local_file, 'rb') as f:
            file_data = base64.b64encode(f.read()).decode()
            
        padding_needed = len(file_data) % 4
        if padding_needed:
            file_data += '=' * (4 - padding_needed)
            
        command = f"UPLOAD {remote_name} {file_data}"
        result = send_command(command)
        
        if result['status'] == 'OK':
            print(f"{Colors.GREEN}[✓] {result['data']}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}[!] Upload failed: {result['data']}{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}[!] Error: {str(e)}{Colors.ENDC}")

def remote_delete():
    filename = input(f"{Colors.YELLOW}┌─[DELETE]─[Enter filename]\n└─➤ {Colors.ENDC}")
    
    if not filename:
        print(f"{Colors.RED}[!] No filename provided{Colors.ENDC}")
        return
        
    confirm = input(f"{Colors.RED}⚠ WARNING: Are you sure you want to delete '{filename}'? (y/N): {Colors.ENDC}")
    
    if confirm.lower() != 'y':
        print(f"{Colors.YELLOW}[*] Deletion canceled{Colors.ENDC}")
        return
        
    print(f"{Colors.BLUE}[*] Deleting file {filename}...{Colors.ENDC}")
    result = send_command(f"DELETE {filename}")
    
    if result['status'] == 'OK':
        print(f"{Colors.GREEN}[✓] {result['data']}{Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] Deletion failed: {result['data']}{Colors.ENDC}")

def display_help():
    box_width = 60
    title = "AVAILABLE COMMANDS"
    
    print(f"{Colors.BLUE}┌{'─' * box_width}┐")
    print(f"│ {Colors.BOLD}{title:^{box_width-2}}{Colors.ENDC}{Colors.BLUE} │")
    print(f"├{'─' * box_width}┤")
    
    commands = [
        ("list", "Show all files on server"),
        ("get", "Download a file"),
        ("upload", "Upload a file to server"),
        ("delete", "Delete a file from server"),
        ("help", "Show this help message"),
        ("exit", "Exit the application")
    ]
    
    for cmd, desc in commands:
        cmd_display = f"{Colors.GREEN}{cmd}{Colors.ENDC}"
        desc_display = f" - {desc}"
        visible_len = len(cmd) + len(desc) + 2  
        padding = box_width - 2 - visible_len   
        
        print(f"│ {cmd_display:10} - {desc}{' ' * padding}{Colors.BLUE}│")
        
    print(f"└{'─' * box_width}┘{Colors.ENDC}")

def show_banner():   
    # Display a random banner
    print(f"{Colors.YELLOW}{'─' * 80}{Colors.ENDC}")
    print(f"{Colors.GREEN}Connected to server: {Colors.BOLD}{server_address[0]}:{server_address[1]}{Colors.ENDC}")
    print(f"{Colors.YELLOW}{'─' * 80}{Colors.ENDC}")

def main_loop():
    commands = {
        'list': remote_list,
        'get': remote_get,
        'upload': remote_upload,
        'delete': remote_delete,
        'help': display_help,
    }
    
    show_banner()
    display_help()
    
    while True:
        cmd = input(f"{Colors.GREEN}fm{Colors.BLUE}@{Colors.GREEN}server{Colors.BLUE}$ {Colors.ENDC}").strip().lower()
        
        if cmd == 'exit' or cmd == 'quit':
            print(f"{Colors.YELLOW}Exiting application. Goodbye!{Colors.ENDC}")
            break
        elif cmd in commands:
            commands[cmd]()
        elif cmd == '':
            continue
        else:
            print(f"{Colors.RED}[!] Unknown command: '{cmd}'. Type 'help' for available commands.{Colors.ENDC}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    try:
        main_loop()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Program terminated by user.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {str(e)}{Colors.ENDC}")