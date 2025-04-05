from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "gpt2"
cache_dir = "./gpt2_local"

# Downloads to ./gpt2_local (instead of default hidden cache)
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
model = AutoModelForCausalLM.from_pretrained(model_name, cache_dir=cache_dir)
