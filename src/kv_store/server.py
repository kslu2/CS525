from collections import deque

import socket
import logging
import threading
import time
import sys
import os
import struct

STATISTICS_REFRESH_INTERVAL = 30.0

NETCACHE_PORT = 50000
NOCACHE_PORT = 50001

NETCACHE_READ_FAIL = 3
NETCACHE_WRITE_QUERY = 1
NETCACHE_READ_QUERY = 0
NETCACHE_INIT_QUERY = 6

NUM_SWITCH = 6

NETCACHE_REQUEST_SUCCESS = 10
NETCACHE_KEY_NOT_FOUND = 20

NETCACHE_VALUE_SIZE = 256

def convert(val):
    return int.from_bytes(bytes(val, "utf-8"), "big")

def build_message(op, key, seq=0, value = ""):

    msg = bytearray()
    msg += op.to_bytes(1, 'big')
    msg += seq.to_bytes(4, 'big')
    msg += key.to_bytes(16, 'big')
    msg += convert(value).to_bytes(NETCACHE_VALUE_SIZE, 'big')

    return msg

class KVServer:

    def __init__(self, host, nocache=False, suppress=False, max_listen=10):
        os.system("sysctl -w net.ipv4.conf.server1-eth0.rp_filter=0")
        os.system("sysctl -w net.ipv4.conf.server1-eth1.rp_filter=0")
        os.system("sysctl -w net.ipv4.conf.server1-eth2.rp_filter=0")
        os.system("sysctl -w net.ipv4.conf.server1-eth3.rp_filter=0")
        os.system("sysctl -w net.ipv4.conf.server1-eth4.rp_filter=0")
        os.system("sysctl -w net.ipv4.conf.server1-eth5.rp_filter=0")
        # server ip address
        self.host1 = '0.0.0.0'
        # self.host2 = host.split(' ')[1]
        # self.host3 = host.split(' ')[2]
        # self.host4 = host.split(' ')[3]
        # self.host5 = host.split(' ')[4]
        # server name
        self.name = 'server1'

        # port server is listening to
        if nocache:
            self.port = NOCACHE_PORT
        else:
            self.port = NETCACHE_PORT

        # suppress printing messages
        self.suppress = suppress
        # udp server socket
        self.udpss = None
        #tcp server socket
        self.tcpss = None
        # max clients to listen to
        self.max_listen = max_listen
        # queue to store incoming requests while blocking
        self.incoming_requests = deque()
        self.success_count = 0
        # unix socket for out of band communication with controller
        # (used for cache coherency purposes)
        self.unixss = None

        self.total_time = 0

    def activate(self):

        # enable logging for debuggin purposes
        logging.basicConfig(
                filename='log/{}.log'.format(self.name),
                format='%(asctime)s %(levelname)-8s %(message)s',
                level=logging.DEBUG,
                datefmt='%d-%m-%Y %H:%M:%S')

        # create udp socket server
        self.udpss1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpss1.bind((self.host1, self.port))

        # self.udpss2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.udpss2.bind((self.host2, self.port))

        # self.udpss3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.udpss3.bind((self.host3, self.port))

        # self.udpss4 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.udpss4.bind((self.host4, self.port))

        # self.udpss5 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.udpss5.bind((self.host5, self.port))

        # create tcp socket server
        #self.tcpss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.tcpss.bind((self.host1, self.port))
        #self.tcpss.listen(1)

        # spawn new thread that serves incoming udp (read) queries
        server_udp_t1 = threading.Thread(target=self.handle_client_udp_request, args=(self.udpss1, ))
        server_udp_t1.start()
        # server_udp_t2 = threading.Thread(target=self.handle_client_udp_request, args=(self.udpss2, ))
        # server_udp_t2.start()
        # server_udp_t3 = threading.Thread(target=self.handle_client_udp_request, args=(self.udpss3, ))
        # server_udp_t3.start()
        # server_udp_t4 = threading.Thread(target=self.handle_client_udp_request, args=(self.udpss4, ))
        # server_udp_t4.start()
        # server_udp_t5 = threading.Thread(target=self.handle_client_udp_request, args=(self.udpss5, ))
        # server_udp_t5.start()

        # starting time of serving requests (used for throughput calculation)
        self.start_time = time.time()

    def create_controller_channel(self):
        try:
            os.unlink(UNIX_CHANNEL)
        except:
            if os.path.exists(UNIX_CHANNEL):
                print('Error: unlinking unix socket')
                sys.exit(1)

        self.unixss = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.unixss.bind(UNIX_CHANNEL)
        self.unixss.listen(1)

        # spawn new thread that servers requests from controller (out-of-band communication)
        server_cont_t = threading.Thread(target=self.handle_controller_request)
        server_cont_t.start()

    # handles incoming udp queries
    def handle_client_udp_request(self, sock):

        while True:
            # if server is not currently blocking updates/writes then if there are
            # requests waiting in the queue then serve those requests, elsewise
            # serve the new incoming packet
            netcache_pkt, addr = sock.recvfrom(1024)
            switch_num = int(addr[0].split(".")[-1]) % NUM_SWITCH
            if switch_num == 0:
                switch_num = NUM_SWITCH

            # netcache_pkt is an array of bytes belonging to incoming packet's data
            # the data portion of the packet represents the netcache header, so we
            # can extract all the fields defined in the netcache custom protocol
            op = netcache_pkt[0]
            seq = netcache_pkt[1:5]
            key = netcache_pkt[5:21]
            value = netcache_pkt[21:]
            #transform key to int
            key_s = int.from_bytes(key,'big')
            key = key.decode('utf-8').lstrip('\x00')
            seq = int.from_bytes(seq,'big')
            #transform val to string

            if op == NETCACHE_READ_QUERY:
                #self.total_time += float(time.time())
                self.success_count += 1
                #logging.info('Received READ_SUCCESS(' + str(self.total_time) + ') from client ' + addr[0] + ' success rate ' + str(self.success_count))

                if not self.suppress:
                    print('Received READ_SUCCESS() success count {} from switch {}'.format(str(self.success_count), str(switch_num)))
                
                if self.success_count % 2592 == 0:
                    print("All packets received")
                    print(f"Ending Time: {time.time()}")


            else:
                logging.info('Unsupported/Invalid query type received from client ' + addr[0])
                print('Unsupported query type (received op = ' + str(op) + ')')

def main(disable_cache, suppress_output):

    from subprocess import check_output

    # dynamically get the IP address of the server
    server_ip = check_output(['hostname', '--all-ip-addresses']).decode('utf-8').rstrip()
    server = KVServer(server_ip, nocache=disable_cache, suppress=suppress_output)
    server.activate()


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--disable-cache', help='do not use netcache', action='store_true')
    parser.add_argument('--suppress-output', help='supress output printing messages', action='store_true')
    args = parser.parse_args()

    main(args.disable_cache, args.suppress_output)
