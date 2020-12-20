# Functions used in this project
import struct

def getCheckSum(package):
    '''(message)->checkSum
    Chunk into 16-bit block
    Add up
    Circulate to maintain 16 bits
    Obtain 1s complement
    :return: 16-bit checkSum
    :usage: Generate checkSum, verify checkSum(return 0 if correct)
    '''
    sum = 0x0
    for i in range(0,len(package),2):
        if len(package)<i+2:
            a=b'\x00'+package[i:]
            value = int.from_bytes(a,byteorder='little',signed=False)
            sum += int.from_bytes(a,byteorder='little',signed=False)
        else:
            a=package[i:i+2]
            value = int.from_bytes(package[i:i+2],byteorder='little',signed=False)
            sum += int.from_bytes(package[i:i+2],byteorder='little',signed=False)
    while sum > 65535:
        high = sum >>16
        sum &= 0xffff
        sum += high
    # print(hex(sum))
    sum = sum ^ 0xffff
    # print(hex(sum))
    return sum


def CreateRDTMessage(SYN=False, FIN=False, ACK=False, SEQ=0, SEQ_ACK=0, Payload=''):
    '''(bool,bool,bool,integer,integer,integer,short,str)->Message
    Create a message and return it
    :param SYN:  Flag  1 bit
    :param FIN:  Flag  1 bit
    :param ACK:  Flag  1 bit
    :param SEQ:  Sequence number  4 bytes
    :param SEQ_ACK: Ack  4 bytes
    :param LEN:  Length of Payload  4 bytes
    :param CHECKSUM: Checksum  2 bytes
    :param Payload: Payload  str
    :return: a binary message
    '''
    LEN = len(Payload)
    fmt = "<3?3ih%ds" % LEN
    Payload = bytes(Payload.encode())
    return struct.pack(fmt, SYN, FIN, ACK, SEQ, SEQ_ACK, LEN, CHECKSUM, Payload)

def UnpackRDTMessage(message):
    message_len = len(message)
    payload_len = message_len - 18
    fmt = "<4?3iH%ds" % payload_len
    return struct.unpack(fmt, message)


if __name__ == "__main__":
    # test of CreateRdtMessage
    payload = "?????"
    message = CreateRDTMessage(True,False,False,1,1,Payload="")
    print("Pack:", message)
    a = getCheckSum(message)
    print(a)
    # print("Pack type:",type(message))
    # print("Pack int",int.from_bytes(message,byteorder='little',signed=False))
    unpack = UnpackRDTMessage(message)
    print(unpack[0:3] == (True, False, False))
    print("Unpack:",unpack)
