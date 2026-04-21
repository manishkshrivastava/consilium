"""
Phase 2: Fine-tune Llama 3.1 8B on telco data using LoRA
- Optimized for Apple Silicon (M4 Pro, 24GB unified memory)
- Uses float16 precision (MPS does not support bitsandbytes 4-bit)
- LoRA keeps trainable parameters small (~2%)

Prerequisites:
  pip install torch transformers peft trl accelerate datasets sentencepiece
"""

from pathlib import Path
import json
import torch
import os

# =============================================================================
# Configuration
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_FILE = PROJECT_ROOT / "data" / "processed" / "train.jsonl"
VAL_FILE = PROJECT_ROOT / "data" / "processed" / "val.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "models" / "telco-slm-v1"

# Model config
BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # Ungated, Apache 2.0, NVIDIA uses Qwen for telco reasoning
MAX_SEQ_LENGTH = 2048  # Reduced from 4096 to fit in 24GB with float16

# LoRA config
LORA_R = 16            # Reduced from 32 for memory efficiency on MPS
LORA_ALPHA = 32        # 2x rank
LORA_DROPOUT = 0.05
TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# Training config — tuned for M4 Pro 24GB
BATCH_SIZE = 1             # Keep at 1 for MPS memory safety
GRADIENT_ACCUMULATION = 16  # Effective batch size = 1 * 16 = 16
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
WARMUP_RATIO = 0.05
MAX_STEPS = -1             # Set to positive number for quick test (e.g., 50)
SAVE_STEPS = 200
LOGGING_STEPS = 10


# =============================================================================
# Data Loading
# =============================================================================

def load_training_data(filepath: Path) -> list:
    """Load JSONL training data."""
    data = []
    with open(filepath) as f:
        for line in f:
            data.append(json.loads(line))
    return data


def format_chat_to_text(example: dict, tokenizer) -> str:
    """Convert chat messages to the model's expected text format."""
    messages = example["messages"]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    return text


# =============================================================================
# Main Training
# =============================================================================

def main():
    print("=" * 60)
    print("TELCO SLM - Phase 2: LoRA Fine-Tuning (Apple Silicon)")
    print("=" * 60)

    # Detect device
    if torch.backends.mps.is_available():
        device = "mps"
        print(f"\nDevice: Apple Silicon (MPS)")
        print(f"Memory: 24 GB unified (shared with system)")
    elif torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_mem / (1024**3)
        print(f"\nDevice: {gpu_name} ({gpu_mem:.1f} GB)")
    else:
        device = "cpu"
        print("\nWARNING: No GPU detected. Training will be extremely slow.")

    # =========================================================================
    # Step 1: Load model
    # =========================================================================
    print("\n[1/4] Loading base model...")
    print(f"  Model: {BASE_MODEL}")
    print(f"  This will download ~16GB on first run...")

    from transformers import AutoModelForCausalLM, AutoTokenizer

    # For Apple Silicon: load in float16, no quantization
    # MPS doesn't support bitsandbytes 4-bit quantization
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="auto" if device == "cuda" else None,
        use_cache=False,  # Required for gradient checkpointing
    )

    # Move to MPS if on Apple Silicon
    if device == "mps":
        model = model.to(device)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    print(f"  Model loaded successfully on {device}")
    param_gb = sum(p.numel() * p.element_size() for p in model.parameters()) / (1024**3)
    print(f"  Model memory: ~{param_gb:.1f} GB")

    # =========================================================================
    # Step 2: Add LoRA adapters
    # =========================================================================
    print("\n[2/4] Adding LoRA adapters...")

    from peft import LoraConfig, get_peft_model

    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    # Enable gradient checkpointing to save memory
    model.gradient_checkpointing_enable()

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  Trainable parameters: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # =========================================================================
    # Step 3: Prepare dataset
    # =========================================================================
    print("\n[3/4] Loading and formatting training data...")

    if not TRAIN_FILE.exists():
        print(f"  ERROR: Training data not found at {TRAIN_FILE}")
        print("  Run scripts/data_prep/03_prepare_training_data.py first!")
        return

    train_data = load_training_data(TRAIN_FILE)
    val_data = load_training_data(VAL_FILE) if VAL_FILE.exists() else []

    print(f"  Training examples: {len(train_data)}")
    print(f"  Validation examples: {len(val_data)}")

    from datasets import Dataset

    def process_example(example):
        text = format_chat_to_text(example, tokenizer)
        return {"text": text}

    train_dataset = Dataset.from_list(train_data).map(process_example)
    val_dataset = Dataset.from_list(val_data).map(process_example) if val_data else None

    print(f"  Dataset formatted")

    # =========================================================================
    # Step 4: Train
    # =========================================================================
    print("\n[4/4] Starting training...")

    from trl import SFTTrainer
    from transformers import TrainingArguments

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Apple Silicon specific settings
    use_fp16 = (device == "mps" or (device == "cuda" and not torch.cuda.is_bf16_supported()))
    use_bf16 = (device == "cuda" and torch.cuda.is_bf16_supported())

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        learning_rate=LEARNING_RATE,
        warmup_ratio=WARMUP_RATIO,
        max_steps=MAX_STEPS,
        fp16=use_fp16,
        bf16=use_bf16,
        logging_steps=LOGGING_STEPS,
        save_steps=SAVE_STEPS,
        save_total_limit=3,
        eval_strategy="steps" if val_dataset else "no",
        eval_steps=SAVE_STEPS if val_dataset else None,
        optim="adamw_torch",  # adamw_8bit not supported on MPS
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",
        gradient_checkpointing=True,
        dataloader_pin_memory=False,  # Required for MPS
        max_grad_norm=1.0,
    )

    from transformers import DataCollatorForLanguageModeling

    # Tokenize the dataset
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
            padding=False,
        )

    train_tokenized = train_dataset.map(tokenize_function, batched=True, remove_columns=train_dataset.column_names)
    val_tokenized = val_dataset.map(tokenize_function, batched=True, remove_columns=val_dataset.column_names) if val_dataset else None

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    from transformers import Trainer

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=val_tokenized,
        data_collator=data_collator,
        processing_class=tokenizer,
    )

    total_steps = len(train_dataset) * NUM_EPOCHS // (BATCH_SIZE * GRADIENT_ACCUMULATION)
    print(f"\n  Output directory: {OUTPUT_DIR}")
    print(f"  Device: {device}")
    print(f"  Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION}")
    print(f"  Estimated total steps: ~{total_steps}")
    print(f"  Training for {NUM_EPOCHS} epochs...")
    print(f"  {'='*40}")

    # Train!
    trainer.train()

    # =========================================================================
    # Save
    # =========================================================================
    print("\nSaving model...")

    # Save LoRA adapter
    adapter_dir = OUTPUT_DIR / "adapter"
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"  LoRA adapter saved to: {adapter_dir}")

    # Merge LoRA into base model
    print("\nMerging LoRA adapter into base model...")
    try:
        from peft import PeftModel
        merged_model = model.merge_and_unload()
        merged_dir = OUTPUT_DIR / "merged"
        merged_dir.mkdir(parents=True, exist_ok=True)
        merged_model.save_pretrained(str(merged_dir))
        tokenizer.save_pretrained(str(merged_dir))
        print(f"  Merged model saved to: {merged_dir}")
    except Exception as e:
        print(f"  Could not merge: {e}")
        print(f"  LoRA adapter is still usable at: {adapter_dir}")

    # Convert to GGUF for Ollama
    print("\nTo convert to GGUF for Ollama, run:")
    print(f"  pip install llama-cpp-python")
    print(f"  python -m llama_cpp.convert {OUTPUT_DIR}/merged --outfile telco-slm.gguf")
    print(f"  Or use: huggingface-cli convert-to-gguf {OUTPUT_DIR}/merged")

    print("\n" + "=" * 60)
    print("Phase 2 Complete!")
    print("Next steps:")
    print("  1. Evaluate: python scripts/evaluation/evaluate_gsma.py")
    print("  2. Convert to GGUF and test with Ollama")
    print("  3. Build RAG: python scripts/rag/build_rag.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
