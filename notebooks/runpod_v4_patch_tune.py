"""
Consilium v4 Patch-Tune — RunPod A40
Surgical patch on v2 adapter. DO NOT call get_peft_model again.

BEFORE RUNNING:
1. Upload v4_patch_train.jsonl to RunPod
2. Upload llama-telco-v2-adapter.zip to RunPod and unzip it
3. Upload gold_eval_v3.jsonl for benchmark (optional, can do after)

Split into cells for Jupyter. Each section = one cell.
"""

# ============================================================
# Cell 1: Install dependencies
# ============================================================
import subprocess
subprocess.run(["pip", "install", "unsloth[cu124-torch260]", "torchao<0.10", "--quiet"], check=True)
subprocess.run(["pip", "install", "--upgrade", "typing_extensions", "--force-reinstall", "--quiet"], check=True)
print("Dependencies installed. >>> RESTART KERNEL NOW <<<")

# ============================================================
# Cell 2: Load v2 adapter (run AFTER kernel restart)
# ============================================================
import torch
from unsloth import FastLanguageModel

# Base model: unsloth/meta-llama-3.1-8b-instruct-bnb-4bit (from adapter_config.json)
# Unsloth auto-resolves the base model from the adapter config
# DO NOT call get_peft_model — adapter is already a LoRA model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="./telco-v2-adapter",  # <-- unzipped v2 adapter directory
    max_seq_length=1024,
    load_in_4bit=True,
)

# Verify: must show Llama base + LoRA trainable params
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
print(f"GPU: {torch.cuda.get_device_name()}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
print(f"Total params: {total:,}")
print(f"Trainable params: {trainable:,}")
print(f"Trainable %: {trainable/total*100:.2f}%")
print(f"Model type: {model.config.model_type}")  # Should print "llama"

if trainable == 0:
    print("WARNING: No trainable params! Adapter may not have loaded correctly.")
    print("Check that telco-v2-adapter/ contains adapter_config.json and adapter_model.safetensors")
if model.config.model_type != "llama":
    print(f"WARNING: Expected 'llama' but got '{model.config.model_type}'!")

# ============================================================
# Cell 3: Load data
# ============================================================
import json
from datasets import Dataset

TRAIN_FILE = "v4_patch_train.jsonl"

def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]

train_data = load_jsonl(TRAIN_FILE)
print(f"Training rows: {len(train_data)}")

# Quick sanity check
sample = train_data[0]
print(f"Keys: {list(sample.keys())}")
print(f"Messages: {len(sample['messages'])} (system/user/assistant)")
print(f"Sample user: {sample['messages'][1]['content'][:100]}...")

def format_to_text(example):
    text = tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False
    )
    return {"text": text}

train_dataset = Dataset.from_list(train_data).map(format_to_text)
print(f"Dataset ready: {len(train_dataset)} examples")

# ============================================================
# Cell 4: Train (v4 patch-tune)
# ============================================================
from unsloth import UnslothTrainer, UnslothTrainingArguments

OUTPUT_DIR = "./telco-7b-output-v4"

training_args = UnslothTrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=4,       # A40 48GB can handle batch=4
    gradient_accumulation_steps=4,        # effective batch = 16
    learning_rate=5e-5,                   # SURGICAL: 5e-5, not 2e-4
    warmup_steps=30,                      # shorter warmup for small dataset
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=10,
    save_steps=500,
    save_total_limit=2,
    eval_strategy="no",
    optim="adamw_8bit",
    weight_decay=0.01,
    lr_scheduler_type="cosine",
    seed=42,
    report_to="none",
)

trainer = UnslothTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    args=training_args,
    dataset_text_field="text",
    max_seq_length=1024,
    packing=True,
)

print(f"Config: LR={training_args.learning_rate}, epochs={training_args.num_train_epochs}")
print(f"Effective batch: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
print(f"Starting v4 patch-tune...")
trainer.train()
print("TRAINING COMPLETE!")

# ============================================================
# Cell 5: Save v4 adapter
# ============================================================
import os, zipfile

ADAPTER_PATH = "./telco-v4-adapter"
model.save_pretrained(ADAPTER_PATH)
tokenizer.save_pretrained(ADAPTER_PATH)

ZIP_PATH = "./telco-v4-adapter.zip"
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ADAPTER_PATH):
        for file in files:
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, ADAPTER_PATH)
            zf.write(filepath, arcname)
print(f"v4 adapter saved: {ZIP_PATH} ({os.path.getsize(ZIP_PATH) / 1e6:.1f} MB)")

# ============================================================
# Cell 6: Merge adapter with base model (for GGUF)
# ============================================================
# Clean up training artifacts first to free disk space
import shutil
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
    print(f"Cleaned up {OUTPUT_DIR}")

print("Merging adapter with base model...")
merged_path = "./telco-v4-merged"

model.save_pretrained_merged(
    merged_path,
    tokenizer,
    save_method="merged_16bit",
)
print(f"Merged model saved to {merged_path}")

# ============================================================
# Cell 7: Convert to GGUF (pinned llama.cpp)
# ============================================================
import subprocess

# Clone pinned llama.cpp
if not os.path.exists("llama.cpp"):
    subprocess.run([
        "git", "clone", "--branch", "b5200",
        "https://github.com/ggerganov/llama.cpp.git"
    ], check=True)

# Install gguf from llama.cpp's own package
subprocess.run([
    "pip", "install", "./llama.cpp/gguf-py", "--quiet"
], check=True)

# Convert to GGUF F16
subprocess.run([
    "python", "llama.cpp/convert_hf_to_gguf.py",
    merged_path,
    "--outfile", "telco-v4-f16.gguf",
    "--outtype", "f16",
], check=True)
print("F16 GGUF created")

# Quantize to Q4_K_M
# First build llama-quantize
subprocess.run(["cmake", "-B", "llama.cpp/build", "llama.cpp"], check=True)
subprocess.run(["cmake", "--build", "llama.cpp/build", "--config", "Release", "-j"], check=True)

subprocess.run([
    "llama.cpp/build/bin/llama-quantize",
    "telco-v4-f16.gguf",
    "telco-v4-Q4_K_M.gguf",
    "Q4_K_M",
], check=True)

gguf_size = os.path.getsize("telco-v4-Q4_K_M.gguf") / 1e9
print(f"GGUF Q4_K_M created: telco-v4-Q4_K_M.gguf ({gguf_size:.1f} GB)")
print("Download this file to your Mac!")

# ============================================================
# Cell 8 (OPTIONAL): Quick smoke test before downloading
# ============================================================
FastLanguageModel.for_inference(model)

test_messages = [
    {"role": "system", "content": "You are Consilium, a telecom network intelligence assistant. Analyze network data, diagnose issues, and provide actionable recommendations."},
    {"role": "user", "content": "ERAB setup success rate dropped from 99.1% to 92.3% on site METRO_100 over 2 hours. What's the most likely cause?"},
]

inputs = tokenizer.apply_chat_template(test_messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to("cuda")
outputs = model.generate(input_ids=inputs, max_new_tokens=300, temperature=0.3)
response = tokenizer.decode(outputs[0][inputs.shape[-1]:], skip_special_tokens=True)
print("=== Smoke Test ===")
print(response)
