import hashlib
import time
from numpy import random
import random as random_module


class Block:
    def __init__(self, timestamp, data, previous_hash, random_number="0"):
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.difficulty = 2
        self.random_number = random_number
        if random_number == "0":
            self.hash = self.hash_block()

    @classmethod
    def from_dict(cls, block_dict):
        new_block = cls(
            block_dict["timestamp"],
            block_dict["data"],
            block_dict["previous_hash"],
            block_dict["random_number"],
        )
        new_block.hash = block_dict["hash"]
        return new_block

    def hash_block(self):
        # take difficulty to be first 2 character of hash to be 0
        sha = hashlib.sha256()
        while True:
            sha.update(
                str(self.timestamp).encode("utf-8")
                + str(self.data).encode("utf-8")
                + str(self.random_number).encode("utf-8")
                + str(self.previous_hash).encode("utf-8")
            )
            if sha.hexdigest()[: self.difficulty] == "0" * self.difficulty:
                return sha.hexdigest()
            self.random_number = random_module.getrandbits(64)

    @staticmethod
    def check_difficulty(hash):
        # print(f"Checking difficulty for hash: {hash}")
        # check how many leading 0s are there in the hash
        cnt = 0
        for i in hash:
            if i == "0":
                cnt += 1
            else:
                break
        return cnt

    @staticmethod
    def ghast_weight(hash):
        cnt = 0
        for i in hash:
            if i == "0":
                cnt += 1
            else:
                break
        return 2 ** (cnt - 2)

    def __dict__(self):
        return {
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "random_number": self.random_number,
        }


class BlockChain:
    def __init__(self, name, hashPower, init_blocks_file):
        self.chain = []
        self.height_map = {}
        self.graph = {}
        self.subtree_size = {}
        self.owner_map = {}
        self.parent_map = {}
        self.longest_chain_length = 1
        self.ghast_weights = {}
        self.longest_chain_hash = (
            "0038e8a8063ea575068bb0ccebe242a42ba2c1e45204e4f37bb87ea8364cfa9e"
        )
        self.name = name
        self.init_blocks_file = init_blocks_file
        self.hashPower = hashPower

        # self.create_genesis_block()
        self.init_csv_file()
        self.get_previous_blocks()

    def GHAST_chain(self):
        ghast_longest_chain = []
        init = "0"
        ghast_longest_chain.append(init)
        ghast_enabled = False
        while init in self.graph:
            maxa_subtree_size = 0
            total_subtree_size = 0
            maxa_node = None
            if not ghast_enabled:
                for child in self.graph[init]:
                    if self.subtree_size[child] > maxa_subtree_size:
                        maxa_subtree_size = self.subtree_size[child]
                        maxa_node = child
                    elif (
                        self.subtree_size[child] == maxa_subtree_size
                        and child < maxa_node
                    ):
                        maxa_node = child
                    total_subtree_size += self.subtree_size[child]

            # if not total majority apply ghast_weights
            if maxa_subtree_size <= total_subtree_size / 2 or ghast_enabled:
                ghast_enabled = True
                maxa_subtree_size = 0
                maxa_node = None
                for child in self.graph[init]:
                    if self.ghast_weights[child] > maxa_subtree_size:
                        maxa_subtree_size = self.ghast_weights[child]
                        maxa_node = child
                    elif (
                        self.ghast_weights[child] == maxa_subtree_size
                        and child < maxa_node
                    ):
                        maxa_node = child

            init = maxa_node
            ghast_longest_chain.append(init)

        return ghast_longest_chain

    def init_csv_file(self):
        self.csv_file = f"./bin/blockchain/blockchain_{self.name}.csv"
        with open(self.csv_file, "w") as f:
            f.write("Timestamp,Previous Hash,Hash,Random Number,Owner\n")

    def get_previous_blocks(self):
        with open(self.init_blocks_file, "r") as f:
            blocks = f.readlines()

        first = True
        for block in blocks:
            if first:
                first = False
                continue
            block = block.strip().split(",")
            print("Previous_Block", block)
            new_block = Block(block[0], block[1], block[2], block[3])
            new_block.data = "data"
            new_block.timestamp = block[0]
            new_block.previous_hash = block[1]
            new_block.hash = block[2]
            new_block.random_number = block[3]
            self.add_block(new_block, block[4])

    def validate_block(self, block):

        if (
            block.hash not in self.height_map
            and block.previous_hash in self.height_map
            and Block.check_difficulty(block.hash) >= 2
        ):
            return True
        print(f"Previous hash: {block.previous_hash}")
        print(f"Block hash: {block.hash}")
        print(f"Block difficulty: {Block.check_difficulty(block.hash)}")
        print(f"Height map: {self.height_map}")
        print(f"Block hash not in height map: {block.hash not in self.height_map}")
        print(
            f"Block previous hash in height map: {block.previous_hash in self.height_map}"
        )
        print(f"Block difficulty >= 2: {Block.check_difficulty(block.hash) >= 2}")
        return False

    def add_block(self, block: Block, owner):
        if len(self.height_map) == 0:
            self.height_map[block.hash] = 1
            self.owner_map[block.hash] = owner
            self.chain.append(block)
            self.write_block_to_csv(block)
            self.longest_chain_hash = block.hash
            self.longest_chain_length = 1
            self.subtree_size[block.hash] = 1
            self.ghast_weights[block.hash] = Block.ghast_weight(block.hash)
            self.graph[block.previous_hash] = self.graph.get(block.previous_hash, set())
            self.graph[block.previous_hash].add(block.hash)
            return True

        if self.validate_block(block):
            self.chain.append(block)
            self.height_map[block.hash] = self.height_map[block.previous_hash] + 1
            self.owner_map[block.hash] = owner
            self.subtree_size[block.hash] = 1
            self.parent_map[block.hash] = block.previous_hash
            self.graph[block.previous_hash] = self.graph.get(block.previous_hash, set())
            self.graph[block.previous_hash].add(block.hash)
            self.ghast_weights[block.hash] = Block.ghast_weight(block.hash)

            parent = block.previous_hash
            while parent != "0":
                if parent not in self.subtree_size:
                    self.subtree_size[parent] = 0
                    self.ghast_weights[parent] = 0
                self.subtree_size[parent] += 1
                self.ghast_weights[parent] += self.ghast_weights[block.hash]
                if parent not in self.parent_map:
                    break
                parent = self.parent_map[parent]

            ghost_chain = self.GHAST_chain()
            self.longest_chain_length = len(ghost_chain)
            self.longest_chain_hash = ghost_chain[-1]

            self.write_block_to_csv(block)
            return True
        # else:
        #     print("Block validation failed")

        return False

    def mine_block(self, data):
        print(self.longest_chain_hash, "longest_chain_hash")
        new_block = Block(time.asctime(time.localtime()), data, self.longest_chain_hash)
        print(new_block.hash, "mined_block")
        self.add_block(new_block, self.name)
        return new_block

    def write_block_to_csv(self, block: Block):
        with open(self.csv_file, "a") as f:
            f.write(
                f"{block.timestamp},{block.previous_hash},{block.hash},{block.random_number},{self.owner_map[block.hash]}\n"
            )

    def tauGenerator(self):
        return random.exponential(1 / self.hashPower)

    def get_longest_chain_hash(self):
        return self.longest_chain_hash

    # Destructor
    def __del__(self):
        file = f"./bin/metadata/{self.name}.txt"
        with open(file, "w") as f:
            f.write(f"{self.longest_chain_hash},{self.longest_chain_length}")
            f.write("\n")
            f.write(f"total blocks: {len(self.chain)}")
