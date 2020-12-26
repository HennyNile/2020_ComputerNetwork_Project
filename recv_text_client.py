# Echo server program
from CN_rdt.rdt import RDTSocket
from CN_rdt.utils import CreateRDTMessage,UnpackRDTMessage


client_addr = ('127.0.0.1',13001)         # Symbolic name meaning all available interfaces
# client_port = 12000              # Arbitrary non-privileged port
server_addr = ('127.0.0.1',1236)
data = "abcdefghijklmnopqrstuvwxyz123456789456123"
with RDTSocket() as s:
    s.bind(client_addr)
    #print(s.getsockname())
    if s.connect(server_addr):
        print("Connect_socket",s.dest_addr)
        while True:
            t_message = input()
            print("sending message:",t_message)
            if t_message == "exit": break
            if t_message == "close": s.close()
            else:
                s.simple_send(data)
                # message = s.recv(1024)
                # print("Client recv:",message)
                # package = CreateRDTMessage(Payload=t_message)
                # s.sendto(package,s.dest_addr)
            # r_message = UnpackRDTMessage(s.recv(1024))
            # print(r_message)
    else:
        print("No return value")

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