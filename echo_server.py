# Echo server program
import socket
from rdt import RDTSocket
from utils import CreateRDTMessage,UnpackRDTMessage
import threading
import time


class socketThreading(threading.Thread):
    def __init__(self,id,conn):
        threading.Thread.__init__(self)
        self.id = id
        self.conn = conn

    def run(self):
        socketCommunicate(conn,id);

def socketCommunicate(conn,thread_id):
    while True:
        data = conn.recv(1024)
        print("Socket",thread_id,"Received:", UnpackRDTMessage(data)[8].decode())
        if not data: break
    # conn.sendall(data)

HOST = '127.0.0.1'                 # Symbolic name meaning all available interfaces
PORT = 1236              # Arbitrary non-privileged port
with RDTSocket() as s:
    s.bind((HOST, PORT))
    # s.listen(5)
    id = 1
    while True:
        conn,addr = s.accept()
        print('Connected by', addr)
        print("new sock is", conn.getsockname())
        thread = socketThreading(id,conn)
        thread.start()
        id += 1
