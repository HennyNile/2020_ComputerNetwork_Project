# Echo server program
import socket
from CN_rdt.rdt import RDTSocket


HOST = '127.0.0.1'                 # Symbolic name meaning all available interfaces
PORT = 1236              # Arbitrary non-privileged port
with RDTSocket() as s:
    s.bind((HOST, PORT))
    # s.listen(5)
    conn, addr = s.accept()
    with conn:
        print('Connected by', addr)
        while True:
            data = conn.recv(1024)
            if not data: break
            conn.sendall(data)