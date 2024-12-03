import socket
from _thread import *
from time import sleep
import json
import sys
import random
import pandas as pd


# Global variables
# List to keep track of clients
clients = []
# Output file
output_file = None
nodeid = ""
nodeip = ""
nodeport = 0


# Class to make a peer object
class Peer:
    def __init__(self, conn, addr):
        self.conn = conn  # socket object
        self.addr = addr  # address of the peer node

    def __str__(self):
        return f"{self.addr[0]}:{self.addr[1]}"  # return the address of the peer node


# Function to listen to a peer
def listen_client(client):
    global clients, output_file

    while True:
        try:
            data = client.conn.recv(2048).decode()  # receive data from the peer
        except:
            continue
        if not data:
            continue

        try:
            data = json.loads(data)  # convert the data to json
        except:
            print(f"Peer_{client.addr[1]}: ", data)
            continue
        print(f"Peer_{client.addr[1]}: ", data)

        # if the type of the message is getData then send the data to the peer
        if data["type"] == "getData":

            live_client = [
                str(client) for client in clients
            ]  # get the address of all the peers
            clients.append(
                Peer(client.conn, (data["ip"], data["port"]))
            )  # add the client to the list of peers
            client.addr = (data["ip"], data["port"])  # update the address of the peers

            # write the address of the peers to the output file
            with open(output_file, "a") as f:
                print(f"Peer_{client.addr[1]} registered: {client.addr}", file=f)

            # send the address of all the peers to the new peer
            message = {"type": "getData_reply", "Peers": live_client}
            client.conn.sendall(json.dumps(message).encode())

        # if the type of message is 'Death' then remove the peer from the list of peers
        elif data["type"] == "Death":
            for i in range(len(clients)):
                if clients[i].addr == (data["ip"], data["port"]):
                    clients.pop(i)

                    # write the address of the peer to the output file that the peer is removed
                    with open(output_file, "a") as f:
                        print(f"Connection closed by Peer_{i}", file=f)
                    break


# Function to accept peers
def accept_clients(sock, clients):
    global output_file
    while True:
        sock.listen()

        # accept the connection from the peer
        conn, addr = sock.accept()
        my_client = Peer(conn, addr)
        idx = len(clients) - 1

        # update the output file that the peer is connected
        with open(output_file, "a") as f:
            print("Peer_{} connected: {}".format(idx, addr), file=f)

        # start a new thread to listen to the other peer
        start_new_thread(listen_client, (my_client,))


# Function to send data to all the peers
def send_all_clients(data, idx):
    global clients, output_file
    for i in range(len(clients)):
        if clients[i] == idx:
            continue
        try:
            clients[i].conn.sendall(data)
            with open(output_file, "a") as f:
                print(f"Sent to Peer_{i}: {data}", file=f)

        except Exception as e:
            with open(output_file, "a") as f:
                print(f"Connection closed by Peer_{i} because of {e}", file=f)
            clients.pop(i)
            break


def send_sens_data():
    global clients, output_file, nodeid, nodeip, nodeport
    file_path = f"C:\IIT_Jodhpur\BTP\Blockchain_BTP-main\SWaT.A1 & A2_Dec 2015-20241130T113652Z-001\SWaT.A1 & A2_Dec 2015\Physical\SWaT_Dataset_Attack_v0.xlsx"

    # Open the CSV file
    print(f"Reading data from {file_path}")
    data = pd.read_excel(file_path, header=0)
    print(f"Data sending started")

    # Iterate over each row in the DataFrame
    for _, row in data.iloc[1100:].iterrows():
        # Accessing timestamp (UTC time) and RSRQ values based on your data
        timestamp = row[0]  # UTC column
        value = row[2]
        status = row[52]
        if status == "Normal" and nodeid != "16919327":
            print(f"The timestamp is {timestamp} and the value is {value}")
            message = {
                "type": "Sensor_data",
                "timestamp": timestamp,
                "Value": value,
                "nodeid": nodeid,
                "nodeip": nodeip,
                "nodeport": nodeport,
                "Tconf": random.randint(7, 10),
                "Status": status,
            }

            # Sending the message to all clients
            send_all_clients(json.dumps(message).encode(), None)

            # Sleep for 1 second between each row
        else:
            print(f"The timestamp is {timestamp} and the value is {value}")
            message = {
                "type": "Sensor_data",
                "timestamp": timestamp,
                "Value": value,
                "nodeid": nodeid,
                "nodeip": nodeip,
                "nodeport": nodeport,
                "Tconf": random.randint(7, 10),
                "Status": status,
            }

            # Sending the message to all clients
            send_all_clients(json.dumps(message).encode(), None)

            # Sleep for 1 second between each row
            sleep(1)


# Main function
def main(ip, port, node_id):
    global clients, output_file, nodeip, nodeport, nodeid
    nodeip = ip
    nodeport = port
    nodeid = node_id
    # create the output file for each seed node
    output_file = f"bin/servers/output_{node_id}.txt"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((ip, port))

        # write the address of the seed node to the output file
        with open(output_file, "w") as f:
            print("Server is running on {}:{}".format(ip, port), file=f)

        # start a new thread to accept the peers for that particular seed node
        start_new_thread(accept_clients, (sock, clients))

        start_new_thread(send_sens_data, ())

        while True:
            sleep(5)
            print("Server is alive")


if __name__ == "__main__":
    main("127.0.0.1", int(sys.argv[1]), sys.argv[2])
    nodeip = "127.0.0.1"
    nodeport = int(sys.argv[1])
    nodeid = sys.argv[2]
