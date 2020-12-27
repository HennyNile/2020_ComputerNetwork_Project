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
        data = conn.recv(4096)
        print("Socket",thread_id,"Received a message")
        if not data:
            print("Receive finished!")
            break
        #print(UnpackRDTMessage(data)[8].decode()[0:100])
        #alice1.write(UnpackRDTMessage(data)[8].decode())
        #print(data.decode())
        alice1.write(data.decode())


alice1 = open("alice1.txt","w+")


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
