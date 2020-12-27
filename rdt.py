from USocket import UnreliableSocket
import utils as utils
import threading
import time
import heapq

port_pool = [(12000+ _) for _ in range(1000)]
port_pool_flag = [0 for _ in range(1000)]

# Package Header
#######################################################
# 0SYN 1FIN 2ACK 3BLANK 4SEQ 5SEQ_ACK 6LEN 7CHECKSUM 8PAYLOAD
#######################################################
syn_h = 0
fin_h = 1
ack_h = 2
seq_h = 4
seq_ack_h = 5
len_h = 6
checksum_h = 7
payload_h = 8
syn_sent_h = (True, False, False)
syn_recv_h = (True, False, True)
est_conn_h = (False, False, True)
fin_sent_h = (False, True, True) # ACK for latest received pkg
fin_ack_h = (False, False, True)  # ACK for fin_sent
fin_recv_ack_h = (False,False,True)

class recvThreading(threading.Thread):
    def __init__(self, rdt):
        threading.Thread.__init__(self)
        self.buffer = None
        self.rdt = rdt
        self.thread_running = False

    def run(self):
        buffer,addr = self.rdt.recvfrom(4096)
        print((time.time() * 1000) % 1000)
        print("receive an unkown package in thread", utils.UnpackRDTMessage(buffer)[0:8])
        self.thread_running = True
        if check_package(buffer, 3) :
            package = utils.UnpackRDTMessage(buffer)
            if package[6]>0:
                print("receive an message in thread", utils.UnpackRDTMessage(buffer)[0:8])
                if len(self.rdt.recv_buffer) == 0:
                    self.rdt.recv_buffer = [(package[4],buffer)]
                else:
                    posi = 0
                    for i in range(len(self.rdt.recv_buffer)):
                        if self.rdt.recv_buffer[i][0] < package[4]:
                            posi = i
                    self.rdt.recv_buffer = self.rdt.recv_buffer[0:posi+1] + [(package[4], buffer)] + self.rdt.recv_buffer[
                                                posi+1:len(self.rdt.recv_buffer)]
                ack_package = utils.CreateRDTMessage(SYN=False, FIN=False, ACK=True, SEQ=self.rdt.seq,
                                                     SEQ_ACK=package[4]+package[6])
                self.rdt.sendto(ack_package, self.rdt.dest_addr)
                self.thread_running = False
                self.run()
            else:
                self.buffer = buffer
        self.thread_running = False

    def get_thread_running(self):
        return self.thread_running

class Package(object):
    def __init__(self, pkg):
        self.pkg = pkg
    def __lt__(self, other):
        return self.pkg[seq_h] < other.pkg[seq_h]
    def getPkg(self):
        return self.pkg

def check_package(package, package_type):
    # package_type
    # 0: syn_sent
    # 1: syn_recv
    # 2: est_conn
    # 3: communication
    # 4: fin_sent
    # 5: fin_recv
    # 6: fin_recv_ack
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
    if package_type == 3 and not package_msg[0:3] == est_conn_h:
        print("+++Communicate mistakes\n+++Invalid package: Wrong header!")
        return False
    if package_type == 4 and not package_msg[0:3] == fin_sent_h:
        print("+++FIN_SENT Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 5 and not package_msg[0:3] == fin_ack_h:
        print("+++FIN_RECV Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 6 and not package_msg[0:3] == fin_recv_ack_h:
        print("+++FIN_RECV_ACK Failed\n+++Invalid package: Wrong header!")
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
        self.seq_ack = 0
        self.seq = 0
        self.dest_addr = None
        self.recv_buffer = []
        self.maxwinsize = 5
        self.maxmessagelen = 3000
        self.timeout = 2
        self.this_fin = True
        self.this_fin_seq = None

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
        syn_sent, client_addr = self.recvfrom(4096)
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
                port_pool_flag[i] = 1
                break
        newsockaddr = "127.0.0.1,"+str(newport)
        syn_recv = utils.CreateRDTMessage(SYN=syn_recv_h[0], FIN=syn_recv_h[1], ACK=syn_recv_h[2], SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack, Payload=newsockaddr)
        self.sendto(syn_recv,self.dest_addr)
        print("2.SYN_RECV is sent.")

        # Establish connection
        est_conn, client_addr = self.recvfrom(4096)
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
        conn.seq = 1
        conn.seq_ack = 1
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
        #print(self.dest_addr)
        self.sendto(syn_sent,self.dest_addr)
        print("1.SYN_SENT is sent.")

        # listen for SYN_RECV
        syn_recv, server_addr = self.recvfrom(4096)

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
        self.sendto(est_conn,self.dest_addr)
        self.dest_addr = newsockaddr
        self.seq = 1
        self.seq_ack = 1
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
        if len(self.recv_buffer) > 0 :
            if self.recv_buffer[0][0] == self.seq_ack:
                package = utils.UnpackRDTMessage(self.recv_buffer[0][1])
                print((time.time()*1000)%1000)
                print("Read a message in buffer.", package[0:8])
                self.seq_ack += package[6]
                self.recv_buffer = self.recv_buffer[1:]
                return package[8]

        if self.this_fin == False and self.this_fin_seq is not None:
            if self.seq_ack == self.this_fin_seq:
                self.close()
                return None

        temdata, addr = self.recvfrom(bufsize=bufsize)
        while not addr == self.dest_addr:
            temdata, addr = self.recvfrom(bufsize=bufsize)

        if check_package(temdata,3) and len(temdata)>18:
            print((time.time()*1000)%1000)
            print("receive an message", utils.UnpackRDTMessage(temdata)[0:8])
            package = utils.UnpackRDTMessage(temdata)
            if package[4] > self.seq_ack:
                for i in range(len(self.recv_buffer)):
                    if self.recv_buffer[i][0] > package[4]:
                        self.recv_buffer = self.recv_buffer[0:i]+[(package[4],temdata)] + self.recv_buffer[i:len(self.recv_buffer)]
                        self.recv(4096)
            elif package[4] == self.seq_ack:
                self.seq_ack += package[6]
                data = package[8]
            ack_package = utils.CreateRDTMessage(SYN=False,FIN=False,ACK=True,SEQ= self.seq,SEQ_ACK=self.seq_ack)
            self.sendto(ack_package,self.dest_addr)
        elif check_package(temdata, 4):
            package = utils.UnpackRDTMessage(temdata)
            self.this_fin = False
            self.this_fin_seq = package[4]
            if self.seq_ack == self.this_fin_seq:
                self.close()
                return None
        else:
            data = self.recv(4096)

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
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
        all_message = bytes
        message_len = len(all_message)
        if message_len%self.maxmessagelen == 0:
            package_num = int(message_len/self.maxmessagelen)
        else:
            package_num = int(message_len/self.maxmessagelen) + 1
        print("Need to send",package_num,"packages.")
        winsize = 0
        if package_num<self.maxwinsize:
            winsize = package_num
        else:
            winsize = self.maxwinsize
        winflag = [0 for i in range(winsize)]
        winbuffer = [None for i in range(winsize)]
        winseqack = [0 for i in range(winsize)]
        win_left_position = 0
        win_right_position = 0
        SetTimerFlag = 0
        starttime = 0
        #self.seq_ack = 0
        thread = 0
        while True:
            if win_left_position == package_num:
                break

            if not SetTimerFlag:
                #print("Timer is reset.")
                SetTimerFlag = 1
                starttime = time.time()
                thread = recvThreading(self)
                thread.start()

            if thread.get_thread_running():
                continue

            if time.time() - starttime < self.timeout:
                if thread.buffer is not None:
                    print((time.time() * 1000) % 1000)
                    print("receive an ACK", utils.UnpackRDTMessage(thread.buffer)[0:8])
                    local_message = thread.buffer
                    fields = utils.UnpackRDTMessage(local_message)
                    for i in range(win_left_position, win_right_position):
                        if fields[5] == winseqack[i - win_left_position]:
                            winflag[i - win_left_position] = 1
                            break
                    # if winseqack[0] == 1:
                    #     starttime = time.time()
                    thread.buffer = None
            else:
                print((time.time() * 1000) % 1000)
                print("Retransmission! self.seq is",self.seq,"self.seq_ack is",self.seq_ack)
                package = winbuffer[0]
                self.sendto(bytes, self.dest_addr)
                starttime = time.time()

            while winflag[0] == 1:
                win_left_position += 1
                for i in range(winsize - 1):
                    winflag[i] = winflag[i + 1]
                    winbuffer[i] = winbuffer[i+1]
                    winseqack[i] = winseqack[i+1]
                winflag[winsize - 1] = 0
                winbuffer[winsize-1] = None
                winseqack[winsize-1] = 0
                SetTimerFlag = 0

            if win_right_position - win_left_position < winsize and win_right_position < package_num:
                pac_msg_len = 0
                package_message = 0
                if (message_len - win_right_position*self.maxmessagelen)<self.maxmessagelen :
                    pac_msg_len = message_len - win_right_position*self.maxmessagelen
                else:
                    pac_msg_len = self.maxmessagelen
                package_message = all_message[win_right_position*self.maxmessagelen:win_right_position*self.maxmessagelen+pac_msg_len].decode()
                # #print("length of payload is",len(package_message),"pac_msg_len is",pac_msg_len,"message_len is",message_len)
                package = utils.CreateRDTMessage(SYN = est_conn_h[0],FIN=est_conn_h[1],ACK = est_conn_h[2],SEQ=self.seq,SEQ_ACK=self.seq_ack, Payload=package_message)
                self.seq += pac_msg_len
                winbuffer[win_right_position - win_left_position] = package
                winseqack[win_right_position - win_left_position] = self.seq
                print((time.time() * 1000) % 1000)
                print("sending a package",utils.UnpackRDTMessage(package)[0:8])
                self.sendto(package,self.dest_addr)
                win_right_position += 1

        print("send finished!")
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return True

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither further sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        if self.this_fin:  # raise a close request
            # 1.Sent fin_sent package
            fin_sent = utils.CreateRDTMessage(fin_sent_h[0], fin_sent_h[1], fin_sent_h[2], SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.sendto(fin_sent, self.dest_addr)
            print("1.fin_send is sent.")

            # 2. recv an ack package
            ack,addr = self.recvfrom(4096)
            print(ack)
            ack_package = utils.UnpackRDTMessage(ack)
            while not check_package(ack,3) or  not (ack_package[5] == self.seq and ack_package[6] == 0):
                ack,addr = self.recvfrom(4096)
                ack_package = utils.UnpackRDTMessage(ack)
            print("2.An ack package is received.")

            # 3. recv a fin_sent package
            recv_sent2,addr = self.recvfrom(4096)
            recv_sent2_package = utils.UnpackRDTMessage(recv_sent2)
            while not check_package(recv_sent2,4):
                recv_sent2,addr = self.recvfrom(4096)
                recv_sent2_package = utils.UnpackRDTMessage(recv_sent2)
            print("3.An fin_sent package is received.")

            # 4. send an ack package
            ack2 = utils.CreateRDTMessage(SYN=est_conn_h[0],FIN=est_conn_h[1],ACK=est_conn_h[2],SEQ=self.seq,SEQ_ACK=self.seq_ack)
            self.sendto(ack2,self.dest_addr)
            print("4.An ack package is sent.")

            self.dest_addr = None
            return
        else:   # receive a close request
            print("1.receive an fin_sent package")

            # 1.send an ACK
            ack = utils.CreateRDTMessage(SYN=est_conn_h[0], FIN=est_conn_h[1], ACK=est_conn_h[2], SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack)
            self.sendto(ack, self.dest_addr)
            print("2.An ack package is sent.")


            # 2.send an fin package
            fin_sent = utils.CreateRDTMessage(fin_sent_h[0], fin_sent_h[1], fin_sent_h[2], SEQ=self.seq,
                                              SEQ_ACK=self.seq_ack)
            self.sendto(fin_sent, self.dest_addr)
            print("3.An fin_sent is sent.")

            # 3.recv an ack package
            ack2,addr = self.recvfrom(4096)
            ack2_package = utils.UnpackRDTMessage(ack2)
            while not check_package(ack2,3) or not (ack2_package[5] == self.seq and ack2_package[6] == 0):
                ack2,addr = self.recvfrom(4096)
                ack2_package = utils.UnpackRDTMessage(ack2)
            print("4.An ack package is received.")

            self.dest_addr = None
            return None
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
    # connRsp, serverAddr = clientSocket.recvfrom(4096)
    # fmt = "<3?3ih%ds" % len(payload)
    # print(struct.unpack(fmt, connRsp))
