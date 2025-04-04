import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def set_seed(seed=42):
	torch.manual_seed(seed)
	if torch.cuda.is_available():
		torch.cuda.manual_seed_all(seed)

def extract_kv_cache(system_prompt, model, tokenizer):
	"""
	Tokenize the system prompt and precompute its KV cache.
	Returns a tuple of (past_key_values, encoded_system_prompt).
	"""
	encoded_sys = tokenizer(system_prompt, return_tensors="pt", add_special_tokens=True)
	input_ids = encoded_sys.input_ids.to(next(model.parameters()).device)
	attention_mask = encoded_sys.attention_mask.to(next(model.parameters()).device)
	
	with torch.no_grad():
		out = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=True)
	
	return out.past_key_values, encoded_sys

def process_kv_cache(past_key_values):
	"""
	Processes the past_key_values to create a dictionary with (layer, position) as keys
	and concatenated head embeddings (num_head * dimension) as values.
	"""
	kv_cache = {}
	for layer_idx, layer_data in enumerate(past_key_values):
		key, value = layer_data  # key and value tensors
		
		# key shape: [batch_size, num_heads, seq_len, embed_size_per_head]
		# value shape: [batch_size, num_heads, seq_len, embed_size_per_head]

		num_positions = key.shape[2]

		for position_idx in range(num_positions):
			# Extract the key and value vectors for the current layer and position.
			key_vector = key[:, :, position_idx, :]  # Shape: [batch_size, num_heads, embed_size_per_head]
			value_vector = value[:, :, position_idx, :]  # Shape: [batch_size, num_heads, embed_size_per_head]

			# Concatenate along the num_heads dimension to get the combined vector.
			combined_vector = torch.cat([key_vector, value_vector], dim=1)  # Shape: [batch_size, num_heads * embed_size_per_head]

			kv_cache[(layer_idx, position_idx)] = combined_vector.squeeze()  # Remove batch dimension

	return kv_cache

def process_prompts(model, tokenizer):
	# Load dataset and read the first system prompt and probe
	df = pd.read_json("hf://datasets/Naomibas/llm-system-prompts-benchmark/hundred_system_prompts.json")
	row = df.iloc[0]
	system_prompt = row["prompt"]
	probe = row["probe"]
	
	print("System Prompt:")
	print(system_prompt)
	print("\nProbe:")
	print(probe)
	
	# Extract KV cache for the system prompt
	past_key_values, encoded_sys = extract_kv_cache(system_prompt, model, tokenizer)
	system_length = encoded_sys.input_ids.shape[1]
	print("\nExtracted KV cache from system prompt (length {} tokens).".format(system_length))
	
	# Process the KV cache
	kv_cache = process_kv_cache(past_key_values)
	print("\nProcessed KV cache.  Number of (layer, position) keys:", len(kv_cache))
	# Further processing with `past_key_values` can be added here.

def main():
	set_seed(42)
	
	# Initialize the model and tokenizer
	model_name = "gpt2"
	tokenizer = AutoTokenizer.from_pretrained(model_name)
	model = AutoModelForCausalLM.from_pretrained(model_name)
	model.eval()
	
	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
	model.to(device)
	
	# Process prompts and extract KV cache
	process_prompts(model, tokenizer)

if __name__ == "__main__":
	main()