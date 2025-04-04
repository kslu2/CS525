import time
import grpc
from concurrent import futures
import logging
import io

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

import kv_cache_pb2
import kv_cache_pb2_grpc

# Configure logging for detailed output.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global constants
MODEL_NAME = "gpt2"
SYSTEM_PROMPT = "You are a helpful and informative AI assistant."

# Load model and tokenizer once during server startup.
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Loading model {MODEL_NAME} on device {device}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
model.to(device)
model.eval()

def set_seed(seed=42):
	torch.manual_seed(seed)
	if torch.cuda.is_available():
		torch.cuda.manual_seed_all(seed)

def deserialize_kv_cache(kv_cache_bytes):
	"""
	Deserialize the key-value cache from bytes.
	"""
	buffer = io.BytesIO(kv_cache_bytes)
	return torch.load(buffer, map_location=device)

def baseline_inference(probe):
	"""
	Baseline inference: concatenate the fixed system prompt with the probe,
	then run inference without any precomputed cache.
	"""
	set_seed(42)

	input_text = SYSTEM_PROMPT + probe
	encoded_full = tokenizer(input_text, return_tensors="pt", add_special_tokens=True)

	input_ids = encoded_full.input_ids.to(device)
	attention_mask = encoded_full.attention_mask.to(device)

	if device.type == "cuda":
		torch.cuda.synchronize()
		
	start = time.time()
	
	with torch.no_grad():
		output_ids = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=20,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False
    )
	
	if device.type == "cuda":
		torch.cuda.synchronize()
	
	elapsed = time.time() - start
	first_token = tokenizer.decode(output_ids[0, -1], skip_special_tokens=True)

	logger.info(f"Baseline inference time: {elapsed:.6f} seconds, with first token: {first_token}")
	
	return first_token

def kv_cache_inference(input, kv_cache_bytes, prompt_len):
	"""
	KV Cache inference: use the provided serialized kv cache for the system prompt,
	then process only the probe.
	"""
	set_seed(42)
	# Deserialize the kv cache.
	cached_kv = deserialize_kv_cache(kv_cache_bytes)
	full_enc = tokenizer(input, return_tensors="pt", add_special_tokens=True)

	input_ids = full_enc.input_ids.to(device)
	attention_mask = full_enc.attention_mask.to(device) 

	if device.type == "cuda":
		torch.cuda.synchronize()

	start = time.time()

	probe_seq_len = input_ids.shape[1] - prompt_len
	batch_size = input_ids.shape[0]
	
	probe_position_ids = torch.arange(
    prompt_len, prompt_len + probe_seq_len,
    dtype=torch.long, device=device
	).unsqueeze(0).expand(batch_size, probe_seq_len)

	with torch.no_grad():
		output_ids = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        past_key_values=cached_kv,
        max_new_tokens=1,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False,
        position_ids=probe_position_ids
    )
	
	if device.type == "cuda":
		torch.cuda.synchronize()

	elapsed = time.time() - start
	first_token = tokenizer.decode(output_ids[0, -1], skip_special_tokens=True)

	logger.info(f"KV Cache inference time: {elapsed:.6f} seconds, with first token: {first_token}")
	return first_token

# Implement the gRPC service.
class KVCacheServiceServicer(kv_cache_pb2_grpc.KVCacheServiceServicer):
	def Inference(self, request, context):
		"""
		Handle the Inference RPC. If kv_cache is provided, run kv_cache_inference,
		otherwise run baseline_inference.
		"""
		input = request.input		
		
		if request.kv_cache:
			logger.info("Received inference request with kv_cache")
			first_token = kv_cache_inference(input, request.kv_cache, request.prompt_len)
		else:
			logger.info("Received baseline inference request without kv_cache")
			first_token = baseline_inference(input)
		
		return kv_cache_pb2.InferenceResponse(first_token=first_token)

def serve():
	# Create a gRPC server with a thread pool.
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	kv_cache_pb2_grpc.add_KVCacheServiceServicer_to_server(KVCacheServiceServicer(), server)
	
	server.add_insecure_port('[::]:50051')
	logger.info("Starting gRPC server on port 50051...")
	server.start()
	
	try:
		# Keep the server running.
		while True:
			time.sleep(5)
	except KeyboardInterrupt:
		logger.info("Shutting down server...")
		server.stop(0)

if __name__ == "__main__":
	serve()
