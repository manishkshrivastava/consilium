"""
Phase 2: Fine-tune Qwen 2.5 3B on telco data using MLX + LoRA
- Optimized for Apple Silicon (M4 Pro, 24GB unified memory)
- MLX is Apple's native ML framework — much faster than PyTorch MPS
- LoRA keeps trainable parameters small

Usage:
  python scripts/training/train_mlx.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "mlx_format"
OUTPUT_DIR = PROJECT_ROOT / "models" / "telco-slm-v1-mlx"

# =============================================================================
# Configuration
# =============================================================================
MODEL = "Qwen/Qwen2.5-3B-Instruct"

# LoRA config
LORA_RANK = 16
LORA_LAYERS = 16  # Number of layers to apply LoRA to

# Training config
BATCH_SIZE = 4
LEARNING_RATE = 1e-5
NUM_ITERS = 4000       # Total training iterations
STEPS_PER_EVAL = 200   # Evaluate every N steps
SAVE_EVERY = 200       # Save checkpoint every N steps
MAX_SEQ_LENGTH = 2048
GRAD_CHECKPOINT = True  # Save memory with gradient checkpointing


def main():
    print("=" * 60)
    print("TELCO SLM - Phase 2: MLX LoRA Fine-Tuning")
    print("=" * 60)
    print(f"\n  Model: {MODEL}")
    print(f"  LoRA rank: {LORA_RANK}")
    print(f"  LoRA layers: {LORA_LAYERS}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Learning rate: {LEARNING_RATE}")
    print(f"  Iterations: {NUM_ITERS}")
    print(f"  Max sequence length: {MAX_SEQ_LENGTH}")
    print(f"  Output: {OUTPUT_DIR}")
    print()

    # Check data exists
    train_file = DATA_DIR / "train.jsonl"
    valid_file = DATA_DIR / "valid.jsonl"

    if not train_file.exists():
        print("ERROR: Training data not found. Run prepare_mlx_data.py first.")
        sys.exit(1)

    # Count training examples
    with open(train_file) as f:
        train_count = sum(1 for _ in f)
    print(f"  Training examples: {train_count}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build the mlx_lm.lora command
    cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model", MODEL,
        "--train",
        "--data", str(DATA_DIR),
        "--adapter-path", str(OUTPUT_DIR / "adapter"),
        "--iters", str(NUM_ITERS),
        "--batch-size", str(BATCH_SIZE),
        "--lora-rank", str(LORA_RANK),
        "--lora-layers", str(LORA_LAYERS),
        "--learning-rate", str(LEARNING_RATE),
        "--steps-per-eval", str(STEPS_PER_EVAL),
        "--save-every", str(SAVE_EVERY),
        "--max-seq-length", str(MAX_SEQ_LENGTH),
    ]

    if GRAD_CHECKPOINT:
        cmd.append("--grad-checkpoint")

    print(f"\n  Running: {' '.join(cmd[-10:])}")
    print(f"  {'='*40}")
    print()

    # Run training
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode != 0:
        print(f"\nTraining failed with exit code {result.returncode}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Training Complete!")
    print(f"  Adapter saved to: {OUTPUT_DIR / 'adapter'}")
    print()
    print("Next steps:")
    print(f"  1. Test: python scripts/training/test_model.py")
    print(f"  2. Fuse adapter into model:")
    print(f"     python -m mlx_lm.fuse --model {MODEL} --adapter-path {OUTPUT_DIR / 'adapter'} --save-path {OUTPUT_DIR / 'fused'}")
    print(f"  3. Convert to GGUF for Ollama:")
    print(f"     python -m mlx_lm.convert --hf-path {OUTPUT_DIR / 'fused'} --mlx-path {OUTPUT_DIR / 'mlx'} -q")
    print("=" * 60)


if __name__ == "__main__":
    main()
