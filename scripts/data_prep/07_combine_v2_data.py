"""
Combine cleaned training data + new protocol + KPI data into v2 training set.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# Source files
cleaned_train = DATA_DIR / "v2_cleaned_train.jsonl"
protocol_data = DATA_DIR / "v2_protocol_knowledge.jsonl"
kpi_data = DATA_DIR / "v2_kpi_analysis.jsonl"

# Output
output_file = DATA_DIR / "train_v2.jsonl"

def load_jsonl(path):
    if not path.exists():
        print(f"  MISSING: {path}")
        return []
    with open(path) as f:
        data = [json.loads(line) for line in f if line.strip()]
    print(f"  {path.name}: {len(data)} records")
    return data

print("Loading data sources...")
all_data = []
all_data.extend(load_jsonl(cleaned_train))
all_data.extend(load_jsonl(protocol_data))
all_data.extend(load_jsonl(kpi_data))

# Validate each record has messages with system/user/assistant
valid = []
invalid = 0
for record in all_data:
    msgs = record.get("messages", [])
    roles = [m.get("role") for m in msgs]
    if "user" in roles and "assistant" in roles:
        valid.append(record)
    else:
        invalid += 1

print(f"\nTotal valid records: {len(valid)}")
if invalid:
    print(f"Dropped {invalid} invalid records")

# Category distribution
categories = {}
for r in valid:
    cat = r.get("category", "unknown")
    categories[cat] = categories.get(cat, 0) + 1

print(f"\nCategory distribution:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {cat:30s} {count:6d}")

# Write output
with open(output_file, "w") as f:
    for record in valid:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\nWritten: {output_file}")
print(f"Total: {len(valid)} records")
