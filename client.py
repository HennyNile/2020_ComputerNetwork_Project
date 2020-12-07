from rdt import socket

SERVER_ADDR = "127.0.0.1"
SERVER_PORT = 12000
MESSAGE = "hello!"
BUFFER_SIZE = 2048
client =socket()
client.connect((SERVER_ADDR, SERVER_PORT))
client.send(MESSAGE)
data = client.recv(BUFFER_SIZE)
assert data == MESSAGE
client.close()