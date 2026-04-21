# ============================================================
# CELL 1: Install + Load Model
# ============================================================
# !pip install "unsloth[kaggle-new] @ git+https://github.com/unslothai/unsloth.git" --quiet

import torch
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
    max_seq_length=1024,  # v2: increased from 512
    load_in_4bit=True,
)
print(f"Model loaded. GPU: {torch.cuda.get_device_name()}")

# ============================================================
# CELL 2: LoRA Config
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
# CELL 3: Load Data + Train
# ============================================================
import json
from datasets import Dataset
from unsloth import UnslothTrainer, UnslothTrainingArguments

# v2: combined dataset (cleaned original + protocol + KPI)
TRAIN_FILE = "/kaggle/input/telco-training-data-v2/train_v2.jsonl"
OUTPUT_DIR = "/kaggle/working/telco-7b-output-v2"

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

# v2 changes:
# - max_seq_length: 512 → 1024 (longer, more detailed answers)
# - ~34,400 examples (34,189 cleaned + 116 KPI + ~100 protocol)
# - With packing + seq_len 1024, fewer steps per epoch
# - Estimated ~1200-1400 steps for 1 epoch (vs 2137 with seq_len 512)
training_args = UnslothTrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    warmup_steps=50,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=10,
    save_steps=500,        # v2: more frequent saves
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
    max_seq_length=1024,   # v2: increased from 512
    packing=True,
)

print(f"Starting v2 training...")
trainer.train()
print("TRAINING COMPLETE!")

# ============================================================
# CELL 4: Save Adapter
# ============================================================
import os
import shutil
import zipfile

# Find the latest checkpoint
ckpts = sorted(
    [d for d in os.listdir(OUTPUT_DIR) if d.startswith("checkpoint-")],
    key=lambda x: int(x.split("-")[1])
)
latest_ckpt = os.path.join(OUTPUT_DIR, ckpts[-1]) if ckpts else None
print(f"Latest checkpoint: {latest_ckpt}")

# Also save the final model directly
ADAPTER_PATH = "/kaggle/working/telco-7b-adapter-v2"
model.save_pretrained(ADAPTER_PATH)
tokenizer.save_pretrained(ADAPTER_PATH)
print(f"Adapter saved to {ADAPTER_PATH}")

# Zip it for easy download
ZIP_PATH = "/kaggle/working/telco-7b-adapter-v2.zip"
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ADAPTER_PATH):
        for file in files:
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, ADAPTER_PATH)
            zf.write(filepath, arcname)
print(f"Zipped: {ZIP_PATH} ({os.path.getsize(ZIP_PATH) / 1e6:.1f} MB)")
