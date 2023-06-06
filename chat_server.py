import queue
import json
import time
import socket
import threading


class Message:
    def __init__(self, type, msg) -> None:
        self.type = type
        self.msg = msg


class Connection:
    def __init__(self, socket: socket.socket) -> None:
        self.incoming_queue = queue.Queue()
        self.socket = socket
        self.name = None
        self.thread = threading.Thread(target=self.handle_incoming_traffic, daemon=True)
        self.thread.start()
        self.counter = 0
        self.counter_reset = threading.Thread(target=self.reset_counter, daemon=True)
        self.counter_reset.start()


    def is_alive(self):
        return self.socket is not None

    def close(self):
        if self.is_alive():
            try:
                self.socket.getpeername()
                print(f"Closing connection from {self.name}")
            except OSError:
                print(f"Closed connection by {self.name}.")
            self.socket.close()
            self.socket = None

    def handle_incoming_traffic(self):
        while self.is_alive():
            try:
                data = self.socket.recv(1024)
            except Exception:
                break
            if not data:
                break
            else:
                try:
                    incoming_data = json.loads(data.decode("utf-8"))
                except json.decoder.JSONDecodeError:
                    remote = self.socket.getpeername()
                    print(f"Invalid payload from {remote[0]}:{remote[1]}")
                else:
                    self.incoming_queue.put(incoming_data)
            time.sleep(0.001)
        self.close()

    def reset_counter(self):
        while True:
            self.counter = 0
            time.sleep(1)

    def handle_outgoing_traffic(self, data):
        if self.is_alive():
            try:
                self.socket.send(json.dumps(data).encode("utf-8"))
                self.counter += 1
            except ConnectionResetError:
                pass


class ChatServer:
    def __init__(self, ip="0.0.0.0", port=10000) -> None:
        self.messages = []
        self.server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((ip, port))
        self.server_socket.listen()
        self.connections = {}
        self.connections_lock = threading.Lock()
        self.incoming_connections_thread = threading.Thread(
            target=self.handle_new_connection, daemon=True)
        self.incoming_connections_thread.start()
        self.server_msg = []

    def handle_new_connection(self):
        while True:
            sock, addr = self.server_socket.accept()
            print(f"Connected by {addr}")
            connection_id = f"{addr[0]}:{addr[1]}"
            connection = Connection(sock)
            with self.connections_lock:
                self.connections[connection_id] = connection
            time.sleep(0.001)

    def check_incoming_messages(self):
        new_messages = {}
        for connection_id in self.connections:
            conn_queue = self.connections[connection_id].incoming_queue
            if not conn_queue.empty():
                msg = conn_queue.get()
                msg_obj = Message(msg["type"], msg["msg"])
                new_messages[connection_id] = msg_obj
        return new_messages
    
    def check_existing_name(self, name):
        for id in self.connections:
            if name == self.connections[id].name:
                return True
        return False

    def process_incomig_messages(self):
        new_messages = self.check_incoming_messages()
        self.check_connections_liveness()
        for connection_id in new_messages:
            curr_msg = new_messages[connection_id]
            print(curr_msg.msg)
            curr_connection = self.connections[connection_id]
            if curr_msg.type == "REQUEST":
                if "server" in curr_msg.msg[0].lower() or "admin" in curr_msg.msg[0].lower():
                    bad_name = Message("NEWCON", "Name cannot include 'server' or 'admin'! Cannot ")
                    curr_connection.handle_outgoing_traffic(bad_name.__dict__)
                    time.sleep(0.1)
                    curr_connection.socket.close()
                else:            
                    if self.check_existing_name(curr_msg.msg):
                        bad_name = Message("NEWMSG", [f"{curr_msg.msg[0]}", "Name already in use!"])
                        curr_connection.handle_outgoing_traffic(bad_name.__dict__)
                        time.sleep(0.1)
                        curr_connection.socket.close()
                    else:
                        curr_connection.name = curr_msg.msg
                        connected = Message("CONNECTED", connection_id)
                        curr_connection.handle_outgoing_traffic(connected.__dict__)
                        broadcast_new_connection = Message("NEWCON", curr_msg.msg)
                        self.broadcast_message(broadcast_new_connection.__dict__)
            elif curr_msg.type == "NEWMSG":
                if curr_connection.counter > 2:
                    self.ban_user(curr_connection.name[0], "You have been banned for spamming")
                else:
                    broadcast_new_msg = Message("NEWMSG", curr_msg.msg)
                    self.broadcast_message(broadcast_new_msg.__dict__)
            elif curr_msg.type == "CLOSED":
                self.connections[connection_id].close()
                broadcast_closed_msg = Message("CLOSED", curr_msg.msg)
                self.broadcast_message(broadcast_closed_msg.__dict__)
            else:
                bad_msg_type = Message("NEWMSG", "Wrong message type!")
                curr_connection.handle_outgoing_traffic(bad_msg_type.__dict__)

        if len(self.server_msg) > 0:
            msg = self.server_msg.pop()
            if msg.startswith("ban-"):
                self.ban_user(msg[4:], "You have been banned by admin")
            else:
                broadcast_server_msg = Message("NEWMSG", ["serveradmin", msg])
                self.broadcast_message(broadcast_server_msg.__dict__)

    def ban_user(self, name, msg):
        if name in self.get_connections_name():
            ban_msg = Message("NEWMSG", [f"{name}", f"{msg}"])
            conn_to_ban = self.get_connection_by_name(name)
            conn_to_ban.handle_outgoing_traffic(ban_msg.__dict__)
            time.sleep(0.01)
            conn_to_ban.socket.close()
            broadcast_ban = Message("CLOSED", [f"Banned {name}"])
            self.broadcast_message(broadcast_ban.__dict__)

    def get_connections_name(self):
        names = []
        for id in self.connections:
            names.append(self.connections[id].name[0])
        return names
    
    def get_connection_by_name(self, name) -> Connection:
        for id in self.connections:
            if self.connections[id].name[0] == name:
                return self.connections[id]

    def broadcast_message(self, data):
        for connection_id in self.connections:
            self.connections[connection_id].handle_outgoing_traffic(data)

    def add_text_to_messages():
        pass

    def check_connections_liveness(self):
        conns_to_del = []
        for connection_id in self.connections:
            if not self.connections[connection_id].is_alive():
                conns_to_del.append(connection_id)
        for id in conns_to_del:
            self.connections.pop(id)


def new_terminal(server: ChatServer):
    while True:
        inp = input()
        server.server_msg.append(inp)
        time.sleep(0.001)

def main():
    server = ChatServer()
    t = threading.Thread(target=new_terminal, args=(server,),  daemon=True)
    t.start()
    while True:
        server.process_incomig_messages()
        time.sleep(0.001)


if __name__ == "__main__":
    main()
