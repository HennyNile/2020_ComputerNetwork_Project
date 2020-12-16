from CN_rdt.USocket import UnreliableSocket
import CN_rdt.utils as utils
import threading
import time
import struct

# Package Header
#######################################################
# 0SYN 1FIN 2ACK 3BLANK 4SEQ 5SEQ_ACK 6LEN 7CHECKSUM 8PAYLOAD
#######################################################
syn_sent_h = [True, False, False]
syn_recv_h = [True, False, True]
est_conn_h = [False, False, True]
fin_sent_h = [False, True, True]  # ACK for latest received pkg
fin_recv_h = [False, False, True]  # ACK for fin_sent


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
        print("-------server on-------")
        # self = connection socket
        sendTo = self.sendto
        # GET SYN_SENT
        syn_sent, client_addr = self.recvfrom(1024)
        while (1):
            syn_sent_upk = utils.UnpackRDTMessage(syn_sent)
            print("server gets syn_sent:", syn_sent_upk)
            print("syn_sent_upk:",syn_sent_upk)
            assert syn_sent_upk[0] == True, "SYN_SENT has no SYN flag, establish connection first!"
            assert utils.getCheckSum(syn_sent) == 0, "Corrupt SYN SENT data!"
            break
        # SYN_RECV
        self.seq_ack = syn_sent_upk[4] + 1
        syn_recv = utils.CreateRDTMessage(SYN=syn_recv_h[0], FIN=syn_recv_h[1], ACK=syn_recv_h[2], SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack, Payload='')
        sendTo(syn_recv, client_addr)
        # ESTABLISH CONNECTION
        est_conn, client_addr = self.recvfrom(1024)
        est_conn_upk = utils.UnpackRDTMessage(est_conn)
        print("server gets est_conn:", est_conn_upk)
        assert est_conn_upk[5] == self.seq + 1, "Establish package does not increment seq_ack!"
        assert utils.getCheckSum(est_conn) == 0, "Corrupt SYN RECV data!"
        self.seq += 1
        self.seq_ack = est_conn_upk[4] + est_conn_upk[6]
        # temporarily super sendto, super recvfrom
        self._send_to = self.sendto
        self._recv_from = self.recvfrom
        # return conn,addr
        conn.bind(('127.0.0.1', 1235))
        addr = client_addr
        # set socket's dest_addr
        self.dest_addr = client_addr
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
        # SYN_SENT
        syn_sent = utils.CreateRDTMessage(syn_sent_h[0], syn_sent_h[1], syn_sent_h[1], SEQ=self.seq, SEQ_ACK=0,
                                          Payload='')
        sendTo = self.sendto
        sendTo(syn_sent, address)
        # SYN_RECV
        syn_recv, server_addr = self.recvfrom(1024)
        syn_recv_upk = utils.UnpackRDTMessage(syn_recv)
        print("client gets syn_recv:", syn_recv_upk)
        #   verify field:SYN, CHECKSUM, SEQ
        assert syn_recv_upk[0] == True, "SYN_RECV has no SYN flag!"
        assert syn_recv_upk[2] == True, "SYN_RECV has no ACK flag!"
        assert utils.getCheckSum(syn_recv) == 0, "Corrupt SYN RECV data!"
        assert syn_recv_upk[5] == self.seq + 1, "SYN_RECV does not increment seq_ack!"
        #   update field:SEQ=x+syn_sent len, SEQ_ACK=y+len
        self.seq += 1
        self.seq_ack = syn_recv_upk[4] + 1
        # ESTABLISH CONNECTION
        est_conn = utils.CreateRDTMessage(est_conn_h[0], est_conn_h[1], est_conn_h[2], SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack, Payload='')
        sendTo(est_conn, address)
        # temporarily super sendto, super recvfrom
        self._send_to = self.sendto
        self._recv_from = self.recvfrom
        # set socket's dest_addr
        self.dest_addr = address
        # raise NotImplementedError()
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

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
        assert self._recv_from is None, "Connection not established yet. Use recvfrom instead."
        self.recvfrom(bufsize=bufsize)
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return data

    def send(self, bytes: bytes):
        """
        Send data to the socket. 
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        assert self._send_to is None, "Connection not established yet. Use sendto instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        raise NotImplementedError()
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither further sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        # FIN_SENT
        fin_sent = utils.CreateRDTMessage(fin_sent_h[0], fin_sent_h[1], fin_sent_h[1], SEQ=self.seq, SEQ_ACK=0,
                                          Payload='')
        fin_sent_upk = utils.UnpackRDTMessage(fin_sent)
        sendTo = self.sendto
        sendTo(fin_sent, self.dest_addr)
        # FIN_RECV
        fin_recv, addr = self.recvfrom(1024)
        fin_recv_upk = utils.UnpackRDTMessage(fin_recv)
        print("client gets syn_recv:", fin_recv_upk)
        #   verify field:SYN, CHECKSUM, SEQ
        assert fin_recv_upk[2] == True, "FIN_RECV has no ACK flag!"
        assert utils.getCheckSum(fin_recv) == 0, "Corrupt FIN RECV data!"
        assert fin_recv_upk[5] == self.seq + fin_sent[6], "FIN_RECV does not increment seq_ack!"
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
    # connMsg = utils.CreateRDTMessage(SYN=True,FIN=False,ACK=False,SEQ=0,SEQ_ACK=0,Payload=payload)
    # sendTo = clientSocket.sendto
    # sendTo(connMsg,clientAddress)
    # connRsp, serverAddr = clientSocket.recvfrom(1024)
    # fmt = "<3?3ih%ds" % len(payload)
    # print(struct.unpack(fmt, connRsp))
