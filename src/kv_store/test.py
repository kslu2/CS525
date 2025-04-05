from client_api import NetCacheClient
import time

def main(n_servers, no_cache):
    client = NetCacheClient(n_servers=n_servers, no_cache=no_cache)

    # those queries should be replied by the server
    """
    for i in range(12):
        for j in range(2):
            for k in range(12):
                for p in range(9):
                    custom_key = f"{i:02}{j}{k:02}{p}"
                    client.read(custom_key)
                    time.sleep(0.005)
    """
    client.send_system_prompt()



if __name__=="__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--n-servers', help='number of servers', type=int, required=False, default=1)
    parser.add_argument('--disable-cache', help='do not use netcache', action='store_true')
    args = parser.parse_args()

    main(args.n_servers, args.disable_cache)