# ============================================================
# TelcoGPT 7B — Google Colab Training Notebook
# ============================================================
# Copy each section into a separate Colab cell and run in order.
# Runtime: T4 GPU (free), ~4-8 hours training
# ============================================================

# ============================================================
# CELL 1: Install dependencies
# ============================================================
# !pip install unsloth
# !pip install --no-deps trl peft accelerate bitsandbytes

# ============================================================
# CELL 2: Upload training data
# ============================================================
# from google.colab import files
# uploaded = files.upload()  # Upload train.jsonl and valid.jsonl

# ============================================================
# CELL 3: Verify GPU
# ============================================================
# import torch
# print(f"GPU: {torch.cuda.get_device_name(0)}")
# print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")

# ============================================================
# CELL 4: Load model with Unsloth (4-bit quantized)
# ============================================================
# from unsloth import FastLanguageModel
#
# model, tokenizer = FastLanguageModel.from_pretrained(
#     model_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
#     max_seq_length=2048,
#     load_in_4bit=True,
#     dtype=None,
# )
#
# print(f"Model loaded: Qwen 2.5 7B (4-bit)")

# ============================================================
# CELL 5: Add LoRA adapters
# ============================================================
# model = FastLanguageModel.get_peft_model(
#     model,
#     r=32,
#     lora_alpha=64,
#     lora_dropout=0.05,
#     target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
#                      "gate_proj", "up_proj", "down_proj"],
#     bias="none",
#     use_gradient_checkpointing="unsloth",
#     random_state=42,
# )
#
# trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
# total = sum(p.numel() for p in model.parameters())
# print(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

# ============================================================
# CELL 6: Load and format training data
# ============================================================
# import json
# from datasets import Dataset
#
# def load_jsonl(path):
#     data = []
#     with open(path) as f:
#         for line in f:
#             data.append(json.loads(line))
#     return data
#
# train_data = load_jsonl("train.jsonl")
# val_data = load_jsonl("valid.jsonl")
# print(f"Train: {len(train_data)}, Val: {len(val_data)}")
#
# def format_to_text(example):
#     text = tokenizer.apply_chat_template(
#         example["messages"], tokenize=False, add_generation_prompt=False
#     )
#     return {"text": text}
#
# train_dataset = Dataset.from_list(train_data).map(format_to_text)
# val_dataset = Dataset.from_list(val_data).map(format_to_text)
# print(f"Formatted. Sample length: {len(train_dataset[0]['text'])} chars")

# ============================================================
# CELL 7: Configure training
# ============================================================
# from trl import SFTTrainer
# from transformers import TrainingArguments
#
# training_args = TrainingArguments(
#     output_dir="telco-slm-7b-output",
#     num_train_epochs=3,
#     per_device_train_batch_size=2,
#     gradient_accumulation_steps=8,
#     learning_rate=2e-4,
#     warmup_ratio=0.05,
#     fp16=not torch.cuda.is_bf16_supported(),
#     bf16=torch.cuda.is_bf16_supported(),
#     logging_steps=10,
#     save_steps=500,
#     save_total_limit=3,
#     eval_strategy="steps",
#     eval_steps=500,
#     optim="adamw_8bit",
#     weight_decay=0.01,
#     lr_scheduler_type="cosine",
#     seed=42,
#     report_to="none",
# )
#
# trainer = SFTTrainer(
#     model=model,
#     tokenizer=tokenizer,
#     train_dataset=train_dataset,
#     eval_dataset=val_dataset,
#     args=training_args,
#     dataset_text_field="text",
#     max_seq_length=2048,
#     packing=True,
# )
#
# print(f"Ready to train. Estimated steps: {len(train_dataset) * 3 // (2 * 8)}")

# ============================================================
# CELL 8: Train!
# ============================================================
# trainer.train()

# ============================================================
# CELL 9: Save LoRA adapter
# ============================================================
# model.save_pretrained("telco-slm-7b-adapter")
# tokenizer.save_pretrained("telco-slm-7b-adapter")
# print("LoRA adapter saved!")

# ============================================================
# CELL 10: Save as GGUF for Ollama (optional)
# ============================================================
# model.save_pretrained_gguf(
#     "telco-slm-7b-gguf",
#     tokenizer,
#     quantization_method="q4_k_m",
# )
# print("GGUF saved!")

# ============================================================
# CELL 11: Download files to your Mac
# ============================================================
# import shutil
# shutil.make_archive("telco-slm-7b-adapter", "zip", "telco-slm-7b-adapter")
# files.download("telco-slm-7b-adapter.zip")
#
# # If GGUF was created:
# # shutil.make_archive("telco-slm-7b-gguf", "zip", "telco-slm-7b-gguf")
# # files.download("telco-slm-7b-gguf.zip")
