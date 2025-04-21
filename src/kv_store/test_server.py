from client_api import NetCacheClient
import time

def main(n_servers, no_cache):
    client = NetCacheClient(n_servers=n_servers, no_cache=no_cache)
    key = "12345678"
    
    target_size = (12 * 12 * 9 * 64 * 2 * 4)
    value_size = 256
    if target_size % value_size != 0:
        print("target_len must be divisible by value_len")
        return

    num_msg = target_size // value_size

    print(f"Starting Time: {time.time()}")
    for _ in range(num_msg):
        client.read(key)



if __name__=="__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--n-servers', help='number of servers', type=int, required=False, default=1)
    parser.add_argument('--disable-cache', help='do not use netcache', action='store_true')
    args = parser.parse_args()

    main(args.n_servers, args.disable_cache)