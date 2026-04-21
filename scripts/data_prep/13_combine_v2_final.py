#!/usr/bin/env python3
"""
13_combine_v2_final.py — Combine v1 base + v2 synthetic into final training dataset.

Steps:
  1. Load v1 base (34,189 records)
  2. Load v2 synthetic (KPI cleaned + rebalance + protocol cleaned + troubleshooting cleaned)
  3. Dedup v2 against v1 (question-level trigram similarity)
  4. Shuffle
  5. 90/10 train/val split on new data, all v1 goes to train
  6. Output final files

Outputs:
  data/v2_final/train.jsonl
  data/v2_final/val.jsonl
  data/v2_final/stats.json
"""

import json
import random
import sys
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SYNTHETIC_DIR = DATA_DIR / "v2_synthetic"
OUTPUT_DIR = DATA_DIR / "v2_final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Config ──────────────────────────────────────────────────────────────────

V1_FILE = DATA_DIR / "processed" / "train.jsonl"

V2_FILES = [
    SYNTHETIC_DIR / "kpi_rca_cleaned.jsonl",
    SYNTHETIC_DIR / "kpi_rca_rebalance.jsonl",
    SYNTHETIC_DIR / "protocol_balanced_cleaned.jsonl",
    SYNTHETIC_DIR / "troubleshooting_balanced_cleaned.jsonl",
]

VAL_RATIO = 0.10  # 10% of new data for validation
DEDUP_THRESHOLD = 0.80  # Question similarity threshold for dedup


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_jsonl(path):
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def get_question(record):
    """Extract the user question from a ChatML record."""
    msgs = record.get("messages", [])
    for m in msgs:
        if m.get("role") == "user":
            return m.get("content", "").strip()
    return ""


def get_trigrams(text):
    text = text.lower().strip()
    return set(text[i:i+3] for i in range(len(text) - 2))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedup_v2_against_v1(v1_records, v2_records, threshold=0.80):
    """Remove v2 records that are too similar to v1 questions."""
    print(f"  Building v1 question index ({len(v1_records)} records)...")

    # Build trigram index from v1 (sample-based for performance)
    v1_questions = []
    for r in v1_records:
        q = get_question(r)
        if q:
            v1_questions.append((q, get_trigrams(q)))

    print(f"  Checking {len(v2_records)} v2 records against v1...")
    kept = []
    removed = 0

    for i, r in enumerate(v2_records):
        q = get_question(r)
        if not q:
            kept.append(r)
            continue

        tri = get_trigrams(q)
        is_dup = False

        # Check against a sample of v1 questions for performance
        # Full check would be O(n*m), so we sample
        sample_size = min(2000, len(v1_questions))
        sample = random.sample(v1_questions, sample_size) if len(v1_questions) > sample_size else v1_questions

        for v1_q, v1_tri in sample:
            if jaccard(tri, v1_tri) >= threshold:
                is_dup = True
                break

        if is_dup:
            removed += 1
        else:
            kept.append(r)

        if (i + 1) % 5000 == 0:
            print(f"    Checked {i+1}/{len(v2_records)}, removed {removed} so far")

    print(f"  Dedup complete: removed {removed}, kept {len(kept)}")
    return kept, removed


def dedup_within(records, threshold=0.85):
    """Remove exact duplicate questions within a dataset."""
    seen = {}
    kept = []
    removed = 0

    for r in records:
        q = get_question(r).lower().strip()
        if q in seen:
            removed += 1
        else:
            seen[q] = True
            kept.append(r)

    return kept, removed


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    random.seed(42)

    print("=" * 60)
    print("📊 COMBINING V2 FINAL DATASET")
    print("=" * 60)

    # 1. Load v1
    print(f"\n📂 Loading v1 base: {V1_FILE}")
    v1_records = load_jsonl(V1_FILE)
    print(f"   {len(v1_records)} records")

    # 2. Load v2 synthetic
    print(f"\n📂 Loading v2 synthetic:")
    v2_records = []
    v2_sources = {}
    for f in V2_FILES:
        if not f.exists():
            print(f"   ⚠ Missing: {f.name}")
            continue
        records = load_jsonl(f)
        v2_sources[f.name] = len(records)
        v2_records.extend(records)
        print(f"   {f.name}: {len(records)}")
    print(f"   Total v2: {len(v2_records)}")

    # 3. Dedup within v2
    print(f"\n🔍 Dedup within v2 (exact question match)...")
    v2_records, internal_removed = dedup_within(v2_records)
    print(f"   Removed {internal_removed} internal duplicates")

    # 4. Dedup v2 against v1
    print(f"\n🔍 Dedup v2 against v1 (threshold={DEDUP_THRESHOLD})...")
    v2_records, cross_removed = dedup_v2_against_v1(v1_records, v2_records, DEDUP_THRESHOLD)

    # 5. Split v2 into train/val
    print(f"\n📊 Splitting v2: {int((1-VAL_RATIO)*100)}% train / {int(VAL_RATIO*100)}% val")
    random.shuffle(v2_records)
    val_size = int(len(v2_records) * VAL_RATIO)
    v2_val = v2_records[:val_size]
    v2_train = v2_records[val_size:]
    print(f"   v2 train: {len(v2_train)}")
    print(f"   v2 val:   {len(v2_val)}")

    # 6. Combine: all v1 goes to train + v2 train
    train_records = v1_records + v2_train
    val_records = v2_val

    # Shuffle train
    random.shuffle(train_records)
    random.shuffle(val_records)

    # 7. Write output
    train_file = OUTPUT_DIR / "train.jsonl"
    val_file = OUTPUT_DIR / "val.jsonl"

    print(f"\n💾 Writing output:")
    with open(train_file, "w") as f:
        for r in train_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"   {train_file}: {len(train_records)} records")

    with open(val_file, "w") as f:
        for r in val_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"   {val_file}: {len(val_records)} records")

    # 8. Stats
    stats = {
        "v1_base": len(v1_records),
        "v2_sources": v2_sources,
        "v2_total_raw": sum(v2_sources.values()),
        "v2_internal_dupes_removed": internal_removed,
        "v2_cross_dupes_removed": cross_removed,
        "v2_after_dedup": len(v2_train) + len(v2_val),
        "train_total": len(train_records),
        "val_total": len(val_records),
        "grand_total": len(train_records) + len(val_records),
    }

    stats_file = OUTPUT_DIR / "stats.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n{'='*60}")
    print(f"📊 FINAL DATASET SUMMARY")
    print(f"{'='*60}")
    print(f"   v1 base:              {stats['v1_base']:,}")
    print(f"   v2 synthetic (raw):   {stats['v2_total_raw']:,}")
    print(f"   v2 internal dupes:    -{stats['v2_internal_dupes_removed']:,}")
    print(f"   v2 cross dupes (v1):  -{stats['v2_cross_dupes_removed']:,}")
    print(f"   v2 after dedup:       {stats['v2_after_dedup']:,}")
    print(f"   ─────────────────────────────")
    print(f"   Train:                {stats['train_total']:,}")
    print(f"   Validation:           {stats['val_total']:,}")
    print(f"   Grand total:          {stats['grand_total']:,}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
