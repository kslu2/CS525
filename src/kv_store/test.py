from client_api import NetCacheClient
import time

def main(n_servers, no_cache):
    client = NetCacheClient(n_servers=n_servers, no_cache=no_cache)

    # read should be forwared to KV-Store and return error (not inserted)
    key = "12345678"
    
    target_size = (12 * 12 * 9 * 64 * 2 * 4)
    value_size = 256

    if target_size % value_size != 0:
        print("target_len must be divisible by value_len")
        return

    num_msg = target_size // value_size

    for _ in range(num_msg):
        client.read(key)

    successful_reads = client.successful_reads

    if successful_reads != num_msg:
        print(f"Failed to read all messages: expected {num_msg} but got {successful_reads}")
    
    latencies = client.latencies

    total_latency = sum(latencies) if latencies else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    std_dev_latency = (sum((x - avg_latency) ** 2 for x in latencies) / len(latencies)) ** 0.5 if latencies else 0

    print(f"Total latency: {total_latency:.6f} seconds")
    print(f"Avg latency: {avg_latency:.6f} seconds")
    print(f"Std Dev latency: {std_dev_latency:.6f} seconds")



if __name__=="__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--n-servers', help='number of servers', type=int, required=False, default=1)
    parser.add_argument('--disable-cache', help='do not use netcache', action='store_true')
    args = parser.parse_args()

    main(args.n_servers, args.disable_cache)