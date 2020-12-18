from USocket import UnreliableSocket
import utils as utils

port_pool = [(12000+ _) for _ in range(1000)]
port_pool_flag = [0 for _ in range(1000)]
sockets = {}

# Package Header
#######################################################
# 0SYN 1FIN 2ACK 3BLANK 4SEQ 5SEQ_ACK 6LEN 7CHECKSUM 8PAYLOAD
#######################################################
syn_sent_h = (True, False, False)
syn_recv_h = (True, False, True)
est_conn_h = (False, False, True)
fin_sent_h = (False, True, True) # ACK for latest received pkg
fin_recv_h = (False, False, True)  # ACK for fin_sent


def check_package(package, package_type):
    # package_type
    # 0: syn_sent
    # 1: syn_recv
    # 2: est_conn
    # 3: communication
    # 4: fin_sent
    # 5: fin_recv
    if not utils.getCheckSum(package) == 0:
        print("+++Invalid package: Wrong checksum!")
        return False
    package_msg = utils.UnpackRDTMessage(package)
    if package_type == 0 and not package_msg[0:3] == syn_sent_h:
        print("+++SYN_SENT Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 1 and not package_msg[0:3] == syn_recv_h:
        print("+++SYN_RECV Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 2 and not package_msg[0:3] == est_conn_h :
        print("+++EST_CONN Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 3:
        return False
    if package_type == 4 and not package_msg[0:3] == fin_sent_h:
        return False
    if package_type == 5 and not package_msg[0:3] == fin_recv_h:
        return False
    if package_type <0 or package_type > 5 :
        print("+++Invalid package type:",package_type)
        return False
    return True



class RDTSocket(UnreliableSocket):
    """
    The functions with which you are to build your RDT.
    -   recvfrom(bufsize)->bytes, addr
    -   sendto(bytes, address)
    -   bind(address)

    You can set the mode of the socket.
    -   settimeout(timeout)
    -   setblocking(flag)
    By default, a socket is created in the blocking mode. 
    https://docs.python.org/3/library/socket.html#socket-timeouts

    """

    def __init__(self, rate=None, debug=True):
        super().__init__(rate=rate)
        self._rate = rate
        self._send_to = None
        self._recv_from = None
        self.debug = debug
        #############################################################################
        # TODO: ADD YOUR NECESSARY ATTRIBUTES HERE
        #############################################################################
        # package unpacking format
        self.seq_ack = None
        self.seq = 0
        self.dest_addr = None
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def accept(self) -> ("RDTSocket", (str, int)):
        """
        Accept a connection. The socket must be bound to an address and listening for 
        connections. The return value is a pair (conn, address) where conn is a new 
        socket object usable to send and receive data on the connection, and address 
        is the address bound to the socket on the other end of the connection.

        This function should be blocking. 
        """
        conn, addr = RDTSocket(self._rate), None
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        print("------- listening for connection request -------")
        self._send_to = self.sendto
        self._recv_from = self.recvfrom

        # Listen for Connection request
        syn_sent, client_addr = self.recvfrom(1024)
        print("1.Received a connection request...")
        self.dest_addr = client_addr
        if not check_package(syn_sent, 0):
            self.dest_addr = None
            return conn, addr
        syn_sent_upk = utils.UnpackRDTMessage(syn_sent)
        self.seq_ack = syn_sent_upk[4] + 1

        # Send syn_recv to client
        newport = 0
        for i in range(1000):
            if port_pool_flag[i] == 0:
                newport = port_pool[i]
                port_pool_flag[i]= 1
                break
        newsockaddr = "127.0.0.1,"+str(newport)
        syn_recv = utils.CreateRDTMessage(SYN=syn_recv_h[0], FIN=syn_recv_h[1], ACK=syn_recv_h[2], SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack, Payload=newsockaddr)
        #print(syn_recv)
        #print("test1")
        self.send(syn_recv)
        #print("test2")
        print("2.SYN_RECV is sent.")

        # Establish connection
        est_conn, client_addr = self.recvfrom(1024)
        if not client_addr == self.dest_addr:
            print("+++EST_CONN Failed\n+++Invalid package: Wrong client!")
            self.dest_addr = None
            return conn,addr
        est_conn_upk = utils.UnpackRDTMessage(est_conn)
        if not check_package(est_conn, 2):
            self.dest_addr = None
            return conn,addr
        if not est_conn_upk[5] == self.seq + 1:
            print("+++EST_CONN Failed\n+++Invalid package: Wrong sqe_ack!")
            self.dest_addr = None
            return conn,addr
        self.seq += 1
        self.seq_ack = est_conn_upk[4] + est_conn_upk[6]
        print("3.Connection established.")

        conn.bind(("127.0.0.1",newport))
        addr = self.dest_addr
        conn.dest_addr = self.dest_addr
        conn._send_to = conn.sendto
        conn._recv_from = conn.recvfrom
        self.dest_addr = None
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return conn, addr

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        self._send_to = self.sendto
        self._recv_from = self.recvfrom

        # Send SYN_SENT
        syn_sent = utils.CreateRDTMessage(syn_sent_h[0], syn_sent_h[1], syn_sent_h[1], SEQ=self.seq, SEQ_ACK=0,Payload='')
        self.dest_addr = address
        self.send(syn_sent)
        print("1.SYN_SENT is sent.")

        # listen for SYN_RECV
        syn_recv, server_addr = self.recvfrom(1024)

        #print(syn_recv)
        if not check_package(syn_recv,1):
            self.dest_addr = None
            return False
        syn_recv_upk = utils.UnpackRDTMessage(syn_recv)
        if not syn_recv_upk[5] == self.seq + 1:
            print("+++SYN_RECV Failed\n+++Invalid package: Wrong seq_ack!")
            self.dest_addr = None
            return False
        self.seq += 1
        self.seq_ack = syn_recv_upk[4] + 1
        newsockaddr = syn_recv_upk[8].decode().split(',')
        newsockaddr = (newsockaddr[0],int(newsockaddr[1]))
        print("2.SYN_RECV is right.")

        # ESTABLISH CONNECTION
        est_conn = utils.CreateRDTMessage(est_conn_h[0], est_conn_h[1], est_conn_h[2], SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack, Payload='')
        self.send(est_conn)
        self.dest_addr = newsockaddr
        print("Connected!")
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return True

    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket. 
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        data = None
        assert self._recv_from is not None, "Connection not established yet. Use recvfrom instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        temdata, addr = self.recvfrom(bufsize=bufsize)
        while not addr == self.dest_addr:
           temdata, addr = self.recvfrom(bufsize=bufsize)
        data = temdata
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        #print("another hello again")
        return data

    def send(self, bytes: bytes):
        """
        Send data to the socket. 
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        assert self._send_to is not None, "Connection not established yet. Use sendto instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        self.sendto(bytes,self.dest_addr)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither further sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        # FIN_SENT
        fin_sent = utils.CreateRDTMessage(fin_sent_h[0], fin_sent_h[1], fin_sent_h[2], SEQ=self.seq, SEQ_ACK=0,Payload='')
        self.send(fin_sent)
        print("1.Close request is sent.")

        # FIN_RECV
        fin_recv, addr = self.recv(1024)
        fin_recv_upk = utils.UnpackRDTMessage(fin_recv)
        if not check_package(fin_recv, 5):
            self.close()
        else:
            if not fin_recv_upk[5] == self.seq + fin_sent[6]:
                self.close()
        print("2.Close is agreed.")
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        super().close()

    def set_send_to(self, send_to):
        self._send_to = send_to

    def set_recv_from(self, recv_from):
        self._recv_from = recv_from

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""

if __name__ == '__main__':
    clientAddress = ('127.0.0.1', 11111)
    serverAddress = ('127.0.0.1', 1236)
    payload = ''
    # Create a client socket
    clientSocket = RDTSocket()
    clientSocket.bind(clientAddress)
    # Create a connection request message
    clientSocket.connect(serverAddress)
    clientSocket.connect(serverAddress)
    # connMsg = utils.CreateRDTMessage(SYN=True,FIN=False,ACK=False,SEQ=0,SEQ_ACK=0,Payload=payload)
    # sendTo = clientSocket.sendto
    # sendTo(connMsg,clientAddress)
    # connRsp, serverAddr = clientSocket.recvfrom(1024)
    # fmt = "<3?3ih%ds" % len(payload)
    # print(struct.unpack(fmt, connRsp))
