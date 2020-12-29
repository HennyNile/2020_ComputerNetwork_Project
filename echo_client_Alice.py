# Echo server program
from CN_rdt.rdt import RDTSocket
from CN_rdt.utils import CreateRDTMessage,UnpackRDTMessage
import os

buf = bytearray(os.path.getsize("alice.txt"))
alice = open("alice.txt",'rb')
alice.readinto(buf)



client_addr = ('127.0.0.1',13001)         # Symbolic name meaning all available interfaces
# client_port = 12000              # Arbitrary non-privileged port
server_addr = ('127.0.0.1',1236)
with RDTSocket() as s:
    s.bind(client_addr)
    #print(s.getsockname())
    if s.connect(server_addr):
        print("Connect_socket",s.dest_addr)
        s.send(buf)

    # # s.listen(5)
    # conn, addr = s.accept()
    # with conn:
    #     print('Connected by', addr)
    #     while True:
    #         print("hello")
    #         data = conn.recv(1024)
    #         print("hello")
    #         if not data: break
    #         conn.sendall(data)
