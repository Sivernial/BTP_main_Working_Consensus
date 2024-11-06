import hashlib
import time
from numpy import random


class Block:
    def __init__(self, timestamp, data, previous_hash):
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.hash_block()

    @classmethod
    def from_dict(cls, block_dict):
        new_block = cls(
            block_dict["timestamp"], block_dict["data"], block_dict["previous_hash"]
        )
        new_block.hash = block_dict["hash"]
        return new_block

    def hash_block(self):
        sha = hashlib.sha256()
        sha.update(
            str(self.timestamp).encode("utf-8")
            + str(self.data).encode("utf-8")
            + str(self.previous_hash).encode("utf-8")
        )
        return sha.hexdigest()

    def __dict__(self):
        return {
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
        }


class BlockChain:
    def __init__(self, name, hashPower, init_blocks_file):
        self.chain = []
        self.height_map = {}
        self.owner_map = {}
        self.longest_chain_length = 1
        self.longest_chain_hash = None
        self.name = name
        self.init_blocks_file = init_blocks_file
        self.hashPower = hashPower

        self.init_csv_file()
        self.get_previous_blocks()

    def init_csv_file(self):
        self.csv_file = f"bin/blockchain/blockchain_{self.name}.csv"
        with open(self.csv_file, "w") as f:
            f.write("Timestamp,Previous Hash,Hash,Owner\n")

    def get_previous_blocks(self):
        with open(self.init_blocks_file, "r") as f:
            blocks = f.readlines()

        first = True
        for block in blocks:
            if first:
                first = False
                continue
            block = block.strip().split(",")
            new_block = Block(block[0], block[1], block[2])
            new_block.data = "data"
            new_block.timestamp = block[0]
            new_block.previous_hash = block[1]
            new_block.hash = block[2]
            self.add_block(new_block, block[3])

    def create_genesis_block(self):
        genesis_block = Block("01/01/2017", "Genesis Block", "0")
        self.chain.append(genesis_block)
        self.height_map[genesis_block.hash] = 0
        self.owner_map[genesis_block.hash] = "Genesis Block"
        self.longest_chain_hash = genesis_block.hash

    def validate_block(self, block):
        if block.hash not in self.height_map and block.previous_hash in self.height_map:
            return True
        return False

    def add_block(self, block, owner):
        if len(self.height_map) == 0:
            self.height_map[block.hash] = 1
            self.owner_map[block.hash] = owner
            self.chain.append(block)
            self.write_block_to_csv(block)
            self.longest_chain_hash = block.hash
            self.longest_chain_length = 1
            return True

        if self.validate_block(block):
            self.chain.append(block)
            self.height_map[block.hash] = self.height_map[block.previous_hash] + 1
            self.owner_map[block.hash] = owner
            if self.height_map[block.hash] > self.longest_chain_length:
                self.longest_chain_length = self.height_map[block.hash]
                self.longest_chain_hash = block.hash

            elif self.height_map[block.hash] == self.longest_chain_length:
                if block.hash < self.longest_chain_hash:
                    self.longest_chain_hash = block.hash

            self.write_block_to_csv(block)
            return True
        print(self.longest_chain_hash)
        return False

    def mine_block(self, data):
        new_block = Block(time.asctime(time.localtime()), data, self.longest_chain_hash)
        print(self.longest_chain_hash)
        self.add_block(new_block, self.name)
        return new_block

    def write_block_to_csv(self, block):
        with open(self.csv_file, "a") as f:
            f.write(
                f"{block.timestamp},{block.previous_hash},{block.hash},{self.owner_map[block.hash]}\n"
            )

    def tauGenerator(self):
        return random.exponential(1 / self.hashPower)

    def get_longest_chain_hash(self):
        return self.longest_chain_hash

    # Destructor
    def __del__(self):
        file = f"bin/metadata/{self.name}.txt"
        with open(file, "w") as f:
            f.write(f"{self.longest_chain_hash},{self.longest_chain_length}")
            f.write("\n")
            f.write(f"total blocks: {len(self.chain)}")
