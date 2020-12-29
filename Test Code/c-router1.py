from socket import socket, AF_INET, SOCK_DGRAM, inet_aton, inet_ntoa
import random, time
import threading, queue
from socketserver import ThreadingUDPServer

router1_address = ('127.0.0.1', 12345)
router2_address = ('127.0.0.1', 12346)


lock = threading.Lock()


def bytes_to_addr(bytes):
    return inet_ntoa(bytes[:4]), int.from_bytes(bytes[4:8], 'big')


def addr_to_bytes(addr):
    return inet_aton(addr[0]) + addr[1].to_bytes(4, 'big')


class Router1(ThreadingUDPServer):
    def __init__(self, addr, rate=None, delay=None):
        super().__init__(addr, None)
        self.rate = rate
        self.buffer = 0
        self.delay = delay
        self.next_hop = ('127.0.0.1', 12346)

    def verify_request(self, request, client_address):
        """
        request is a tuple (data, socket)
        data is the received bytes object
        socket is new socket created automatically to handle the request

        if this function returns False， the request will not be processed, i.e. is discarded.
        details: https://docs.python.org/3/library/socketserver.html
        """
        if self.buffer < 100000:  # some finite buffer size (in bytes)
            self.buffer += len(request[0])
            return True
        else:
            return False

    def finish_request(self, request, client_address):
        data, socket = request

        with lock:
            if self.rate: time.sleep(len(data) / self.rate)
            self.buffer -= len(data)
            loss_rate = 0.07
            corrupt_rate = 0.05
            if random.random() < loss_rate:
                return
            for i in range(len(data) - 1):
                if random.random() < corrupt_rate:
                    data[i] = data[:i] + (data[i] + 1).to_bytes(1, 'big') + data[i + 1:]
            """
            blockingly process each request
            you can add random loss/corrupt here

            for example:
            if random.random() < loss_rate:
                return 
            for i in range(len(data)-1):
                if random.random() < corrupt_rate:
                    data[i] = data[:i] + (data[i]+1).to_bytes(1,'big) + data[i+1:]
            """

        """
        this part is not blocking and is executed by multiple threads in parallel
        you can add random delay here, this would change the order of arrival at the receiver side.

        for example:
        time.sleep(random.random())
        """

        to = bytes_to_addr(data[:8])
        print(client_address, to)  # observe the traffic
        socket.sendto(addr_to_bytes(client_address) + data[8:], self.next_hop)

class Router2(ThreadingUDPServer):
    def __init__(self, addr, rate=None, delay=None):
        super().__init__(addr, None)
        self.rate = rate
        self.buffer = 0
        self.delay = delay

    def verify_request(self, request, client_address):
        """
        request is a tuple (data, socket)
        data is the received bytes object
        socket is new socket created automatically to handle the request

        if this function returns False， the request will not be processed, i.e. is discarded.
        details: https://docs.python.org/3/library/socketserver.html
        """
        if self.buffer < 100000:  # some finite buffer size (in bytes)
            self.buffer += len(request[0])
            return True
        else:
            return False

    def finish_request(self, request, client_address):
        data, socket = request
        data_out = b''
        if client_address == ('127.0.0.1','13001'):
            self.rate = 10240
        with lock:
            if self.rate: time.sleep(len(data) / self.rate)
            self.buffer -= len(data)
            loss_rate = 0.07
            corrupt_rate = 0.05
            if random.random() < loss_rate:
                return
            for i in range(len(data) - 1):
                if random.random() < corrupt_rate:
                    data_out += data[:i] + (data[i] + 1).to_bytes(1, 'big') + data[i + 1:]
            """
            blockingly process each request
            you can add random loss/corrupt here

            for example:
            if random.random() < loss_rate:
                return 
            for i in range(len(data)-1):
                if random.random() < corrupt_rate:
                    data[i] = data[:i] + (data[i]+1).to_bytes(1,'big) + data[i+1:]
            """

        """
        this part is not blocking and is executed by multiple threads in parallel
        you can add random delay here, this would change the order of arrival at the receiver side.

        for example:
        time.sleep(random.random())
        """

        to = bytes_to_addr(data[:8])
        print(client_address, to)  # observe the traffic
        socket.sendto(addr_to_bytes(client_address) + data[8:], to)





if __name__ == '__main__':
    with Router1(router1_address,rate=10240*2) as router1:
        print("------router1 working------")
        router1.serve_forever()