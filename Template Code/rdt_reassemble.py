from CN_rdt.USocket import UnreliableSocket
import CN_rdt.utils as utils
import threading
from CN_rdt.USocket import UnreliableSocket
import CN_rdt.USocket as USocket
import CN_rdt.utils as utils
import socket
import time
import heapq

port_pool = [(12000 + _) for _ in range(1000)]
port_pool_flag = [0 for _ in range(1000)]
sockets = {}

# Package Header
#######################################################
# 0SYN 1FIN 2ACK 3BLANK 4SEQ 5SEQ_ACK 6LEN 7CHECKSUM 8PAYLOAD
#######################################################
# Package Header v2
#######################################################
# 0SYN 1FIN 2ACK 3FG 4FF 5LF 6SEQ 7SEQ_ACK 8ID 9LEN 10CHECKSUM 11PAYLOAD
#######################################################
syn_h = 0
fin_h = 1
ack_h = 2
fg_h = 3
ff_h = 4
lf_h = 5
seq_h = 6
seq_ack_h = 7
id_h = 8
len_h = 9
checksum_h = 10
payload_h = 11
syn_sent_h = (True, False, False)
syn_recv_h = (True, False, True)
est_conn_h = (False, False, True)
fin_sent_h = (False, True, True)  # ACK for latest received pkg
fin_ack_recv_h = (False, True, True)
fin_ack_h = (False, False, True)  # ACK for fin_sent


class recvThreading(threading.Thread):
    def __init__(self, rdt):
        threading.Thread.__init__(self)
        self.buffer = None
        self.rdt = rdt

    def run(self):
        self.buffer = self.rdt.recv(1096)

    # Get duplicate pkg, set; Else, ignore
    def run_dup_tect(self, dup_pkg):
        message = self.rdt.recv(4096)
        if message == dup_pkg:
            self.buffer = message

class Package(object):
    def __init__(self, pkg):
        self.pkg = pkg
    def __lt__(self, other):
        if self.pkg[id_h] < other.pkg[id_h]:
            return True
        else:
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
    # 6: fin_ack_recv
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
    if package_type == 2 and not package_msg[0:3] == est_conn_h:
        print("+++EST_CONN Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 3 and not package_msg[0:3] == est_conn_h:
        print("+++EST_CONN Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 4 and not package_msg[0:3] == fin_sent_h:
        print("+++FIN_SENT Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 5 and not package_msg[0:3] == fin_ack_h:
        print("+++FIN_ACK Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type == 6 and not package_msg[0:3] == fin_ack_recv_h:
        print("+++FIN_ACK Failed\n+++Invalid package: Wrong header!")
        return False
    if package_type < 0 or package_type > 6:
        print("+++Invalid package type:", package_type)
        return False
    return True

def interval_merge(intervals):
    merged = []
    for interval in intervals:
        if not merged or merged[-1][1] < interval[0]:
            merged.append(interval)
        else:
            merged[-1][1] = max(merged[-1][1], interval[1])
    return merged


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
        self.seq_ack = None
        # The latest sent seq
        self.seq = 0
        # The next seq to be send: last.seq + last.len
        self.seq_next = 0
        # The id of data pack to be sent
        self.id_cnt = 0
        self.dest_addr = None
        self.send_buffer = []
        self.recv_buffer = []
        self.cur_recv_id = 0
        self.recv_list = {}
        self.recv_id_list={}
        self.recv_intervals = {}
        self.maxwinsize = 5
        self.maxmessagelen = 3000
        self.timeout = 2
        self.active_fin = False
        self.this_fin = False
        self.other_fin = False
        # self.senderwindow = [0 for _ in range(self.winsize)]
        # self.senderbuffer = [0 for _ in range(self.winsize)]
        # self.recvwindow = [0 for  _ in range(self.winsize)]
        # self.recvbuffer = [0 for _ in range(self.winsize)]

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
                port_pool_flag[i] = 1
                break
        newsockaddr = "127.0.0.1," + str(newport)
        syn_recv = utils.CreateRDTMessage(SYN=syn_recv_h[0], FIN=syn_recv_h[1], ACK=syn_recv_h[2], FG=False, FF=False, LF=False, SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack, ID=self.id_cnt, Payload=newsockaddr)
        self.id_cnt += 1
        self.seq_next = self.seq+1
        # print(syn_recv)
        # print("test1")
        self.sendto(syn_recv,self.dest_addr)
        # print("test2")
        print("2.SYN_RECV is sent.")

        # Establish connection
        est_conn, client_addr = self.recvfrom(1024)
        if not client_addr == self.dest_addr:
            print("+++EST_CONN Failed\n+++Invalid package: Wrong client!")
            self.dest_addr = None
            return conn, addr
        est_conn_upk = utils.UnpackRDTMessage(est_conn)
        if not check_package(est_conn, 2):
            self.dest_addr = None
            return conn, addr
        if not est_conn_upk[seq_ack_h] == self.seq_next:
            print("+++EST_CONN Failed\n+++Invalid package: Wrong seq_ack!")
            self.dest_addr = None
            return conn, addr
        self.seq = self.seq_next
        self.seq_ack = est_conn_upk[seq_h] + 1
        print("3.Connection established.")

        conn.bind(("127.0.0.1", newport))
        addr = self.dest_addr
        conn.dest_addr = self.dest_addr
        conn._send_to = conn.sendto
        conn._recv_from = conn.recvfrom
        conn.seq = self.seq
        conn.seq_next = self.seq_next
        conn.seq_ack = self.seq_ack
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
        syn_sent = utils.CreateRDTMessage(syn_sent_h[0], syn_sent_h[1], syn_sent_h[1], SEQ=self.seq, SEQ_ACK=0,ID=self.id_cnt,
                                          Payload='')
        self.id_cnt += 1
        self.seq_next = self.seq +1
        self.dest_addr = address
        self.sendto(syn_sent,address)
        print("1.SYN_SENT is sent.")

        # listen for SYN_RECV
        syn_recv, server_addr = self.recvfrom(1024)

        # print(syn_recv)
        if not check_package(syn_recv, 1):
            self.dest_addr = None
            self._recv_from = None
            self._send_to = None
            return False
        syn_recv_upk = utils.UnpackRDTMessage(syn_recv)
        if not syn_recv_upk[seq_ack_h] == self.seq_next:
            print("+++SYN_RECV Failed\n+++Invalid package: Wrong seq_ack!")
            self.dest_addr = None
            self._send_to = None
            self._recv_from = None
            return False
        self.seq = self.seq_next
        self.seq_ack = syn_recv_upk[seq_h] + 1
        newsockaddr = syn_recv_upk[payload_h].decode().split(',')
        newsockaddr = (newsockaddr[0], int(newsockaddr[1]))
        print("2.SYN_RECV is right.")

        # ESTABLISH CONNECTION, pure ack
        est_conn = utils.CreateRDTMessage(est_conn_h[0], est_conn_h[1], est_conn_h[2], SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack, ID=self.id_cnt, Payload='')
        self.id_cnt += 1
        self.seq_next = self.seq + 1
        self.sendto(est_conn, self.dest_addr)
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
        # if has buffered data
        frag_complete = False
        frag_wait = False
        if self.recv_list.get(self.cur_recv_id):
            data_tem = self.recv_list[self.cur_recv_id]
            if len(data_tem) > bufsize:
                data = data_tem[:bufsize]
                self.recv_list[self.cur_recv_id] = data_tem[bufsize:]
            else:
                data = data_tem
            return data
        if self.recv_list:
            # return once
            for key,value in self.recv_list.items():
                if len(value) > bufsize:
                    data = value[:bufsize]
                    self.recv_list[self.cur_recv_id] = value[bufsize:]
                else:
                    data = value
                break
            return data
        if self.recv_buffer:
            pkg_id = self.recv_buffer[0][id_h]
            self.cur_recv_id = pkg_id
            if self.recv_id_list[pkg_id][0] == 1 and self.recv_id_list[id][1] == 1:
                frag_wait = True
        # Get recv
        while not frag_complete:
            temp_data, addr = self.recvfrom(bufsize=bufsize)
            while not addr == self.dest_addr:
                temp_data, addr = self.recvfrom(bufsize=bufsize)
            # Discard if corrupted
            if utils.getCheckSum(temp_data) != 0:
                # ack = utils.CreateRDTMessage(est_conn_h[0], est_conn_h[1], est_conn_h[2], False, False, False, self.seq, self.seq_ack, '')
                continue
            temp_data_upk = utils.UnpackRDTMessage(temp_data)
            # recv is used after establishing connections, thus no syn pkt will be kept
            # recv FIN, deal with close, return null
            if temp_data_upk[syn_h:ack_h+1] == fin_sent_h:
                # if self passively getting fin_ack
                if not self.active_fin:
                    print("1.FIN_SENT from a close request is received.")
                    syn_sent_upk = temp_data_upk
                    if syn_sent_upk[len_h] == 0:
                        a = 1
                    else:
                        a = syn_sent_upk[len_h]
                    self.seq_ack = syn_sent_upk[seq_h] + a
                    # state: ESTAB->CLOSE_WAIT, LAST_ACK
                    fin_ack_recv = utils.CreateRDTMessage(fin_ack_recv_h[0], fin_ack_recv_h[1], fin_ack_recv_h[2], False,False,False, self.seq,
                                                          syn_sent_upk[seq_h]+1, self.id_cnt, '')
                    self.id_cnt += 1
                    self.seq_next = self.seq + 1
                    self.sendto(fin_ack_recv, self.dest_addr)
                    print("2.FIN_ACK_RECV is sent.")
                    # state: LAST_ACK->CLOSED
                    # recv if not fin_ack, discard and retransmit; recv if fin_ack, release and close
                    fin_ack, fin_addr = self.recvfrom(bufsize=bufsize)
                    fin_ack_upk = utils.UnpackRDTMessage(fin_ack)
                    while (not fin_addr == self.dest_addr) or fin_ack_upk[0:3] != est_conn_h or (not self.checkSeq(fin_ack_upk)):
                        self.sendto(fin_ack_recv,self.dest_addr)
                        fin_ack, fin_addr = self.recvfrom(bufsize=bufsize)
                        fin_ack_upk = utils.UnpackRDTMessage(fin_ack)
                    # USocket.sockets[id(super())].shutdown(socket.SHUT_RDWR)
                    self._send_to = None
                    self._recv_from = None
                    super().close()
                    print("3.Service connection closed.")
                    return None
                # if self choose to close while getting a duplicate fin_ack from the other end, return fin to close method, let it retransmit
                else:
                    print("1.FIN_RECV_ACK retransmission is received.")
                    return temp_data
            # recv normal pkg, pure ack, return pkg
            elif temp_data_upk[syn_h:ack_h+1] == est_conn_h and temp_data_upk[payload_h] == b'':
                print("1.ACK received.")
                return temp_data
                # ack does not consume seq, no need to update seq and seq_ack
                # break
            # recv normal pkg, contain data
            elif temp_data_upk[syn_h:ack_h+1] == est_conn_h:
                print("1.Received data:",temp_data_upk)
                ack = utils.CreateRDTMessage(est_conn_h[0], est_conn_h[1], est_conn_h[2], False, False, False,
                                             self.seq, temp_data_upk[seq_h] + 1, self.id_cnt, '')
                self.sendto(ack,self.dest_addr)
                if len(self.recv_buffer) == 0:
                    # recv data not fragmented, return data, send ack
                    if not temp_data_upk[fg_h]:
                        return temp_data
                        # break
                    else:
                        pkg_id = temp_data_upk[id_h]
                        if self.recv_id_list.get(pkg_id) is None:
                            self.recv_id_list[pkg_id] = [-1,-1]
                        # recv data fragmented and is 1st fragment
                        if temp_data_upk[ff_h]:
                            self.recv_id_list[pkg_id][0] = 1
                            self.cur_recv_id = pkg_id
                            self.recv_intervals[self.cur_recv_id] = []
                            heapq.heappush(self.recv_intervals[self.cur_recv_id], [temp_data_upk[seq_h], temp_data_upk[seq_h]
                                                                              + temp_data_upk[len_h]])
                            heapq.heappush(self.recv_buffer, Package(temp_data_upk))
                # have buffered fragments
                else:
                    pkg_id = temp_data_upk[id_h]
                    # recv current_id's last pkg or has received current_id's last pkg and waiting for previous pkg
                    if pkg_id == self.cur_recv_id and (temp_data_upk[lf_h] or frag_wait):
                        self.recv_id_list[pkg_id][1] = 1
                        merged = interval_merge(self.recv_intervals[self.cur_recv_id])
                        if merged[0][1] == temp_data_upk[seq_h]:
                            text = b''
                            # Combine text, store
                            tem_buffer = self.recv_buffer.copy()
                            for pkg in tem_buffer:
                                if pkg.pkg[id_h] == self.cur_recv_id:
                                    text += pkg.pkg[payload_h]
                                    self.recv_buffer.remove(pkg)
                                else: break
                            text += temp_data_upk[payload_h]
                            self.recv_list[self.cur_recv_id] = text
                            break
                        else:
                            heapq.heappush(self.recv_intervals[pkg_id],
                                           [temp_data_upk[seq_h], temp_data_upk[seq_h] +
                                            temp_data_upk[len_h]])
                            heapq.heappush(self.recv_buffer, Package(temp_data_upk))
                            frag_wait = True
                    else:
                        if self.recv_id_list.get(pkg_id) is None:
                            self.recv_id_list[pkg_id] = [-1,-1]
                        if temp_data_upk[lf_h]:
                            self.recv_id_list[pkg_id][1] = 1
                            merged = interval_merge(self.recv_intervals[pkg_id])
                            if merged[0][1] == temp_data_upk[seq_h]:
                                text = b''
                                # Combine text, return
                                tem_buffer = self.recv_buffer.copy()
                                for pkg in tem_buffer:
                                    if pkg.pkg[id_h] == pkg_id:
                                        text += pkg.pkg[payload_h]
                                        self.recv_buffer.remove(pkg)
                                self.recv_list[id_h] = text
                        else:
                            if temp_data_upk[ff_h]:
                                self.recv_id_list[pkg_id][0] = 1
                            heapq.heappush(self.recv_intervals[pkg_id], [temp_data_upk[seq_h], temp_data_upk[seq_h] +
                                                                    temp_data_upk[len_h]])
                            heapq.heappush(self.recv_buffer, Package(temp_data_upk))
        data_tem = self.recv_list[self.cur_recv_id]
        if len(data_tem) > bufsize:
            data = data_tem[:bufsize]
            self.recv_list[self.cur_recv_id] = data_tem[bufsize:]
        else:
            data = data_tem
            del self.recv_list[self.cur_recv_id]
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        # print("another hello again")
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
        message = utils.UnpackRDTMessage(bytes)[8]
        message_len = len(message)
        package_num = message_len / self.maxmessagelen + 1
        winsize = 0
        if package_num < self.maxwinsize:
            winsize = package_num
        else:
            winsize = self.maxwinsize
        winflag = [0 for i in range(winsize)]
        win_left_position = 0
        win_right_position = 0
        SetTimerFlag = 0
        time = 0
        while True:
            thread = recvThreading(self)
            if win_right_position - win_left_position < winsize and win_left_position < package_num:
                pac_msg_len = 0
                package_message = 0
                if (message_len - win_right_position * self.maxmessagelen) < self.maxmessagelen:
                    pac_msg_len = message_len - win_right_position * self.maxmessagelen
                else:
                    pac_msg_len = self.maxmessagelen
                package_message = message[
                                  win_right_position * self.maxmessagelen:win_right_position * self.maxmessagelen + pac_msg_len].decode()
                package = utils.CreateRDTMessage(SYN=est_conn_h[0], FIN=est_conn_h[1], ACK=est_conn_h[2],
                                                 SEQ=win_right_position * self.maxmessagelen, SEQ_ACK=0,
                                                 Payload=package_message)
                self.sendto(package, self.dest_addr)
                win_right_position += 1
                if not SetTimerFlag:
                    SetTimerFlag = 1
                    time = time.time()
                    thread.start()
                    thread.run()
            else:
                if time.time() - time < self.timeout:
                    if thread.buffer is None:
                        pass
                    else:
                        message = thread.buffer

                else:
                    package_message = message[
                                      win_left_position * self.maxmessagelen:win_left_position * self.maxmessagelen + pac_msg_len].decode()
                    package = utils.CreateRDTMessage(SYN=est_conn_h[0], FIN=est_conn_h[1], ACK=est_conn_h[2],
                                                     SEQ=win_left_position * self.maxmessagelen, SEQ_ACK=0,
                                                     Payload=package_message)
                    self.sendto(package, self.dest_addr)

        # self.sendto(bytes,self.dest_addr)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return

    def simple_send(self, bytes:bytes):
        left = 0
        length = 10
        str_lst = []
        while left+length < len(bytes) :
            str_lst.append(bytes[left:left+length])
            left += length
        if left < len(bytes):
            str_lst.append(bytes[left:])
        pkg = utils.CreateRDTMessage(False,False,True,True,True,False,self.seq,self.seq_ack,self.id_cnt,str_lst[0])
        self.sendto(pkg,self.dest_addr)
        print("SS: send pkg0")
        i = 1
        while i<len(str_lst):
            if i == len(str_lst)-1:
                last = True
            else:
                last = False
            pkg = utils.CreateRDTMessage(False, False, True, True, False, last, self.seq+i*length, self.seq_ack, self.id_cnt,
                                         str_lst[i])
            self.sendto(pkg,self.dest_addr)
            print("SS: send pkg",i)
            i += 1
        i = 1
        while i<len(str_lst):
            data = self.recv(1024)

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither further sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        # state: ESTAB->FIN_WAIT_1
        assert self._send_to is not None, "Cannot close an unestablished connection!"
        fin_sent = utils.CreateRDTMessage(fin_sent_h[0], fin_sent_h[1], fin_sent_h[2], SEQ=self.seq,
                                          SEQ_ACK=self.seq_ack,
                                          Payload='')
        self.sendto(fin_sent,self.dest_addr)
        self.seq_next = self.seq + 1
        print("1.Close request is sent.")

        while (1):
            fin_ack_recv, addr = self.recvfrom(1024)
            fin_ack_recv_upk = utils.UnpackRDTMessage(fin_ack_recv)
            if not check_package(fin_ack_recv, 6) or (not addr == self.dest_addr) or (
            not self.checkSeq(fin_ack_recv_upk)):
                continue
            else:
                break
        # state: FIN_WAIT_1->FIN_WAIT_2
        self.seq = self.seq_next
        self.seq_ack = fin_ack_recv_upk[seq_h] + 1
        print("2.Close is agreed.")
        self.this_fin = True

        # state: FIN_WAIT_2->TIMED_WAIT
        fin_ack = utils.CreateRDTMessage(fin_ack_h[0], fin_ack_h[1], fin_ack_h[2], SEQ=self.seq,
                                         SEQ_ACK=self.seq_ack,
                                         Payload='')
        self.sendto(fin_ack, self.dest_addr)

        # wait while recv till no problem
        while 1:
            # timeOut = self.check_time_out()
            timeOut = True
            if timeOut:
                # shut down
                # USocket.sockets[id(super)].shutdown(socket.SHUT_RDWR)
                print("4.All close and close ack sent.")
                super().close()
                break
            else:
                self.send(fin_ack)
            #############################################################################
            #                             END OF YOUR CODE                              #
            #############################################################################

    def check_time_out(self):
        thread = recvThreading(self)
        start = time.time()
        thread.start()
        thread.run()

        valid = False
        if time.time() - start < 2 * self.timeout:
            if thread.buffer is None:
                pass
            else:
                valid = True
        else:
            valid = True
        return valid

    def checkSeq(self, message):
        return message[seq_h] == self.seq_ack and message[seq_ack_h] == self.seq_next

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
