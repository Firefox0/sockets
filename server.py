import socket 
import threading

HEADER = 4
BUFFER = 4096
PORT = 5050 
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)

class Server:

    connections = {}
    blocked = {}
    forbidden_usernames = {"server", "admin", "moderator"}

    def handle_client(self, client, address):
        self.initialize_client(client, address)
        while True:
            try:
                if msg_length := client.recv(HEADER).decode():
                    msg_length = int(msg_length)
                    msg = client.recv(BUFFER).decode()
                    client_name = self.connections[client]['name']
                    print(f"Received message from {client_name}({address}) with length {msg_length}: {msg}")

                    if msg.startswith(">username"):
                        name = msg.split(" ", 1)[1]
                        self.set_username(client, name)
                    elif msg.startswith(">dm"):
                        split = msg.split()
                        if len(split) < 3:
                            print(f"[ERROR] Couldn't send dm from {client_name}({address}). Recipient/Message missing.")
                            client.send(b"[SERVER] Couldn't send dm. Recipient/Message missing.")
                            return
                        recipient = split[1]
                        message = split[2]
                        self.send_dm(client, recipient, message)
                    elif msg.startswith(">block"):
                        block_user = msg.split(" ", 1)[1]
                        self.block_user(client, block_user)
                    elif msg.startswith(">unblock"): 
                        unblock_user = msg.split(" ", 1)[1]
                        self.unblock_user(client, unblock_user)
                    elif msg == (">dc" or ">relog"):
                        self.disconnect_client(client)
                        break
                    else:
                        self.handle_chat(client, msg)

                    print("")
                    
            except ConnectionResetError:
                self.disconnect_client(client)
                break

    def initialize_client(self, client, address):
        self.connections[client] = {"connection": client, "address": address, "name": ""}
        self.initialize_username(client)
        self.blocked[client] = set()
        print(f"{address} successfully initialized.\n")

    def initialize_username(self, client):
        client.send(b"Username: ")
        msg_length = client.recv(HEADER).decode()
        name = client.recv(BUFFER).decode()

        while not self.set_username(client, name):
            client.send(b"Pick a different username: ")
            msg_length = client.recv(HEADER).decode()
            name = client.recv(BUFFER).decode()

    def set_username(self, client, name):
        for forbidden_name in self.forbidden_usernames:
            if name == forbidden_name:
                print(f"[ERROR] Client {self.connections[client]['name']}({self.connections[client]['address']} wanted to change his name to {forbidden_name}.")
                client.send(f"You can't change your username to {forbidden_name}.".encode())
                return

        prev = self.connections[client]["name"]
        if prev == name:
            print(f"[ERROR] Failed updating username from {prev}({self.connections[client]['address']}) to {name}. Client owns the username already.")
            client.send(b"[SERVER] You own this name already.")
            return
        for target in self.connections:
            if self.connections[target]["name"] == name:
                print(f"[ERROR] Failed updating username from {prev}({self.connections[client]['address']}) to {name}." + 
                      f" Another client {self.connections[target]['name']}({self.connections[target]['address']}) owns the username already")
                client.send(b"[SERVER] Someone owns this name already.")
                return

        self.connections[client]["name"] = name
        client.send(b"[SERVER] Username updated.")
        print(f"Updated username from {self.connections[client]['address']}. {prev} -> {name}\n")
        return 1

    def disconnect_client(self, client):
        print(f"Disconnected {self.connections[client]['address']}")
        client.close()

    def handle_chat(self, client, msg):
        client_address = self.connections[client]["address"]
        final_msg = f"{self.connections[client]['name']}: {msg}"
        client.send(b"[SERVER] Message received")
        print(f"Sending message to all clients...")  

        for target in self.connections: 
            target_connection = self.connections[target]["connection"]
            target_address = self.connections[target]["address"]

            if (target_connection != client and 
                    target_address not in self.blocked[client] and 
                    client_address not in self.blocked[target]):
                target.send(final_msg.encode())

        print("Successfully sent.")

    def send_dm(self, client, recipient, msg):
        client_name = self.connections[client]["name"]
        client_address = self.connections[client]["address"]

        if recipient == client_name:
            print("Client tried to DM himself.")
            client.send(b"You can't DM yourself.")
            return
        if recipient in self.blocked[client]:
            client.send(f"[SERVER] Client {recipient} has blocked you. DM was not sent.".encode())
            return

        final_msg = f"[DM] {client_name}: {msg}"
        for target in self.connections:
            target_name = self.connections[target]["name"]
            if target_name == recipient:
                target_address = self.connections[target]["address"]
                if client_address in self.blocked[target]:
                    print(f"Couldn't send DM from {client_name}({client_address}) to {target_name}({target_address}). Recipient was blocked.")
                    client.send(f"[SERVER] Client {target_name} has blocked you. DM was not sent.".encode())
                    return
                if target_address in self.blocked[client]:
                    print(f"Couldn't send DM from {client_name}({client_address}) to {target_name}({target_address}). Recipient is in block list.")
                    client.send(f"[SERVER] You blocked the Client {target_name}. DM was not sent.".encode())
                    return
                final_msg = f"[DM] {client_name}: {msg}"
                self.connections[target]["connection"].send(final_msg.encode())
                print(f"DM from {client_name}({client_address}) to " + 
                      f"{target_name}({target_address}) with message {final_msg} sent successfully.")
                client.send(b"[SERVER] DM sent successfully.")
                return 

        print(f"Recipient {recipient} not found.")
        client.send(b"[SERVER] The recipient does not exist.")

    def block_user(self, client, block_user):
        client_name = self.connections[client]["name"]
        client_address = self.connections[client]["address"]

        for target in self.connections:
            target_name = self.connections[target]["name"]
            target_address = self.connections[target]["address"]
            if target_name == block_user:
                if target_address in self.blocked[client]:
                    print(b"Client tried block someone who was already blocked.")
                    client.send(f"[SERVER] Client {block_user} was already blocked.".encode())
                    return
                self.blocked[client].add(target_address)
                print(f"{client_name}({client_address}) blocked Client {block_user}({target_name}).".encode())
                client.send(f"[SERVER] Client {block_user} has been blocked.".encode())
                return 

        print(f"{client_name}({client_address}) wanted to block Client {block_user}. Client does not exist.".encode())
        client.send(f"[SERVER] Client {block_user} does not exist.".encode())

    def unblock_user(self, client, unblock_user):
        for target in self.connections:
            target_name = self.connections[target]["name"]
            if target_name == unblock_user:
                target_address = self.connections[target]["address"]
                if target_address not in self.blocked[client]:
                    print(b"Client tried unblock someone who was already unblocked.")
                    client.send(f"[SERVER] Client {target_name} was not blocked.".encode())
                    return

                client_name = self.connections[client]["name"]
                client_address = self.connections[client]["address"]
                try:
                    self.blocked[client].remove(target_address)
                except KeyError:
                    print(f"{client_name}({client_address}) tried to unblock someone who does not exist or wasn't blocked.")
                    client.send(f"[SERVER] Client {target_name} does not exist or was not blocked.".encode())
                else:
                    print(f"{client_name}({client_address}) unblocked Client {target_name}.")
                    client.send(f"[SERVER] Client {target_name}({target_address}) has been unblocked.".encode())
                break

    def start(self):
        print("Starting server...")
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(ADDR)
        server.listen()
        print(f"Server started. Listening on {SERVER}:{PORT}\n")
        
        while True:
            connection, address = server.accept()
            address = ":".join(str(e) for e in address)
            thread = threading.Thread(target=self.handle_client, args=(connection, address))
            thread.start()
            print(f"{address} connected.\n" + 
                  f"Active connections: {threading.activeCount() - 1}\n")

if __name__ == "__main__":
    Server().start()