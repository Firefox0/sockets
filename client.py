import socket
import threading 

HEADER = 4
BUFFER = 4096
PORT = 5050 
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)

class Client: 

    def send(self, msg):
        message = msg.encode()
        msg_length = len(message)
        send_length = str(msg_length).encode()
        self.client.send(send_length)
        self.client.send(message)

    def receive_message(self):
        while True:
            if msg := self.client.recv(BUFFER):
                print(msg.decode())

    def connect(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(ADDR)
        thread = threading.Thread(target=self.receive_message)
        thread.start()

    def start(self):
        self.connect()

        while True:
            msg = input()
            self.send(msg)
            if msg == ">login":
                self.connect()    
            elif msg == ">dc":
                self.client.close()
                
if __name__ == "__main__":
    Client().start()