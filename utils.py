# Functions used in this project
import struct

def CreateRDTMessage(SYN=False, FIN=False, ACK=False, SEQ=0, SEQ_ACK=0, LEN=0, CHECKSUM=0, Payload="hello"):
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


if __name__ == "__main__":
    # test of CreateRdtMessage
    payload = "Oh! My little James!"
    fmt = "<3?3ih%ds" % len(payload)
    print(struct.unpack(fmt, CreateRDTMessage(Payload=payload)))
