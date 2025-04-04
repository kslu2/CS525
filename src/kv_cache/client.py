import time
import grpc
import io
import logging
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

import kv_cache_pb2
import kv_cache_pb2_grpc

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global constants
MODEL_NAME = "gpt2"
SYSTEM_PROMPT = "You are a helpful and informative AI assistant."

# Initialize model and tokenizer on the client side to precompute the kv cache.
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Loading model {MODEL_NAME} on device {device} for client")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
model.to(device)
model.eval()

def serialize_kv_cache(kv_cache):
	"""
	Serialize the key-value cache using torch.save.
	"""
	buffer = io.BytesIO()
	torch.save(kv_cache, buffer)
	return buffer.getvalue()

def precompute_system_prompt_kv_cache():
	"""
	Precompute and serialize the kv cache for the fixed system prompt.
	"""
	system_prompt_enc = tokenizer(SYSTEM_PROMPT, return_tensors="pt", add_special_tokens=True)

	input_ids = system_prompt_enc.input_ids
	attention_mask = system_prompt_enc.attention_mask
	
	with torch.no_grad():
		sp_outputs = model(input_ids=input_ids,
											 attention_mask=attention_mask,
											 use_cache=True)
		
		system_prompt_cache = sp_outputs.past_key_values

	return system_prompt_cache, input_ids.shape[1]

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

def main():
	# Create a gRPC channel to connect to the server.
	channel = grpc.insecure_channel("localhost:50051")
	stub = kv_cache_pb2_grpc.KVCacheServiceStub(channel)

	# Precompute the system prompt's kv cache.
	kv_cache, prompt_len = precompute_system_prompt_kv_cache()

	# 0 = key, 1 = value, ... 0 = 12 layers 6 bytes needed for key
	print(kv_cache[0][0][0][0][0])
	kv_cache_bytes = serialize_kv_cache(kv_cache)
	logger.info("Precomputed system prompt kv cache.")

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

if __name__ == "__main__":
	main()
