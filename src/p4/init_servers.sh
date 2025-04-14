#!/bin/sh

NCACHE_DIR=../../

PYTHON="python3"

usage="${0} <n_servers> [<server-init-flags>]"

n_servers=$1
server_flags=$2

if [ -z $n_servers ]; then
	echo "Error: invalid input: ${usage}"
	exit 1
fi


for i in $(seq $n_servers); do
	server_data="$NCACHE_DIR/src/p4/kv_cache.pt"
	model_data="$NCACHE_DIR/src/kv_store/gpt2_local/models--gpt2/snapshots/607a30d783dfa663caf39e06633721c8d4cfcd7e"
	mx server$i $PYTHON $NCACHE_DIR/src/kv_store/server.py $server_flags --cache $server_data --model $model_data
done
