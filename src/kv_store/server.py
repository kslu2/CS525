from collections import deque

import socket
import logging
import threading
import time
import sys
import os

STATISTICS_REFRESH_INTERVAL = 30.0

NETCACHE_PORT = 50000
NOCACHE_PORT = 50001

NETCACHE_READ_FAIL = 3
NETCACHE_WRITE_QUERY = 1
NETCACHE_READ_QUERY = 0

NETCACHE_REQUEST_SUCCESS = 10
NETCACHE_KEY_NOT_FOUND = 20

NETCACHE_VALUE_SIZE = 512



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
        # server ip address
        self.host = host
        # server name
        self.name = 'server' + self.host.split('.')[-1]

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

        # unix socket for out of band communication with controller
        # (used for cache coherency purposes)
        self.unixss = None


    def activate(self):

        # enable logging for debuggin purposes
        logging.basicConfig(
                filename='log/{}.log'.format(self.name),
                format='%(asctime)s %(levelname)-8s %(message)s',
                level=logging.DEBUG,
                datefmt='%d-%m-%Y %H:%M:%S')

        # create udp socket server
        self.udpss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpss.bind((self.host, self.port))

        # create tcp socket server
        self.tcpss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcpss.bind((self.host, self.port))
        self.tcpss.listen(1)

        # spawn new thread that serves incoming udp (read) queries
        server_udp_t = threading.Thread(target=self.handle_client_udp_request)
        server_udp_t.start()

        # spawn new thread that serves incoming tcp (put/delete) queries
        server_tcp_t = threading.Thread(target=self.handle_client_tcp_request)
        server_tcp_t.start()

        # self.periodic_request_report()

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
    def handle_client_udp_request(self):

        while True:

            # if server is not currently blocking updates/writes then if there are
            # requests waiting in the queue then serve those requests, elsewise
            # serve the new incoming packet
            if len(self.incoming_requests) > 0:
                netcache_pkt, addr = self.incoming_requests.popleft()
            else:
                netcache_pkt, addr = self.udpss.recvfrom(1024)

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
            value = value.decode("utf-8")

            if op == NETCACHE_READ_FAIL:
                logging.info('Received READ_FAIL(' + key + ') from client ' + addr[0])

                if not self.suppress:
                    print('[{}] Received READ_FAIL({}) from client {}'.format(self.name, key, addr[0]))

                #simulate operation
                op_res = 0
                if key == 'times':
                    op_res = '123456789'
                    time.sleep(1)

                msg = build_message(NETCACHE_WRITE_QUERY, key_s, seq, op_res)
                self.udpss.sendto(msg, addr)

                msg = build_message(NETCACHE_REQUEST_SUCCESS, key_s, seq, op_res)
                self.udpss.sendto(msg, addr)


            elif op == NETCACHE_READ_QUERY:
                logging.info('Received READ_SUCCESS(' + key + ') from client ' + addr[0])

                if not self.suppress:
                    print('[{}] Received READ_SUCCESS({}) from client {}'.format(self.name, key, addr[0]))

                msg = build_message(NETCACHE_REQUEST_SUCCESS, key_s, seq, value)
                self.udpss.sendto(msg, addr)

            elif op == NETCACHE_WRITE_QUERY:
                logging.info('Received WRITE_SUCCESS(' + key + ') from client ' + addr[0])

                if not self.suppress:
                    print('[{}] Received WRITE_SUCCESS({}) from client {}'.format(self.name, key, addr[0]))

            else:
                logging.info('Unsupported/Invalid query type received from client ' + addr[0])
                print('Unsupported query type (received op = ' + str(op) + ')')


    # serves incoming tcp queries (i.e. put/delete)
    def handle_client_tcp_request(self):

        while True:

            conn, addr = self.tcpss.accept()

            netcache_pkt = conn.recv(1024)

            op = netcache_pkt[0]
            seq = netcache_pkt[1:5]
            key = netcache_pkt[5:21]
            value = netcache_pkt[21:]

            #transform key to int
            key_s = int.from_bytes(key,'big')
            seq = int.from_bytes(seq, 'big')

            #transform val to string
            value = value.decode("utf-8")
            #transform key to string
            key = key.decode("utf-8").lstrip('\x00')


            if op == NETCACHE_WRITE_QUERY:
                logging.info('Received WRITE_SUCCESS(' + key + ') from client ' + addr[0])

                if not self.suppress:
                    print('[{}] Received WRITE_SUCCES({}) from client {}'.format(self.name, key, addr[0]))

            else:
                logging.info('Unsupported query type received from client '
                        + addr[0] + ":" + str(addr[1]))



def main(disable_cache, suppress_output, input_files):

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
    parser.add_argument('--input', help='input files to prepopulate server', required=False, nargs="*")
    args = parser.parse_args()

    main(args.disable_cache, args.suppress_output, args.input)
