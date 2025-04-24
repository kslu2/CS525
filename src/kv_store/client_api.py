import socket
import time
import sys
import grpc
import io
import os

NETCACHE_PORT = 50000
NOCACHE_PORT = 50001

MAX_SUPPORTED_SERVERS = 254

NETCACHE_READ_QUERY = 0

NETCACHE_VALUE_SIZE = 256

NETCACHE_KEY_NOT_FOUND = 20

NUM_SWITCH = 9


def convert(val):
	return int.from_bytes(bytes(val, "utf-8"), "big")

def build_message(op, key = "", seq=0, value = ""):

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
        self.request_received = 0
        self.successful_reads = 0
        self.servers = []

        if no_cache:
            self.port = NOCACHE_PORT
        else:
            self.port = NETCACHE_PORT

        self.sock_s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_s1.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'client1-eth0')

        # store all latencies of the requests sent (used for evaluation)
        self.latencies = []

    def read(self, key, seq=0, suppress=False):
        self.request_received += 1
        msg = build_message(NETCACHE_READ_QUERY, key, seq)
        if msg is None:
            return

        sock = self.sock_s1
        sock.sendto(msg, ("10.0.0.1", self.port))


        '''
        
        data = self.udps.recv(1024)
        op = data[0]

        latency = time.time() - start_time
        self.latencies.append(latency)
        if op == NETCACHE_KEY_NOT_FOUND:
            print('Error: Key not found (key = ' + key + ')')
        else:
            val = data[21:].decode("utf-8")
            #print(val)
            self.successful_reads += 1
            return val
        '''
        return None

    def request_latency_metric(self):
        total_latency = 0
        for i in self.latencies:
            total_latency += i
        average_latency = total_latency / len(self.latencies)
        print(f"Average Latency of sending message: {average_latency}")
