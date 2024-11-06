import socket
from _thread import start_new_thread
import json
import random
from time import sleep
import time
import logging
from blockchain import BlockChain, Block
import sched

my_x_coordinate = random.randint(0, 10)
my_y_coordinate = random.randint(0, 10)

T_sens = 1
transaction = {}
my_addr = None
output_file = None
TTL = 13
server_sockets = []
time_to_send_message = 5
PACKET_LEN = 2048
message_list = set()
blockChain = None
mine_event = None
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
scheduler = sched.scheduler(time.time, time.sleep)
colors = {
    "INFO": {
        "death": "red",
        "liveness": "green",
        "liveness_reply": "green",
        "peer_request": "blue",
        "peer_reply": "blue",
        "message": "yellow",
    }
}


class Peer:
    def __init__(self, ip, port, conn):
        self.ip = ip
        self.port = port
        self.conn = conn
        self.tries = 0
        self.message_list = set()

    def __str__(self):
        return f"{self.ip}:{self.port}"


connected_peers = {}

sensor_data_map = {}
overall_trust_sensor_map = {}


def calculate_trust_value(sensor_id, sensor_data):
    current_value = float(sensor_data["value"])
    current_conf = sensor_data["conf"]

    Nij = []
    Tconfs = []

    # Iterate over the stored sensor data (i.e., neighboring nodes)
    for node_id, neighbor_data in sensor_data_map.items():
        if node_id == sensor_id:
            continue  # Don't compare the node to itself

        neighbor_value = float(neighbor_data["value"])
        neighbor_conf = int(neighbor_data["conf"])

        # Calculate the absolute difference between current node and neighbor
        value_diff = abs(current_value - neighbor_value)
        support = 1 if value_diff < 1.0 else -1

        # Store support value and confidence of the neighbor
        Nij.append(support)
        Tconfs.append(neighbor_conf)

    if len(Nij) == 0:
        return 0

    # Calculate trust value (Tsens_ij) using the formula
    Tsens_ij = (1 / len(Nij)) * sum(
        support * conf for support, conf in zip(Nij, Tconfs)
    )

    return Tsens_ij


def listen_server(conn):
    global transaction,sensor_data_map, overall_trust_sensor_map
    while True:
        data = conn.recv(2048).decode()
        if not data:
            print("Connection closed by server")
            break
        # data = json.loads(remove_padding(data))
        # if data["type"] == "Sensor_data":
        #     print("Sensor data received from server: ", data)

        data = json.loads(data)
        # Assuming each data received contains an identifier for the sensor node (e.g., 'sensor_id')
        sensor_id = data["nodeid"]
        sensor_value = data["RSRP"]
        sensor_conf = data["Tconf"]

        # Store the data in sensor_data_map
        sensor_data_map[sensor_id] = {"value": sensor_value, "conf": sensor_conf}

        # Calculate trust value for the current node
        trust_value = calculate_trust_value(sensor_id, sensor_data_map[sensor_id])
        if sensor_id not in overall_trust_sensor_map:
            overall_trust_sensor_map[sensor_id] = 1 * sensor_conf * trust_value
        else:
            # Update the existing value
            overall_trust_sensor_map[sensor_id] *= sensor_conf * trust_value
        print(f"Trust value for sensor node {sensor_id}: {trust_value}")

        transaction_field = {
            "timestamp": time.asctime(time.localtime()),
            "nodeid": sensor_id,
            "nodeip": data["nodeip"],
            "nodeport": data["nodeport"],
            "value": sensor_value,
            "Tconf": sensor_conf,
            "Tsens": trust_value,
            "Toverall": overall_trust_sensor_map[sensor_id],
        }
        transaction = transaction_field
        with open(output_file, "a") as f:
            logger.info(f"Transaction: {transaction}")


def add_padding(raw_data):
    return raw_data + " " * (PACKET_LEN - len(raw_data))


def remove_padding(data):
    return data.strip()


def send_death_message(peer_port):

    cur_time = time.localtime()
    message = {
        "type": "Death",
        "ip": my_addr[0],
        "port": peer_port,
        "time": time.asctime(cur_time),
    }
    message = add_padding(json.dumps(message)).encode()
    with open(output_file, "a") as f:
        logger.info(
            f"Sending death message to {peer_port}", extra={"log_color": "INFO[death]"}
        )

    for socket in server_sockets:
        try:
            socket.sendall(message)
        except:
            print(f"Error in sending death message to server {socket.getsockname()}")


def check_liveness(peer_port):
    global connected_peers

    cur_time = time.localtime()
    message = {
        "type": "Liveness",
        "ip": my_addr[0],
        "port": my_addr[1],
        "time": time.asctime(cur_time),
    }
    message = add_padding(json.dumps(message)).encode()
    while True:
        if peer_port not in connected_peers:
            print(f"Closing connection from Peer_{peer_port}")
            break

        sleep(TTL)

        try:
            connected_peers[peer_port].conn.sendall(message)
        except:
            print(f"Error in sending liveness message to  Peer_{peer_port}")

        try:
            connected_peers[peer_port].tries += 1
        except:
            print(f"Closing connection from Peer_{peer_port}")
            break


def listen_peer(peer):
    global connected_peers, my_addr, output_file, logger, message_list

    while True:

        if peer.port in connected_peers and connected_peers[peer.port].tries >= 3:
            print(f"Connection closed by {peer.ip}:{peer.port}")
            del connected_peers[peer.port]
            send_death_message(peer.port)
            break

        try:
            data = peer.conn.recv(PACKET_LEN).decode()
        except:
            continue
        if not data:
            continue

        try:
            data = json.loads(remove_padding(data))
        except Exception as e:
            print(f"Error in listening peer {peer.ip}:{peer.port}: ", data, e)
            continue

        if data["type"] == "peer_Request":
            cur_time = time.localtime()
            message = {
                "type": "peer_Reply",
                "ip": my_addr[0],
                "port": my_addr[1],
                "time": time.asctime(cur_time),
            }
            message = add_padding(json.dumps(message)).encode()
            peer.conn.sendall(message)
            peer.ip = data["ip"]
            peer.port = data["port"]

            with open(output_file, "a") as f:
                logger.info(
                    f"Peer request from {peer.ip}:{peer.port}",
                    extra={"log_color": "INFO[peer_request]"},
                )

            connected_peers[peer.port] = peer

            start_new_thread(check_liveness, (peer.port,))

        elif data["type"] == "peer_Reply":
            with open(output_file, "a") as f:
                logger.info(
                    f"Peer request accepted from {peer.ip}:{peer.port}",
                    extra={"log_color": "INFO[peer_reply]"},
                )

        elif data["type"] == "Liveness":

            with open(output_file, "a") as f:
                logger.info(
                    f"Received liveness message from {peer.ip}:{peer.port} at {data['time']}",
                    extra={"log_color": "INFO[liveness]"},
                )
            cur_time = time.localtime()
            message = {
                "type": "Liveness_reply",
                "ip": my_addr[0],
                "port": my_addr[1],
                "time": time.asctime(cur_time),
            }
            peer.conn.sendall(add_padding(json.dumps(message)).encode())

        elif data["type"] == "Liveness_reply":

            with open(output_file, "a") as f:
                logger.info(
                    f"Sending liveness reply to {peer.ip}:{peer.port} at {data['time']}",
                    extra={"log_color": "INFO[liveness_reply]"},
                )
            connected_peers[peer.port].tries = max(
                0, connected_peers[peer.port].tries - 1
            )

        elif data["type"] == "block message":
            if f"{data['data']}_{data['time']}" in message_list:
                continue
            with open(output_file, "a") as f:
                logger.info(
                    f"{peer.ip}:{peer.port}: {data}",
                    extra={"log_color": "INFO[message]"},
                )
            schedule_mine_block()
            block = Block.from_dict(data["data"])
            blockChain.add_block(block, data["owner"])
            message_list.add(f"{data['data']}_{data['time']}")

        else:

            if (
                data["type"] == "message"
                and f"{data['data']}_{data['time']}" in message_list
            ):
                continue
            else:
                message_list.add(f"{data['data']}_{data['time']}")
                with open(output_file, "a") as f:
                    logger.info(
                        f"{peer.ip}:{peer.port}: {data}",
                        extra={"log_color": "INFO[message]"},
                    )

                send_all_peers(data, peer)


def accept_peers(sock):

    global connected_peers
    sock.listen()

    while True:
        conn, addr = sock.accept()
        print("Connected with", addr)

        start_new_thread(listen_peer, (Peer(addr[0], addr[1], conn),))


def send_all_peers(data, peer_port):
    global connected_peers, message_list
    message_list.add(f"{data['data']}_{data['time']}")
    data = add_padding(json.dumps(data)).encode()
    for port in connected_peers:
        if peer_port != None and (port == peer_port):
            print(f"Skipping {Peer.ip}:{Peer.port}")
            continue
        try:
            connected_peers[port].conn.sendall(data)
        except:
            continue


def send_messages():
    while True:
        sleep(time_to_send_message)
        data = random.choice(["hello", "hi", "bye"])
        time_stamp = time.localtime()
        message = {"type": "message", "data": data, "time": time.asctime(time_stamp)}

        send_all_peers(message, None)


def schedule_mine_block():
    global mine_event, blockChain, scheduler
    if mine_event is not None:
        try:
            scheduler.cancel(mine_event)
        except:
            pass
    mine_event = scheduler.enter(blockChain.tauGenerator(), 1, mine_block, ())


def mine_block():
    global blockChain, my_addr, transaction

    block = blockChain.mine_block(transaction)
    message = {
        "type": "block message",
        "data": block.__dict__(),
        "time": time.asctime(time.localtime()),
        "owner": my_addr[1],
    }
    send_all_peers(message, None)
    schedule_mine_block()


def euclidean_distance(x1, y1, x2, y2):
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def main():
    global my_addr, connected_peers, output_file, server_sockets, logger, colors, blockChain, scheduler, my_x_coordinate, my_y_coordinate

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        my_addr = sock.getsockname()
        output_file = f"bin/clients/output_{my_addr[1]}.log"
        file_handler = logging.FileHandler(output_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(file_handler)

        with open(output_file, "w") as f:
            logger.info(
                f"Client started at {my_addr}", extra={"log_color": "bold_green"}
            )

        with open("config.csv", "r") as f:
            server_sockets = []
            peer_list = set()
            lines = f.readlines()[1:]
            for line in lines:
                ip, port, node_id, x_cod, y_cod = line.split(",")
                if (
                    euclidean_distance(
                        my_x_coordinate, my_y_coordinate, int(x_cod), int(y_cod)
                    )
                    > 5
                ):
                    continue
                else:
                    lines.remove(line)
            print(lines)
            n = len(lines)
            servers_to_pick = random.sample(lines, n // 2 + 1)

            for line in servers_to_pick:
                server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ip, port, node_id, _, _ = line.split(",")
                port = int(port)
                n += 1
                server_sock.connect((ip, port))
                server_sockets.append(server_sock)

        random.shuffle(server_sockets)
        server_sockets = server_sockets[0 : (n // 2 + 1)]
        for server_sock in server_sockets:
            message = {"type": "getData", "ip": my_addr[0], "port": my_addr[1]}
            server_sock.sendall(json.dumps(message).encode())
            pl = server_sock.recv(2048).decode()
            print(pl)
            pl = json.loads(pl)["Peers"]
            pl = [peer.split(":") for peer in pl]
            for p in pl:
                p[1] = int(p[1])
            for item in pl:
                peer_list.add(tuple(item))
            start_new_thread(listen_server, (server_sock,))

        peer_list = list(peer_list)

        start_new_thread(accept_peers, (sock,))
        random.shuffle(peer_list)
        print("The Peer List is:", peer_list)

        peer_count = 0
        for i in range(len(peer_list)):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect((peer_list[i][0], peer_list[i][1]))
                if blockChain is None:
                    blockChain = BlockChain(
                        my_addr[1],
                        1,
                        f"bin/blockchain/blockchain_{peer_list[i][1]}.csv",
                    )
                start_new_thread(
                    listen_peer, (Peer(peer_list[i][0], peer_list[i][1], s),)
                )
                start_new_thread(check_liveness, (peer_list[i][1],))
                message = {"type": "peer_Request", "ip": my_addr[0], "port": my_addr[1]}
                s.sendall(add_padding(json.dumps(message)).encode())
                connected_peers[peer_list[i][1]] = Peer(
                    peer_list[i][0], peer_list[i][1], s
                )
                peer_count += 1
                print(f"Connected with {peer_list[i]}")

            except Exception as e:
                print(f"Connection failed with {peer_list[i]}")
                print("error is: ", e)

            if peer_count >= 4:
                break
        if blockChain is None:
            blockChain = BlockChain(my_addr[1], 1, f"genesis_block.csv")
        # start_new_thread(send_messages, ())
        schedule_mine_block()
        scheduler.run()
        global message_list
        while True:
            print("Enter 1. 'Peer List'\n 2. 'Message List'\n 3. 'Exit'\n")
            command = int(input())
            if command == 1:
                for peer in connected_peers:
                    print(peer)
            elif command == 2:
                print(message_list)


if __name__ == "__main__":
    main()
