import socket
import time
import sys
import grpc
import io

NETCACHE_PORT = 50000
NOCACHE_PORT = 50001

MAX_SUPPORTED_SERVERS = 254

NETCACHE_READ_QUERY = 0
NETCACHE_FLUSH_QUERY = 2
NETCACHE_INIT_QUERY = 6

NETCACHE_VALUE_SIZE = 256

NETCACHE_KEY_NOT_FOUND = 20

SYSTEM_PROMPT = "You are a helpful and informative AI assistant."



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
        self.servers = []

        if no_cache:
            self.port = NOCACHE_PORT
        else:
            self.port = NETCACHE_PORT

        self.udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.get_servers_ips()

        # store all latencies of the requests sent (used for evaluation)
        self.latencies = []

    def send_system_prompt(self, seq = 0):
        msg = build_message(NETCACHE_INIT_QUERY, "init", seq, SYSTEM_PROMPT)
        if msg is None:
            return

        start_time = time.time()
        self.udps.connect(('10.0.0.1', self.port))
        self.udps.send(msg)

        data = self.udps.recv(1024)
        op = data[0]

        latency = time.time() - start_time
        self.latencies.append(latency)

        if op == NETCACHE_KEY_NOT_FOUND:
            print('Error: Key not found (key = ' + key + ')')
        else:
            val = data[21:].decode("utf-8")
            print(val)

    def configure(self):

        # Load probe examples from the dataset.
        dataset_path = "hf://datasets/Naomibas/llm-system-prompts-benchmark/hundred_system_prompts.json"
        probes = load_probes(dataset_path)
        logger.info(f"Loaded {len(probes)} probes from dataset.")

        baseline_times = []
        kv_cache_times = []

        # Loop over the probes and measure inference time for both experiments.
        for probe in probes[:1]:
            # Baseline experiment: without kv cache.
            t_baseline, token_baseline = run_inference(stub, probe, use_kv_cache=False)
            baseline_times.append(t_baseline)

            # KV Cache experiment: send the precomputed system prompt kv cache.
            t_kv, token_kv = run_inference(stub, probe, use_kv_cache=True, kv_cache_bytes=kv_cache_bytes, prompt_len=prompt_len)
            kv_cache_times.append(t_kv)

        avg_baseline = sum(baseline_times) / len(baseline_times)
        avg_kv_cache = sum(kv_cache_times) / len(kv_cache_times)
        speedup = avg_baseline / avg_kv_cache if avg_kv_cache > 0 else float('inf')

        print("\n=== Experiment Results ===")
        print(f"Baseline average time to first token: {avg_baseline:.6f} seconds")
        print(f"KV Cache average time to first token: {avg_kv_cache:.6f} seconds")
        print(f"Speedup factor: {speedup:.2f}x")


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

    def run_inference(stub, probe, use_kv_cache=False, kv_cache_bytes=None, prompt_len=-1):
        """
        Make an inference RPC call. If use_kv_cache is True and kv_cache_bytes is provided,
        include it in the request.
        """
        request = kv_cache_pb2.InferenceRequest(input=SYSTEM_PROMPT + probe) 

        if use_kv_cache and kv_cache_bytes is not None:
            request.kv_cache = kv_cache_bytes
            request.prompt_len = prompt_len

        start = time.time()
        response = stub.Inference(request)
        elapsed = time.time() - start
        logger.info(f"Inference for probe [{probe[:30]}...] took {elapsed:.6f} seconds and returned token {response.first_token}")
        return elapsed, response.first_token

    def load_probes(dataset_path):
        """
        Load probe examples from a JSON dataset. The JSON should contain a 'probe' column.
        """
        df = pd.read_json(dataset_path)
        if "probe" not in df.columns:
            raise ValueError("Dataset does not have a 'probe' column.")
        return df["probe"].tolist()

    def read(self, key, seq=0, suppress=False):
        msg = build_message(NETCACHE_READ_QUERY, key, seq)
        if msg is None:
            return

        start_time = time.time()

        self.udps.connect(('10.0.0.1', self.port))
        self.udps.send(msg)

        data = self.udps.recv(1024)
        op = data[0]

        latency = time.time() - start_time
        self.latencies.append(latency)
        if op == NETCACHE_KEY_NOT_FOUND:
            print('Error: Key not found (key = ' + key + ')')
        else:
            val = data[21:].decode("utf-8")
            print(val)

    def request_latency_metric(self):
        total_latency = 0
        for i in self.latencies:
            total_latency += i
        average_latency = total_latency / len(self.latencies)
        print(f"Average Latency of sending message: {average_latency}")

    def flush(self, seq = 0):
        msg = build_message(NETCACHE_FLUSH_QUERY, seq)
        if msg is None:
            return

        self.udps.connect((self.get_node(key), self.port))
        self.udps.send(msg)

        start_time = time.time()

        data = self.udps.recv(1024)
        op = data[0]

        latency = time.time() - start_time
        self.latencies.append(latency)

        print(f"Received Flush Complete {op}")
