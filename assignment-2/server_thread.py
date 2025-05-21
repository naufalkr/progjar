from socket import *
import socket
import threading
import logging
import time
import sys
from datetime import datetime

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        rcv = ""
        logging.warning(f"Client thread started for {self.address}")
        while True:
            data = self.connection.recv(32)
            if data:
                d = data.decode('utf-8')
                rcv = rcv + d
                logging.warning(f"received data: {repr(rcv)}")
                
                if rcv.startswith("TIME") and (rcv.endswith("\r\n") or rcv.endswith("\n")):
                    now = datetime.now()
                    waktu = now.strftime("%H:%M:%S")
                    response = f"JAM {waktu}\r\n"
                    logging.warning(f"sending response: {repr(response)}")
                    self.connection.sendall(response.encode('utf-8'))
                    rcv = ""
                elif rcv.startswith("QUIT") and (rcv.endswith("\r\n") or rcv.endswith("\n")):
                    logging.warning(f"Client {self.address} requested QUIT")
                    response = "Goodbye!\r\n"
                    self.connection.sendall(response.encode('utf-8'))
                    self.connection.close()
                    return  
                elif rcv.endswith("\r\n") or rcv.endswith("\n"):
                    response = "Invalid request format\r\n"
                    logging.warning(f"sending invalid response: {repr(response)}")
                    self.connection.sendall(response.encode('utf-8'))
                    rcv = ""
            else:
                logging.warning(f"Client {self.address} closed connection")
                break
        self.connection.close()

class Server(threading.Thread):
    def __init__(self):
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread.__init__(self)

    def run(self):
        self.my_socket.bind(('0.0.0.0', 45000))
        self.my_socket.listen(1)
        while True:
            self.connection, self.client_address = self.my_socket.accept()
            logging.warning(f"connection from {self.client_address}")
            
            clt = ProcessTheClient(self.connection, self.client_address)
            clt.start()
            self.the_clients.append(clt)

def main():
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(message)s')
    svr = Server()
    svr.start()

if __name__ == "__main__":
    main()