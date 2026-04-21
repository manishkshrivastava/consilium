"""
Convert our training data to MLX-LM expected format.
MLX-LM expects JSONL with a "messages" field (chat format) or "text" field.
Our data already has "messages" — just need to extract it cleanly.
"""

from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_TRAIN = PROJECT_ROOT / "data" / "processed" / "train.jsonl"
INPUT_VAL = PROJECT_ROOT / "data" / "processed" / "val.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "data" / "mlx_format"


def convert_to_mlx_format(input_path: Path, output_path: Path):
    """Convert our JSONL to MLX-LM chat format."""
    count = 0
    with open(input_path) as fin, open(output_path, "w") as fout:
        for line in fin:
            data = json.loads(line)
            # MLX-LM expects {"messages": [{"role": ..., "content": ...}]}
            entry = {"messages": data["messages"]}
            fout.write(json.dumps(entry) + "\n")
            count += 1
    return count


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Converting training data to MLX format...")

    train_count = convert_to_mlx_format(INPUT_TRAIN, OUTPUT_DIR / "train.jsonl")
    print(f"  Train: {train_count} examples → {OUTPUT_DIR / 'train.jsonl'}")

    val_count = convert_to_mlx_format(INPUT_VAL, OUTPUT_DIR / "valid.jsonl")
    print(f"  Valid: {val_count} examples → {OUTPUT_DIR / 'valid.jsonl'}")

    # MLX also looks for test.jsonl — create a small one from validation
    test_path = OUTPUT_DIR / "test.jsonl"
    with open(OUTPUT_DIR / "valid.jsonl") as fin:
        lines = fin.readlines()
    with open(test_path, "w") as fout:
        # Use first 100 validation examples as test
        for line in lines[:100]:
            fout.write(line)
    print(f"  Test: 100 examples → {test_path}")

    print("\nDone! Ready for MLX training.")


if __name__ == "__main__":
    main()
