"""
Merge LoRA adapter with base model and save as full HF model.
Then convert to GGUF for Ollama.
"""
import sys
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ADAPTER_PATH = PROJECT_ROOT / "telco-7b-adapter-2000"
OUTPUT_PATH = PROJECT_ROOT / "models" / "telco-7b-merged"

print(f"Adapter: {ADAPTER_PATH}")
print(f"Output:  {OUTPUT_PATH}")

# Load base model in float16 (not quantized - we need full precision for merging)
print("\n1. Loading base model (Qwen2.5-7B-Instruct) in float16...")
base_model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    torch_dtype=torch.float16,
    device_map="cpu",  # CPU for Mac - we have 24GB RAM
    trust_remote_code=True,
)
print(f"   Base model loaded. Parameters: {base_model.num_parameters():,}")

# Load tokenizer
print("2. Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct", trust_remote_code=True)

# Load and merge adapter
print("3. Loading LoRA adapter...")
model = PeftModel.from_pretrained(base_model, str(ADAPTER_PATH))
print(f"   Adapter loaded. Trainable params: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

print("4. Merging adapter into base model...")
model = model.merge_and_unload()
print(f"   Merged model parameters: {model.num_parameters():,}")

# Save merged model
print(f"5. Saving merged model to {OUTPUT_PATH}...")
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
model.save_pretrained(OUTPUT_PATH)
tokenizer.save_pretrained(OUTPUT_PATH)

print(f"\nDone! Merged model saved to: {OUTPUT_PATH}")
print(f"\nNext steps:")
print(f"  1. Convert to GGUF:  mlx_lm.convert --hf-path {OUTPUT_PATH} -q --mlx-path {PROJECT_ROOT}/models/telco-7b-mlx")
print(f"  2. Or use llama.cpp to convert to GGUF for Ollama")
