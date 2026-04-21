"""
Step 1: Download TSpec-LLM dataset from HuggingFace
- All 3GPP documents (Release 8-19)
- 13.5 GB, 30,137 documents, 535 million words
- Source: rasoul-nikbakht/TSpec-LLM
"""

from datasets import load_dataset
from huggingface_hub import snapshot_download
from pathlib import Path
import json
import os

# =============================================================================
# Configuration
# =============================================================================
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
TSPEC_DIR = DATA_DIR / "tspec_llm"
TELEQNA_DIR = DATA_DIR / "teleqna"


def download_tspec_llm():
    """Download the TSpec-LLM dataset (all 3GPP documents)."""
    print("=" * 60)
    print("Downloading TSpec-LLM (3GPP Documents)")
    print("This is 13.5 GB — may take a while...")
    print("=" * 60)

    TSPEC_DIR.mkdir(parents=True, exist_ok=True)

    # Download the full dataset
    snapshot_download(
        repo_id="rasoul-nikbakht/TSpec-LLM",
        repo_type="dataset",
        local_dir=str(TSPEC_DIR),
        resume_download=True,
    )

    print(f"\nTSpec-LLM downloaded to: {TSPEC_DIR}")
    print(f"Contents:")
    for item in sorted(TSPEC_DIR.iterdir()):
        if item.is_dir():
            count = sum(1 for _ in item.rglob("*") if _.is_file())
            print(f"  {item.name}/ ({count} files)")
        else:
            size_mb = item.stat().st_size / (1024 * 1024)
            print(f"  {item.name} ({size_mb:.1f} MB)")


def download_teleqna():
    """Download the TeleQnA benchmark dataset for evaluation."""
    print("\n" + "=" * 60)
    print("Downloading TeleQnA Benchmark")
    print("=" * 60)

    TELEQNA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        ds = load_dataset("netop/TeleQnA", trust_remote_code=True)
        # Save to disk
        ds.save_to_disk(str(TELEQNA_DIR / "dataset"))
        print(f"\nTeleQnA downloaded to: {TELEQNA_DIR}")
        print(f"Splits: {list(ds.keys())}")
        for split_name, split_data in ds.items():
            print(f"  {split_name}: {len(split_data)} examples")
    except Exception as e:
        print(f"TeleQnA download failed (may need different repo ID): {e}")
        print("Try manually searching HuggingFace for 'TeleQnA' or 'GSMA telco benchmark'")


def download_tele_llm_models_info():
    """Print info about available pre-fine-tuned telco models."""
    print("\n" + "=" * 60)
    print("Available Pre-Fine-Tuned Telco Models (HuggingFace)")
    print("=" * 60)

    models = [
        {
            "name": "AliMaatouk/LLama-3-8B-Tele-it",
            "desc": "Llama 3 8B fine-tuned on telco data (Yale Tele-LLMs)",
            "size": "8B",
        },
        {
            "name": "AliMaatouk/Tele-LLMs collection",
            "desc": "Family of 1B-8B telco models",
            "size": "1B-8B",
        },
    ]

    for m in models:
        print(f"\n  Model: {m['name']}")
        print(f"  Description: {m['desc']}")
        print(f"  Size: {m['size']}")

    print("\nThese can be used as starting points or for comparison.")


if __name__ == "__main__":
    print("TELCO SLM - Phase 1: Data Download")
    print("=" * 60)

    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage(DATA_DIR.parent)
    free_gb = free / (1024 ** 3)
    print(f"\nAvailable disk space: {free_gb:.1f} GB")

    if free_gb < 20:
        print("WARNING: Less than 20 GB free. TSpec-LLM alone is ~13.5 GB.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != "y":
            print("Aborted.")
            exit(0)

    download_tspec_llm()
    download_teleqna()
    download_tele_llm_models_info()

    print("\n" + "=" * 60)
    print("Phase 1 Download Complete!")
    print("Next step: Run 02_explore_data.py to inspect the data")
    print("=" * 60)
