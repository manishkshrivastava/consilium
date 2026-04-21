"""
Step 2: Explore and understand the downloaded telco data
- Analyze TSpec-LLM structure (3GPP documents)
- Understand document types, lengths, releases
- Check TeleQnA benchmark format
"""

from pathlib import Path
from collections import Counter
import json
import os

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
TSPEC_DIR = DATA_DIR / "tspec_llm"
TELEQNA_DIR = DATA_DIR / "teleqna"


def explore_tspec():
    """Analyze the TSpec-LLM dataset structure."""
    print("=" * 60)
    print("TSpec-LLM Dataset Analysis")
    print("=" * 60)

    if not TSPEC_DIR.exists():
        print(f"TSpec-LLM not found at {TSPEC_DIR}")
        print("Run 01_download_tspec.py first.")
        return

    # Count files by type
    extensions = Counter()
    total_size = 0
    file_count = 0

    for f in TSPEC_DIR.rglob("*"):
        if f.is_file():
            extensions[f.suffix.lower()] += 1
            total_size += f.stat().st_size
            file_count += 1

    print(f"\nTotal files: {file_count}")
    print(f"Total size: {total_size / (1024**3):.2f} GB")
    print(f"\nFile types:")
    for ext, count in extensions.most_common(20):
        print(f"  {ext or '(no ext)'}: {count}")

    # Sample a few markdown files to understand structure
    md_files = list(TSPEC_DIR.rglob("*.md"))
    if md_files:
        print(f"\nMarkdown files found: {len(md_files)}")
        print("\nSample document (first 500 chars):")
        print("-" * 40)
        sample = md_files[0]
        print(f"File: {sample.name}")
        with open(sample, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(500)
            print(content)
        print("-" * 40)

        # Analyze document lengths
        lengths = []
        for md in md_files[:100]:  # Sample first 100
            try:
                with open(md, "r", encoding="utf-8", errors="ignore") as f:
                    lengths.append(len(f.read().split()))
            except Exception:
                pass

        if lengths:
            print(f"\nDocument length stats (sample of {len(lengths)}):")
            print(f"  Min words: {min(lengths):,}")
            print(f"  Max words: {max(lengths):,}")
            print(f"  Mean words: {sum(lengths) // len(lengths):,}")
            print(f"  Median words: {sorted(lengths)[len(lengths)//2]:,}")

    # Look for directory structure (releases, series)
    top_dirs = set()
    for f in TSPEC_DIR.iterdir():
        if f.is_dir() and not f.name.startswith("."):
            top_dirs.add(f.name)

    if top_dirs:
        print(f"\nTop-level directories: {sorted(top_dirs)}")


def explore_teleqna():
    """Analyze the TeleQnA benchmark dataset."""
    print("\n" + "=" * 60)
    print("TeleQnA Benchmark Analysis")
    print("=" * 60)

    dataset_dir = TELEQNA_DIR / "dataset"
    if not dataset_dir.exists() and not TELEQNA_DIR.exists():
        print(f"TeleQnA not found at {TELEQNA_DIR}")
        print("Run 01_download_tspec.py first.")
        return

    try:
        from datasets import load_from_disk
        ds = load_from_disk(str(dataset_dir))
        print(f"\nSplits: {list(ds.keys())}")

        for split_name in ds:
            split = ds[split_name]
            print(f"\n{split_name}:")
            print(f"  Examples: {len(split)}")
            print(f"  Columns: {split.column_names}")

            # Show a sample
            if len(split) > 0:
                sample = split[0]
                print(f"\n  Sample entry:")
                for k, v in sample.items():
                    val_str = str(v)[:200]
                    print(f"    {k}: {val_str}")
    except Exception as e:
        print(f"Could not load TeleQnA: {e}")

        # Try loading from raw files
        json_files = list(TELEQNA_DIR.rglob("*.json"))
        if json_files:
            print(f"\nFound JSON files: {[f.name for f in json_files]}")
            with open(json_files[0]) as f:
                data = json.load(f)
                if isinstance(data, list):
                    print(f"Entries: {len(data)}")
                    print(f"Sample: {json.dumps(data[0], indent=2)[:500]}")
                elif isinstance(data, dict):
                    print(f"Keys: {list(data.keys())}")


def print_next_steps():
    """Print what to do next."""
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    print("""
1. Run 03_prepare_training_data.py to:
   - Convert 3GPP docs into instruction-response pairs
   - Create synthetic NOC incident data
   - Format as chat/instruction templates for Llama 3.1

2. Key data categories to create:
   a) 3GPP Q&A pairs (from TSpec-LLM docs)
   b) NOC incident → diagnosis → resolution flows
   c) Intent → network configuration (YAML) pairs
   d) Troubleshooting dialogues

3. Target: 10K-50K high-quality instruction pairs for fine-tuning
""")


if __name__ == "__main__":
    explore_tspec()
    explore_teleqna()
    print_next_steps()
