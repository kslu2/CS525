import socket
import time
import sys

NETCACHE_PORT = 50000
NOCACHE_PORT = 50001

MAX_SUPPORTED_SERVERS = 254

NETCACHE_READ_QUERY = 0
NETCACHE_FLUSH_QUERY = 2

NETCACHE_VALUE_SIZE = 512

NETCACHE_KEY_NOT_FOUND = 20


def convert(val):
	return int.from_bytes(bytes(val, "utf-8"), "big")

def build_message(op, key, seq=0, value = ""):

    msg = bytearray()
    msg += op.to_bytes(1, 'big')
    msg += seq.to_bytes(4, 'big')

    if len(key) <= 8:
        msg += convert(key).to_bytes(16, 'big')
    else:
        print("Error: Key should be up to 8 bytes")
        return None

    if len(value) <= NETCACHE_VALUE_SIZE:
        msg += convert(value).to_bytes(NETCACHE_VALUE_SIZE, 'big')
    else:
        print(f"Error: Value should be up to {NETCACHE_VALUE_SIZE} bytes")
        return None
    return msg


class NetCacheClient:

    def __init__(self, n_servers=1, no_cache=False):
        self.n_servers = n_servers
        self.servers = []

        if no_cache:
            self.port = NOCACHE_PORT
        else:
            self.port = NETCACHE_PORT

        self.udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.get_servers_ips()

        # store all latencies of the requests sent (used for evaluation)
        self.latencies = []


    # the IP addresses assigned to servers are based on the assignment
    # strategy defined at the p4app.json file; the basic l2 strategy
    # that we are using assigns IP addresses starting from 10.0.0.1
    # and assigns incrementing addresses to defined hosts
    def get_servers_ips(self):
        if self.n_servers > MAX_SUPPORTED_SERVERS:
            print("Error: Exceeded maximum supported servers")
            sys.exit()

        for i in range(self.n_servers):
            self.servers.append("10.0.0." + str(i+1))

    # return the right node who contains the given key - our implementation
    # is based on client side partitioning i.e the client directly sends
    # the message to the correct node
    # TODO:1(dimlek): implement consistent hashing partitioning
    # TODO:2(dimlek): explore option of proxy assisted partitioning
    def get_node(self, key, partition_scheme='range'):

        if partition_scheme == 'range':
            # find the right node through range partitioning based on 1st key character
            first_letter = ord(key[0])
            return self.servers[first_letter % self.n_servers]

        elif partition_scheme == 'hash':
            return self.servers[hash(key) % self.n_servers]

        elif partition_scheme == 'consistent-hash':
            # TODO(dimlek): impelement consistent hashing partitioning
            pass

        else:
            print("Error: Invalid partitioning scheme")
            sys.exit()

        return -1


    def read(self, key, seq=0, suppress=False):
        msg = build_message(NETCACHE_READ_QUERY, key, seq)
        if msg is None:
            return

        start_time = time.time()

        self.udps.connect((self.get_node(key), self.port))
        self.udps.send(msg)

        data = self.udps.recv(1024)
        op = data[0]

        latency = time.time() - start_time
        self.latencies.append(latency)

        if suppress:
            return

        if op == NETCACHE_KEY_NOT_FOUND:
            print('Error: Key not found (key = ' + key + ')')
        else:
            val = data[21:].decode("utf-8")
            print(val)


    def flush(self, key, seq = 0):
        msg = build_message(NETCACHE_FLUSH_QUERY, key, seq)
        if msg is None:
            return

        tcps = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcps.connect((self.get_node(key), self.port))

        start_time = time.time()

        tcps.send(msg)
        status = tcps.recv(1024)

        latency = time.time() - start_time
        self.latencies.append(latency)

        if status[0] == NETCACHE_KEY_NOT_FOUND:
            print('Error: Key not found (key = ' + key + ')')

        tcps.close()
