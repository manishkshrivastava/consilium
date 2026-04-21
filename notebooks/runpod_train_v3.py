"""
TelcoGPT v3 Training — RunPod A100
Run as a single script: python runpod_train_v3.py
Or split into cells for Jupyter.
"""

# ============================================================
# Step 1: Install + Load Model
# ============================================================
import subprocess
subprocess.run(["pip", "install", "unsloth[cu124-torch260]", "--quiet"], check=True)

import torch
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
    max_seq_length=1024,
    load_in_4bit=True,
)
print(f"Model loaded. GPU: {torch.cuda.get_device_name()}")

# ============================================================
# Step 2: LoRA Config
# ============================================================
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=32,
    lora_dropout=0.0,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)
print(f"Trainable: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

# ============================================================
# Step 3: Load Data + Train
# ============================================================
import json
from datasets import Dataset
from unsloth import UnslothTrainer, UnslothTrainingArguments

TRAIN_FILE = "train_v3.jsonl"  # Upload this file to RunPod
OUTPUT_DIR = "./telco-7b-output-v3"

def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]

train_data = load_jsonl(TRAIN_FILE)
print(f"Train: {len(train_data)}")

def format_to_text(example):
    text = tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False
    )
    return {"text": text}

train_dataset = Dataset.from_list(train_data).map(format_to_text)

training_args = UnslothTrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=4,   # A100 has 80GB — can handle batch=4
    gradient_accumulation_steps=4,    # effective batch = 4*4 = 16 (same as before)
    learning_rate=2e-4,
    warmup_steps=50,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=10,
    save_steps=500,
    save_total_limit=3,
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

print(f"Starting v3 training...")
trainer.train()
print("TRAINING COMPLETE!")

# ============================================================
# Step 4: Save Adapter
# ============================================================
import os, zipfile

ADAPTER_PATH = "./telco-7b-adapter-v3"
model.save_pretrained(ADAPTER_PATH)
tokenizer.save_pretrained(ADAPTER_PATH)

ZIP_PATH = "./telco-7b-adapter-v3.zip"
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ADAPTER_PATH):
        for file in files:
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, ADAPTER_PATH)
            zf.write(filepath, arcname)
print(f"Zipped: {ZIP_PATH} ({os.path.getsize(ZIP_PATH) / 1e6:.1f} MB)")
print("Download telco-7b-adapter-v3.zip and you're done!")
