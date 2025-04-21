from p4utils.utils.topology import NetworkGraph
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
from p4utils.utils.helper import load_topo
from scapy.all import sniff, Packet, Ether, IP, UDP, TCP, BitField, Raw
from crc import Crc

import threading
import struct
import random
import socket
import time


# P4 SWITCH ACTION TABLE NAMES DEFINITIONS
INGRESS_LOOKUP_TABLE = "ingress_lookup_table"
EGRESS_LOOKUP_TABLE = "egress_lookup_table"

VTABLE_NAME_PREFIX = 'vt'
VTABLE_SLOT_SIZE = 8   # in bytes
VTABLE_ENTRIES = 65536

CONTROLLER_MIRROR_SESSION = 100
RECIRCULATION_COUNT = 1

NETCACHE_READ_QUERY = 0
NETCACHE_WRITE_QUERY = 1
NETCACHE_FLUSH_QUERY = 2
NETCACHE_INIT_QUERY = 6
NETCACHE_VALUE_SIZE = 2048

UNIX_CHANNEL = '/tmp/server_cont.s'
CACHE_INSERT_COMPLETE = 'INSERT_OK'


class NetcacheHeader(Packet):
    name = 'NcachePacket'
    fields_desc = [BitField('op', 0, 8), BitField('seq', 0, 32),
            BitField('key', 0, 128), BitField('value', 0, NETCACHE_VALUE_SIZE), BitField('value2', 0, NETCACHE_VALUE_SIZE)]


class NCacheController(object):

    def __init__(self, sw_name, vtables_num=16):
        self.topo = load_topo('../p4/topology.json')
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(self.sw_name)
        self.cpu_port = self.topo.get_cpu_port_index(self.sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)

        self.vtables = []
        self.vtables_num = vtables_num


        # create a pool of ids (as much as the total amount of keys)
        # this pool will be used to assign index to keys which will be
        # used to index the cached key counter and the validity register
        self.ids_pool = range(0, VTABLE_ENTRIES)

        # array of bitmap, which marks available slots per cache line
        # as 0 bits and occupied slots as 1 bits
        self.mem_pool = [0] * VTABLE_ENTRIES

        # dictionary storing the value table index, bitmap and counter/validity
        # register index in the P4 switch that corresponds to each key
        self.key_map = {}

        self.setup()


    def inform_server(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(UNIX_CHANNEL)
        except socket.error as msg:
            #print('Error: Unable to contact server for cache operation completion')
            return

        sock.sendall(CACHE_INSERT_COMPLETE)

    def setup(self):
        if self.cpu_port:
            self.controller.mirroring_add(CONTROLLER_MIRROR_SESSION, self.cpu_port)


    # set a static allocation scheme for l2 forwarding where the mac address of
    # each host is associated with the port connecting this host to the switch
    def set_forwarding_table(self):
        for host in self.topo.get_hosts_connected_to(self.sw_name):
            port = self.topo.node_to_node_port_num(self.sw_name, host)
            host_mac = self.topo.get_host_mac(host)
            self.controller.table_add("l2_forward", "set_egress_port", [str(host_mac)], [str(port)])


    def set_value_tables(self):
        for i in range(self.vtables_num):
            self.controller.table_add("vtable_" + str(i), "process_array_" + str(i), ['1'], [])


    # this function manages the mapping between between slots in register arrays
    # and the cached items by implementing the First Fit algorithm described in
    # Memory Management section of 4.4.2 (netcache paper)
    def first_fit(self, key, value_size):
        n_idx = 2
        if value_size <= 0:
            return None
        if key in self.key_map:
            return None
        for idx in range(len(self.mem_pool) - n_idx + 1):
            if self.mem_pool[idx] == 0:
                for jdx in range(n_idx):
                    self.mem_pool[idx + jdx] = 1
                return idx
        return None


    # converts a list of 1s and 0s represented as strings and converts it
    # to a bitmap using bitwise operations (this intermediate representation
    # of a list of 1s and 0s is used to avoid low level bitwise logic inside
    # core implementation logic)
    def convert_to_bitmap(self, strlist, bitmap_len):
        bitmap = 0
        # supports only bitmaps with multiple of 8 bits size
        if bitmap_len % 8 != 0:
            return bitmap
        for i in strlist:
            bitmap = bitmap << 1
            bitmap = bitmap | int(i)

        return bitmap


    # this function checks whether the k-th bit of a given number is set
    def bit_is_set(self, n, k):
        if n & (1 << k):
            return True
        else:
            return False


    # given a key and its associated value, we update the lookup table on
    # the switch and we also update the value registers with the value
    # given as argument (stored in multiple slots)
    def insert(self, key, value, cont=True):
        # find where to put the value for given key
        mem_info = self.first_fit(key, len(value))
        # if key already exists or not space available then stop
        if mem_info == None:
            return
        vt_index = mem_info
        # keep track of number of bytes of the value written so far
        cnt = 0
        # store the value of the key in the vtables of the switch while
        # incrementally storing a part of the value at each value table
        # if the correspoding bit of the bitmap is set
        for h in range(0, RECIRCULATION_COUNT * 2, 2):
            for i in range(self.vtables_num):
                for j in range(2):
                    partial_val = value[cnt:cnt+VTABLE_SLOT_SIZE]
                    self.controller.register_write(VTABLE_NAME_PREFIX + str(i),
                            vt_index + j + h, self.str_to_int(partial_val))

                    cnt += VTABLE_SLOT_SIZE

        # allocate an id from the pool to index the counter and validity register
        # (we take the last element of list because in python list is implemented
        # to optimize for inserting and removing elements from the end of the list)
        ids_pool_list = list(self.ids_pool)
        key_index = ids_pool_list.pop()
        self.ids_pool = range(len(ids_pool_list))
    
        bitmap = 0b11111111
        # add the new key to the cache lookup table of the p4 switch
        self.controller.table_add(INGRESS_LOOKUP_TABLE, "ingress_set_lookup_metadata",
            [str(self.str_to_int(key[8:]))], [str(bitmap), str(vt_index), str(key_index)])
        self.controller.table_add(EGRESS_LOOKUP_TABLE, "egress_set_lookup_metadata",
            [str(self.str_to_int(key[8:]))], [str(bitmap), str(vt_index), str(key_index)])

        # mark cache entry for this key as valid
        self.controller.register_write("ingress_cache_status", key_index, 1)
        self.controller.register_write("egress_cache_status", key_index, 1)

        self.key_map[key] = vt_index, bitmap, key_index

        # inform the server about the successful cache insertion
        if cont:
            self.inform_server()
        print(f"Inserted key-value pair to cache: ({str(key[8:])}, {str(value)}) ")


    # converts a string to a bytes representation and afterwards returns
    # its integer representation of width specified by argument int_width
    # (seems hacky due to restriction to use python2.7)
    def str_to_int(self, x, int_width=VTABLE_SLOT_SIZE):
        # Ensure that the length of the string doesn't exceed int_width
        if len(x) > int_width:
            print(f"Error: Overflow while converting string {x} to int")

        # Add padding with 0x00 if input string size is less than int_width
        bytearr = bytearray(int_width - len(x))

        if isinstance(x, str):  # If x is a string, encode it
            bytearr.extend(x.encode('utf-8'))
        elif isinstance(x, bytes):  # If x is already bytes, directly extend
            bytearr.extend(x)
        else:
            raise ValueError("Expected input to be either string or bytes")

        # Return the integer representation of the packed bytearray
        return struct.unpack(">q", bytearr)[0]


    # given an arbitrary sized integer, the max width (in bits) of the integer
    # it returns the string representation of the number (also stripping it of
    # any '0x00' characters) (network byte order is assumed)
    def int_to_packed(self, int_val, max_width=128, word_size=32):
        num_words = max_width // word_size  # Use integer division
        words = self.int_to_words(int_val, num_words, word_size)

        fmt = '>%dI' % (num_words)  # Format for struct.pack, assuming words are unsigned ints
        packed_data = struct.pack(fmt, *words)

        # Strip the trailing null bytes correctly for a bytes object
        return packed_data.rstrip(b'\x00')  # Ensure null bytes are stripped correctly


    # split up an arbitrary sized integer to words (needed to hack
    # around struct.pack limitation to convert to byte any integer
    # greater than 8 bytes)
    def int_to_words(self, int_val, num_words, word_size):
        max_int = 2 ** (word_size*num_words) - 1
        max_word_size = 2 ** word_size - 1
        words = []
        for _ in range(int(num_words)):
            word = int_val & max_word_size
            words.append(int(word))
            int_val >>= word_size
        words.reverse()
        return words


    # flush the entire kv cache
    def flush(self):
        '''
        for key in list(self.key_map.keys()):
            # delete entry from the lookup_table
            entry_handle = self.controller.get_handle_from_match(
                    NETCACHE_LOOKUP_TABLE, [str(self.str_to_int(key)), ])

            if entry_handle is not None:
                self.controller.table_delete(NETCACHE_LOOKUP_TABLE, entry_handle)

            # delete mapping of key from controller's dictionary
            vt_idx, bitmap, key_idx = self.key_map[key]
            del self.key_map[key]

            # deallocate space from memory pool
            self.mem_pool[vt_idx] = self.mem_pool[vt_idx] ^ bitmap

            # free the id used to index the validity/counter register and append
            # it back to the id pool of the controller
            self.ids_pool.append(key_idx)

            # mark cache entry as valid again (should be the last thing to do)
            self.controller.register_write("cache_status", key_idx, 1)
        '''

    # handling reports from the switch corresponding to hot keys, updates to
    # key-value pairs or deletions - this function receives a packet, extracts
    # its netcache header and manipulates cache based on the operation field
    # of the netcache header (callback function)
    def recv_switch_updates(self, pkt):
        #print("Received message from switch")

        # extract netcache header information
        if pkt.haslayer(UDP):
            ncache_header = NetcacheHeader(bytes(pkt[UDP].payload))
        elif pkt.haslayer(TCP):
            ncache_header = NetcacheHeader(pkt[TCP].payload)

        key = self.int_to_packed(ncache_header.key, max_width=128)
        value = self.int_to_packed(ncache_header.value, max_width=NETCACHE_VALUE_SIZE)

        op = ncache_header.op

        if op == NETCACHE_WRITE_QUERY:
            #print("Received write for key = " + str(key))
            self.insert(key, value)

        elif op == NETCACHE_FLUSH_QUERY:
            print("Received query to flush")
            self.flush()

        else:
            print("Error: unrecognized operation field of netcache header")


    # sniff infinitely the interface connected to the P4 switch and when a valid netcache
    # packet is captured, handle the packet via a callback to recv_switch_updates function
    def hot_reports_loop(self):
        cpu_port_intf = str(self.topo.get_cpu_port_intf(self.sw_name))
        sniff(iface=cpu_port_intf, prn=self.recv_switch_updates, filter="port 50000")

    def dummy_populate_vtables(self):
        test_keys_l = "0000000012345678"
        test_values_512 = "aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffffgggggggghhhhhhhhiiiiiiiijjjjjjjjkkkkkkkkllllllllmmmmmmmmnnnnnnnnooooooooppppppppqqqqqqqqrrrrrrrrssssssssttttttttuuuuuuuuvvvvvvvvwwwwwwwwxxxxxxxxyyyyyyyyzzzzzzzz111111112222222233333333444444445555555566666666666666665555555544444444333333332222222211111111zzzzzzzzyyyyyyyyxxxxxxxxwwwwwwwwvvvvvvvvuuuuuuuuttttttttssssssssrrrrrrrrqqqqqqqqppppppppoooooooonnnnnnnnmmmmmmmmllllllllkkkkkkkkjjjjjjjjiiiiiiiihhhhhhhhggggggggffffffffeeeeeeeeddddddddccccccccbbbbbbbbaaaaaaaa"
        test_values_256 = "aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffffgggggggghhhhhhhhiiiiiiiijjjjjjjjkkkkkkkkllllllllmmmmmmmmnnnnnnnnooooooooppppppppqqqqqqqqrrrrrrrrssssssssttttttttuuuuuuuuvvvvvvvvwwwwwwwwxxxxxxxxyyyyyyyyzzzzzzzz111111112222222233333333444444445555555566666666"
        test_values_128 = "aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffffgggggggghhhhhhhhiiiiiiiijjjjjjjjkkkkkkkkllllllllmmmmmmmmnnnnnnnnoooooooopppppppp"
        self.insert(test_keys_l, test_values_256, False)


    def main(self):
        self.set_forwarding_table()
        self.set_value_tables()
        self.dummy_populate_vtables()


if __name__ == "__main__":
    controller1 = NCacheController('s1').main()
    controller2 = NCacheController('s2').main()
    controller3 = NCacheController('s3').main()
    controller3 = NCacheController('s4').main()
    controller3 = NCacheController('s5').main()
    controller3 = NCacheController('s6').main()
    controller3 = NCacheController('s7').main()
    controller3 = NCacheController('s8').main()
    controller3 = NCacheController('s9').main()
