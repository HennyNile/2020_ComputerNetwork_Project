from rdt import RDTSocket
import time

if __name__=='__main__':
    server = RDTSocket()
    server.bind(('127.0.0.1', 9999))

    while True:
        conn, client_addr = server.accept()
        start = time.perf_counter()
        while True:
            if len(conn.recv_buffer) > 0:
                buffer = []
                for i in range(len(conn.recv_buffer)):
                    buffer.append(conn.recv_buffer[i][0])
                print("recv_buffer of server is",buffer)
            else:
                print("recv_buffer of server is empty.")
            data = conn.recv(4096)
            if data:
                conn.send(data)
            else:
                break
        '''
        make sure the following is reachable
        '''
        conn.close()
        print(f'connection finished in {time.perf_counter()-start}s')