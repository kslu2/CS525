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

NUM_SWITCH = 6


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
        os.system("for ip in $(arp -n | awk '{print $1}' | tail -n +2); do arp -d $ip; done")
        os.system("arp -s 10.0.0.1 00:00:0a:00:00:01 -i client1-eth0")
        os.system("arp -s 10.0.0.2 00:00:0a:00:00:02 -i client1-eth1")
        os.system("arp -s 10.0.0.3 00:00:0a:00:00:03 -i client1-eth2")
        os.system("arp -s 10.0.0.4 00:00:0a:00:00:04 -i client1-eth3")
        os.system("arp -s 10.0.0.5 00:00:0a:00:00:05 -i client1-eth4")
        os.system("arp -s 10.0.0.6 00:00:0a:00:00:06 -i client1-eth5")
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
        
        self.sock_s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_s2.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'client1-eth1')

        self.sock_s3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_s3.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'client1-eth2')

        self.sock_s4 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_s4.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'client1-eth3')

        self.sock_s5 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_s5.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'client1-eth4')

        self.sock_s6 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_s6.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'client1-eth5')

        # store all latencies of the requests sent (used for evaluation)
        self.latencies = []

    def read(self, key, seq=0, suppress=False):
        self.request_received += 1
        msg = build_message(NETCACHE_READ_QUERY, key, seq)
        if msg is None:
            return

        if self.request_received % NUM_SWITCH == 0:
            sock = self.sock_s1
            sock.sendto(msg, ("10.0.0.1", self.port))
        elif self.request_received % NUM_SWITCH == 1:
            sock = self.sock_s2
            sock.sendto(msg, ("10.0.0.2", self.port))
        elif self.request_received % NUM_SWITCH == 2:
            sock = self.sock_s3
            sock.sendto(msg, ("10.0.0.3", self.port))
        elif self.request_received % NUM_SWITCH == 3:
            sock = self.sock_s4
            sock.sendto(msg, ("10.0.0.4", self.port))
        elif self.request_received % NUM_SWITCH == 4:
            sock = self.sock_s5
            sock.sendto(msg, ("10.0.0.5", self.port))
        else:
            sock = self.sock_s6
            sock.sendto(msg, ("10.0.0.6", self.port))
            time.sleep(0.002)

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
