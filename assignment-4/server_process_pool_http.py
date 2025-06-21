from socket import *
import socket
import time
import sys
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from http import HttpServer

httpserver = HttpServer()

#untuk menggunakan processpoolexecutor, karena tidak mendukung subclassing pada process,
#maka class ProcessTheClient dirubah dulu menjadi function, tanpda memodifikasi behaviour didalamnya


def ProcessTheClient(connection, address):
    rcv_bytes = b""  
    
    while True:
        try:
            data = connection.recv(1024)
            if data:
            	#merubah input dari socket (berupa bytes) ke dalam string
				#agar bisa mendeteksi \r\n
                rcv_bytes += data
                
                if b'\r\n\r\n' in rcv_bytes:
                    header_end = rcv_bytes.find(b'\r\n\r\n') + 4
                    header_part = rcv_bytes[:header_end].decode('utf-8', errors='ignore')
                    
                    content_length = 0
                    for line in header_part.split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            content_length = int(line.split(':')[1].strip())
                            break
                    
                    if content_length > 0:
                        body_received = len(rcv_bytes) - header_end
                        if body_received < content_length:
                            continue
                    
                    hasil = httpserver.proses(rcv_bytes)
                    hasil = hasil + b"\r\n\r\n"
                    connection.sendall(hasil)
                    break
                    
            else:
                break
                
        except OSError as e:
            break
    
    connection.close()
    return

def Server():
    the_clients = []
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        my_socket.bind(('0.0.0.0', 8889))
        my_socket.listen(1)
        
        with ProcessPoolExecutor(20) as executor:
            while True:
                try:
                    connection, client_address = my_socket.accept()
                    #logging.warning("connection from {}".format(client_address))
                    p = executor.submit(ProcessTheClient, connection, client_address)
                    the_clients.append(p)
                    #menampilkan jumlah process yang sedang aktif
                    jumlah = ['x' for i in the_clients if i.running()==True]
                    print(jumlah)
                except KeyboardInterrupt:
                    print("Server shutdown...")
                    break
    except Exception as e:
        print(f"Error starting server: {e}")
    finally:
        my_socket.close()

def main():
    Server()

if __name__=="__main__":
    main()

