# TelcoGPT / Unsloth Training Setup Playbook
*Clean, repeatable setup guide — tested on RunPod A40*
*Last updated: 2026-03-28*

---

## Platform Selection

| Platform | GPU | Cost | Setup | Best For |
|----------|-----|------|-------|----------|
| **Kaggle** | T4 (16GB) | Free | Simple | Quick experiments, budget |
| **Google Colab Pro** | A100 (40GB) | $10/month | Simple | Fast training, easy setup |
| **RunPod** | A40 (48GB) | $0.41/hr | Simple (see below) | Full control, large datasets |

---

## OPTION A: Kaggle / Colab Setup

### Cell 1 — Install
```python
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" --quiet
!pip install "git+https://github.com/unslothai/unsloth-zoo.git" --quiet
```

### Restart Kernel

### Cell 2 — Verify
```python
import torch
from unsloth import FastLanguageModel
print(f"Torch: {torch.__version__}, CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name()}")
print("READY")
```

### Cell 3 — Train (paste training script)

**If torchao error:** `!pip uninstall -y torchao` → restart kernel → retry

---

## OPTION B: RunPod Setup (RECOMMENDED — Tested 2026-03-28)

### Pod Configuration
- **GPU:** A40 (recommended) or any with 20+ GB VRAM
- **Region:** CA-MTL-1 (Montreal) or US — avoid Israel (slow downloads)
- **Container Disk:** 40 GB minimum
- **Volume Disk:** 100 GB
- **Template:** RunPod PyTorch (any version — we override packages)

### Cell 1 — Install (%%bash cell)

```bash
%%bash
pip install "unsloth[cu124-torch260]" --quiet
pip install rich --quiet
echo "DONE"
```

**Expected warnings (safe to ignore):**
- `torchaudio X requires torch==X but you have torch Y` — we don't use torchaudio
- `pip's dependency resolver does not currently take into account...` — pip noise
- `WARNING: Running pip as the 'root' user` — normal on RunPod

**If you see actual errors** (not warnings), stop and start a fresh pod.

### Restart Kernel (MANDATORY)

### Cell 2 — Verify Environment
```python
import torch
print(f"Torch: {torch.__version__}")
print(f"CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
from unsloth import FastLanguageModel
print("Unsloth: OK")
print("ALL CLEAR - ready to train!")
```

**Expected output:**
```
Torch: 2.6.0+cu124
CUDA: True
GPU: NVIDIA A40
Unsloth: OK
ALL CLEAR - ready to train!
```

**Known harmless messages:**
- `Flash Attention 2 installation seems to be broken. Using Xformers instead.` — no performance impact
- `Will patch your computer to enable 2x faster free finetuning` — normal unsloth banner

### Cell 3 — Upload Data
Upload `train.jsonl` to `/workspace/` via Jupyter file browser (left sidebar).

### Cell 4 — Training Script (Llama 3.1 8B)
```python
import json, os, torch, zipfile
from unsloth import FastLanguageModel
from datasets import Dataset
from unsloth import UnslothTrainer, UnslothTrainingArguments

print("1. Loading Llama 3.1-8B...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
    max_seq_length=512,
    load_in_4bit=True,
)
print(f"   GPU: {torch.cuda.get_device_name()}")

print("2. Adding LoRA...")
model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=32, lora_dropout=0.0,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    bias="none", use_gradient_checkpointing="unsloth", random_state=42,
)

print("3. Loading data...")
def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]

train_data = load_jsonl("/workspace/train.jsonl")
print(f"   Records: {len(train_data)}")
print(f"   Sample: {train_data[0]['messages'][1]['content'][:100]}")

def format_to_text(example):
    text = tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False
    )
    return {"text": text}

train_dataset = Dataset.from_list(train_data).map(format_to_text)

print("4. Starting training...")
trainer = UnslothTrainer(
    model=model, tokenizer=tokenizer, train_dataset=train_dataset,
    args=UnslothTrainingArguments(
        output_dir="/workspace/llama-telco-v2-output",
        num_train_epochs=1,
        per_device_train_batch_size=8,    # A40 optimized
        gradient_accumulation_steps=2,     # effective batch = 16
        learning_rate=2e-4,
        warmup_steps=50,
        bf16=True,
        logging_steps=10,
        save_steps=500,
        save_total_limit=2,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",
    ),
    dataset_text_field="text",
    max_seq_length=512,
    packing=True,
)

trainer.train()
print("TRAINING COMPLETE!")

print("5. Saving adapter...")
ADAPTER_PATH = "/workspace/llama-telco-v2-adapter"
model.save_pretrained(ADAPTER_PATH)
tokenizer.save_pretrained(ADAPTER_PATH)

ZIP_PATH = "/workspace/llama-telco-v2-adapter.zip"
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ADAPTER_PATH):
        for file in files:
            filepath = os.path.join(root, file)
            zf.write(filepath, os.path.relpath(filepath, ADAPTER_PATH))
print(f"Zipped: {ZIP_PATH} ({os.path.getsize(ZIP_PATH)/1e6:.1f} MB)")
```

### Cell 5 — Download
Navigate to `/workspace/` in Jupyter file browser → right-click `llama-telco-v2-adapter.zip` → Download.

### STOP THE POD when done.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `CUDA: False` | torch not built for this GPU driver | Reinstall unsloth: `pip install "unsloth[cu124-torch260]"` |
| `NotImplementedError` on model load | Unsloth version too old for model | Use latest unsloth, NOT pinned versions |
| `No module named 'rich'` | Missing dependency | `pip install rich` |
| `Flash Attention broken, using Xformers` | Flash Attention not compiled | Harmless — Xformers performance is identical |
| `torchaudio requires torch==X` | Pre-installed torchaudio version mismatch | Ignore — we don't use torchaudio |
| `Disk quota exceeded` | Volume disk full | `du -sh /workspace/*` and clean old files |
| `No space left on device` | Container disk full | Need 40GB+ container disk |
| Corrupted numpy (`~umpy` warnings) | Multiple force-reinstalls broke pip | Start a fresh pod — don't try to fix |
| Any persistent env issues | Accumulated install conflicts | **Fresh pod > fixing broken pod** |

---

## Key Principles (Learned the Hard Way)

1. **Use `unsloth[cu124-torch260]`** — one command installs everything correctly. Don't manually pin versions.
2. **Always restart kernel after install** — Python caches old module versions
3. **Always verify before training** — check CUDA, GPU, and unsloth import
4. **Container disk ≥ 40GB** — ML packages are huge
5. **Fresh pod > fixing broken pod** — if you hit weird errors after multiple installs, start over
6. **Ignore pip warnings** — dependency resolver warnings and root user warnings are harmless on RunPod
7. **Don't force-reinstall repeatedly** — it corrupts pip's package metadata (the `~umpy` problem)

---

## What NOT to Do

- **Don't pin unsloth to old versions** (e.g., `unsloth==2024.11.8`) — they lack support for newer model paths
- **Don't use `--no-deps`** with unsloth — it misses required dependencies
- **Don't run multiple `--force-reinstall` passes** — corrupts pip state
- **Don't try to fix a broken environment** — fresh pod takes 5 min, debugging takes hours

---

## Version Matrix (Tested 2026-03-28 on RunPod A40)

Installed via `pip install "unsloth[cu124-torch260]"`:

| Package | Version | Notes |
|---------|---------|-------|
| torch | 2.6.0+cu124 | Installed by unsloth |
| unsloth | latest | cu124-torch260 variant |
| rich | latest | Must install separately |
| Everything else | Auto-resolved | unsloth handles dependencies |

---

## Supported Models

| Model | Unsloth Name | Origin | License |
|-------|-------------|--------|---------|
| Llama 3.1-8B-Instruct | `unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit` | Meta (USA) | Llama License |
| Qwen 2.5-7B-Instruct | `unsloth/Qwen2.5-7B-Instruct-bnb-4bit` | Alibaba (China) | Apache 2.0 |
| Llama 3-8B-Instruct | `unsloth/llama-3-8b-Instruct-bnb-4bit` | Meta (USA) | Llama License |
| Mistral 7B-Instruct | `unsloth/mistral-7b-instruct-v0.3-bnb-4bit` | Mistral (France) | Apache 2.0 |

---

## Training History

| Version | Base Model | Data | GPU | Steps | Loss | Overall | Notes |
|---------|-----------|------|-----|-------|------|---------|-------|
| Qwen FT v1 | Qwen 2.5 7B | 34K | Kaggle T4 | ~2000 | ~0.35 | 79.3% | First successful run |
| Llama FT v1 | Llama 3.1 8B | 34K | RunPod A40 | 2137 | 0.33 | 78.1% | KPI 61.1%, Knowledge 73.0% |
| Llama FT v2 | Llama 3.1 8B | 49K | RunPod A40 | ~2800 | TBD | TBD | +15K synthetic targeting KPI/protocol gaps |

---

## Post-Training Pipeline (Merge → GGUF → Ollama)

After training completes and adapter is downloaded to Mac:

1. **Merge adapter** — use `device_map="auto"` (GPU merge on RunPod, 3-5 min)
2. **Convert to GGUF** — clone llama.cpp, run `convert_hf_to_gguf.py`
3. **Quantize** — `llama-quantize` to Q4_K_M (~4.6 GB)
4. **Create Ollama model** — `ollama create` with Modelfile
5. **Benchmark** — run benchmark suite, compare per-category scores
