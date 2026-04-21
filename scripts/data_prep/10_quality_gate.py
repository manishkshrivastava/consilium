#!/usr/bin/env python3
"""
10_quality_gate.py — Quality gate for synthetic training data.

Checks:
  1. JSON/schema validity
  2. Exact + near-duplicate detection (via trigram similarity)
  3. Answer length distribution
  4. Topic coverage balance (keyword clustering)
  5. Shallow answer detection (generic/low-quality markers)
  6. Random sample export for manual review

Usage:
  python 10_quality_gate.py data/v2_synthetic/kpi_rca.jsonl [--sample 200] [--dedup-threshold 0.85]

Outputs:
  - Console report
  - <input>_qc_report.json — full stats
  - <input>_duplicates.jsonl — flagged duplicates
  - <input>_sample_review.jsonl — random sample for manual review
  - <input>_cleaned.jsonl — deduplicated clean output
"""

import json
import sys
import argparse
import random
import re
from pathlib import Path
from collections import Counter, defaultdict


# ─── Schema Validation ───────────────────────────────────────────────────────

def validate_schema(records):
    """Check each record has valid ChatML structure."""
    issues = []
    valid = []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            issues.append((i, "not a dict"))
            continue
        msgs = rec.get("messages")
        if not isinstance(msgs, list) or len(msgs) != 3:
            issues.append((i, f"messages length={len(msgs) if isinstance(msgs, list) else 'missing'}"))
            continue
        roles = [m.get("role") for m in msgs]
        if roles != ["system", "user", "assistant"]:
            issues.append((i, f"wrong roles: {roles}"))
            continue
        if not all(m.get("content") for m in msgs):
            issues.append((i, "empty content"))
            continue
        valid.append(rec)
    return valid, issues


# ─── Duplicate Detection ─────────────────────────────────────────────────────

def get_trigrams(text):
    """Get character trigram set for similarity."""
    text = text.lower().strip()
    return set(text[i:i+3] for i in range(len(text) - 2))


def jaccard_similarity(set_a, set_b):
    """Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def find_duplicates(records, threshold=0.85):
    """Find exact and near-duplicate questions."""
    exact_dupes = []
    near_dupes = []
    seen_exact = {}
    questions = []

    for i, rec in enumerate(records):
        q = rec["messages"][1]["content"].strip()
        q_lower = q.lower()

        # Exact duplicate check
        if q_lower in seen_exact:
            exact_dupes.append((i, seen_exact[q_lower], q[:100]))
        else:
            seen_exact[q_lower] = i

        questions.append((i, q, get_trigrams(q)))

    # Near-duplicate check (sample-based for performance)
    # Compare each question against a window of recent ones
    window_size = 200
    for idx in range(len(questions)):
        i, q_i, tri_i = questions[idx]
        start = max(0, idx - window_size)
        for jdx in range(start, idx):
            j, q_j, tri_j = questions[jdx]
            sim = jaccard_similarity(tri_i, tri_j)
            if sim >= threshold and (i, j) not in [(d[0], d[1]) for d in exact_dupes]:
                near_dupes.append((i, j, sim, q_i[:80], q_j[:80]))

    return exact_dupes, near_dupes


# ─── Answer Quality Checks ──────────────────────────────────────────────────

SHALLOW_MARKERS = [
    r"contact (your |the )?vendor",
    r"contact (your |the )?support",
    r"reach out to",
    r"please consult",
    r"it depends on (your |the )?specific",
    r"there are many (possible |potential )?reasons",
    r"this is a complex (topic|issue|problem)",
    r"further (investigation|analysis) (is |would be )?(needed|required)",
    r"hope this helps",
    r"let me know if",
    r"I('d| would) recommend (consulting|reaching|checking with)",
]

QUALITY_MARKERS = [
    r"\b(counter|KPI|timer|parameter|threshold)\b",
    r"\b(TS \d{2}\.\d{3}|3GPP)\b",
    r"\b(RSRP|RSRQ|SINR|CQI|MCS|BLER|PRB|RRC|NAS|NGAP|S1AP)\b",
    r"\b(eNB|gNB|MME|AMF|SMF|UPF|PCF|UDM)\b",
    r"\b(cause|root cause|symptom|diagnos|remediat|mitigat)\b",
    r"\b(step \d|check |verify |inspect |monitor )\b",
]


def analyze_answer_quality(records):
    """Analyze answer quality across all records."""
    lengths = []
    shallow_flags = []
    quality_scores = []

    for i, rec in enumerate(records):
        answer = rec["messages"][2]["content"]
        lengths.append(len(answer))

        # Check for shallow markers
        shallow_count = sum(1 for pat in SHALLOW_MARKERS if re.search(pat, answer, re.I))
        if shallow_count >= 2:
            shallow_flags.append((i, shallow_count, rec["messages"][1]["content"][:80]))

        # Check for quality markers (domain specificity)
        quality_count = sum(1 for pat in QUALITY_MARKERS if re.search(pat, answer, re.I))
        quality_scores.append(quality_count)

    return lengths, shallow_flags, quality_scores


# ─── Topic Coverage ──────────────────────────────────────────────────────────

KPI_TOPIC_KEYWORDS = {
    "accessibility / attach / registration": [
        "rrc setup", "attach", "registration", "rach", "preamble", "accessibility", "s1 setup", "ng setup"
    ],
    "retainability / drops": [
        "erab drop", "call drop", "drb", "retainability", "release", "radio link failure", "rlf"
    ],
    "throughput / data": [
        "throughput", "mcs", "data rate", "capacity", "prb utilization", "dl throughput", "ul throughput",
        "carrier aggregation", "mimo", "rank"
    ],
    "handover / mobility": [
        "handover", "ho ", "inter-rat", "intra-freq", "inter-freq", "ping-pong", "x2", "xn",
        "srvcc", "daps", "conditional handover", "mobility"
    ],
    "latency": [
        "latency", "delay", "rtt", "control plane", "user plane", "urllc", "jitter"
    ],
    "volte / ims / voice": [
        "volte", "mos", "ims", "sip", "vonr", "voice", "codec", "evs", "amr", "rtp", "esrvcc"
    ],
    "interference / rf": [
        "interference", "rtwp", "iot", "sinr", "rsrp", "cqi", "beam", "ssb", "csi-rs", "bler"
    ],
    "signaling / core": [
        "signaling", "nas", "paging", "tau", "s1ap", "ngap", "gtp", "mme", "amf", "smf"
    ],
    "transport / backhaul": [
        "transport", "backhaul", "fronthaul", "ipsec", "vlan", "ptp", "sync", "mtu"
    ],
    "energy / infra": [
        "energy", "power", "sleep mode", "power headroom"
    ],
}

PROTOCOL_TOPIC_KEYWORDS = {
    "mobility procedures": [
        "tau", "registration", "service request", "deregistration", "handover", "paging"
    ],
    "session management": [
        "pdu session", "bearer", "pfcp", "gtp-u", "upf", "qos flow", "apn", "dnn"
    ],
    "slicing": [
        "s-nssai", "slice", "sst", "nssf", "nssaa"
    ],
    "ran architecture": [
        "cu-du", "cu-cp", "cu-up", "f1", "e1", "rrc", "mac scheduler", "bwp"
    ],
    "o-ran": [
        "o-ran", "ric", "xapp", "rapp", "e2", "a1", "o1", "o2", "smo", "fronthaul 7.2"
    ],
    "phy / beam": [
        "ssb", "csi-rs", "beam", "harq", "coreset", "search space", "pdcch"
    ],
    "carrier agg / dual connectivity": [
        "carrier aggregation", "en-dc", "nr-dc", "scell", "mcg", "scg", "split bearer"
    ],
    "qos": [
        "5qi", "qos", "gbr", "non-gbr", "reflective qos", "pcc", "qfi"
    ],
    "ims / voice": [
        "ims", "cscf", "sip", "volte", "vonr", "srvcc", "eps fallback"
    ],
    "security": [
        "ausf", "seaf", "5g-aka", "eap-aka", "supi", "suci", "sepp", "nas security"
    ],
    "sba / core nf": [
        "sba", "nrf", "http/2", "sbi", "amf", "smf", "pcf", "udm", "udr", "nef", "nwdaf"
    ],
}


def analyze_topic_coverage(records, topic_keywords):
    """Classify records into topics and check coverage balance."""
    topic_counts = Counter()
    unclassified = 0

    for rec in records:
        q = rec["messages"][1]["content"].lower()
        a = rec["messages"][2]["content"].lower()
        text = q + " " + a

        matched = False
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topic_counts[topic] += 1
                matched = True
                break  # Count in first matching topic only

        if not matched:
            unclassified += 1

    return topic_counts, unclassified


# ─── Report ──────────────────────────────────────────────────────────────────

def print_bar(label, count, total, width=30):
    """Print a simple text bar chart."""
    pct = count / total * 100 if total > 0 else 0
    filled = int(width * count / total) if total > 0 else 0
    bar = "█" * filled + "░" * (width - filled)
    print(f"  {label:40s} {bar} {count:5d} ({pct:4.1f}%)")


def run_qc(input_file, sample_size=200, dedup_threshold=0.85):
    """Run full quality gate on a JSONL file."""
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ File not found: {input_path}")
        return

    # Determine topic keywords based on filename
    if "kpi" in input_path.name.lower() or "rca" in input_path.name.lower():
        topic_keywords = KPI_TOPIC_KEYWORDS
        file_type = "KPI/RCA"
    elif "protocol" in input_path.name.lower():
        topic_keywords = PROTOCOL_TOPIC_KEYWORDS
        file_type = "Protocol"
    elif "troubleshoot" in input_path.name.lower():
        topic_keywords = KPI_TOPIC_KEYWORDS  # Use KPI topics for troubleshooting too
        file_type = "Troubleshooting"
    else:
        topic_keywords = KPI_TOPIC_KEYWORDS
        file_type = "Unknown"

    # Load records
    print(f"\n{'='*70}")
    print(f"📋 QUALITY GATE: {input_path.name} ({file_type})")
    print(f"{'='*70}")

    records = []
    parse_errors = 0
    with open(input_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                parse_errors += 1

    print(f"\n📊 BASIC STATS")
    print(f"  Total lines:    {len(records) + parse_errors}")
    print(f"  Valid JSON:     {len(records)}")
    print(f"  Parse errors:   {parse_errors}")

    # 1. Schema validation
    print(f"\n📋 SCHEMA VALIDATION")
    valid_records, schema_issues = validate_schema(records)
    print(f"  Valid schema:   {len(valid_records)}")
    print(f"  Schema issues:  {len(schema_issues)}")
    if schema_issues[:5]:
        for idx, issue in schema_issues[:5]:
            print(f"    Line {idx}: {issue}")

    # 2. Duplicates
    print(f"\n🔍 DUPLICATE DETECTION (threshold={dedup_threshold})")
    exact_dupes, near_dupes = find_duplicates(valid_records, dedup_threshold)
    print(f"  Exact duplicates:  {len(exact_dupes)}")
    print(f"  Near-duplicates:   {len(near_dupes)}")
    if exact_dupes[:3]:
        print(f"  Sample exact dupes:")
        for i, j, q in exact_dupes[:3]:
            print(f"    #{i} = #{j}: {q}")
    if near_dupes[:3]:
        print(f"  Sample near-dupes:")
        for i, j, sim, qi, qj in near_dupes[:3]:
            print(f"    #{i} vs #{j} (sim={sim:.2f})")
            print(f"      A: {qi}")
            print(f"      B: {qj}")

    # 3. Answer quality
    print(f"\n📏 ANSWER LENGTH DISTRIBUTION")
    lengths, shallow_flags, quality_scores = analyze_answer_quality(valid_records)
    if lengths:
        lengths_sorted = sorted(lengths)
        print(f"  Min:     {min(lengths):,} chars")
        print(f"  P10:     {lengths_sorted[len(lengths)//10]:,} chars")
        print(f"  Median:  {lengths_sorted[len(lengths)//2]:,} chars")
        print(f"  P90:     {lengths_sorted[int(len(lengths)*0.9)]:,} chars")
        print(f"  Max:     {max(lengths):,} chars")
        print(f"  Mean:    {sum(lengths)//len(lengths):,} chars")

        # Length buckets
        print(f"\n  Length distribution:")
        buckets = [(0, 500, "< 500 (too short?)"),
                   (500, 1000, "500–1000 (concise)"),
                   (1000, 2000, "1000–2000 (standard)"),
                   (2000, 3000, "2000–3000 (detailed)"),
                   (3000, 99999, "3000+ (very long)")]
        for lo, hi, label in buckets:
            count = sum(1 for l in lengths if lo <= l < hi)
            print_bar(label, count, len(lengths))

    # 4. Shallow answer detection
    print(f"\n⚠️  SHALLOW ANSWER FLAGS")
    print(f"  Flagged as shallow: {len(shallow_flags)} / {len(valid_records)} ({100*len(shallow_flags)/max(1,len(valid_records)):.1f}%)")
    if shallow_flags[:3]:
        for idx, count, q in shallow_flags[:3]:
            print(f"    #{idx} (markers={count}): {q}")

    # 5. Quality scores (domain specificity)
    print(f"\n🎯 DOMAIN SPECIFICITY (quality marker count per answer)")
    if quality_scores:
        avg_q = sum(quality_scores) / len(quality_scores)
        low_quality = sum(1 for s in quality_scores if s <= 1)
        high_quality = sum(1 for s in quality_scores if s >= 4)
        print(f"  Average markers/answer: {avg_q:.1f}")
        print(f"  Low specificity (≤1):   {low_quality} ({100*low_quality/len(quality_scores):.1f}%)")
        print(f"  High specificity (≥4):  {high_quality} ({100*high_quality/len(quality_scores):.1f}%)")

    # 6. Topic coverage
    print(f"\n📊 TOPIC COVERAGE")
    topic_counts, unclassified = analyze_topic_coverage(valid_records, topic_keywords)
    total_classified = sum(topic_counts.values())
    for topic in sorted(topic_keywords.keys()):
        count = topic_counts.get(topic, 0)
        print_bar(topic, count, len(valid_records))
    print_bar("unclassified", unclassified, len(valid_records))

    # ─── Output files ────────────────────────────────────────────────────

    base = input_path.stem
    output_dir = input_path.parent

    # Save duplicate list
    dupe_file = output_dir / f"{base}_duplicates.jsonl"
    dupe_indices = set()
    for i, j, q in exact_dupes:
        dupe_indices.add(i)
    for i, j, sim, qi, qj in near_dupes:
        dupe_indices.add(i)
    with open(dupe_file, "w") as f:
        for idx in sorted(dupe_indices):
            f.write(json.dumps({"index": idx, "record": valid_records[idx]}, ensure_ascii=False) + "\n")
    print(f"\n💾 Duplicates saved: {dupe_file} ({len(dupe_indices)} records)")

    # Save cleaned (deduped) version
    cleaned_file = output_dir / f"{base}_cleaned.jsonl"
    cleaned_count = 0
    with open(cleaned_file, "w") as f:
        for i, rec in enumerate(valid_records):
            if i not in dupe_indices:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                cleaned_count += 1
    print(f"💾 Cleaned saved:    {cleaned_file} ({cleaned_count} records)")

    # Save random sample for manual review
    sample_file = output_dir / f"{base}_sample_review.jsonl"
    sample_indices = random.sample(range(len(valid_records)), min(sample_size, len(valid_records)))
    with open(sample_file, "w") as f:
        for idx in sorted(sample_indices):
            rec = valid_records[idx]
            f.write(json.dumps({
                "index": idx,
                "question": rec["messages"][1]["content"],
                "answer": rec["messages"][2]["content"],
                "answer_length": len(rec["messages"][2]["content"]),
            }, ensure_ascii=False) + "\n")
    print(f"💾 Review sample:    {sample_file} ({len(sample_indices)} records)")

    # Save full report as JSON
    report = {
        "file": str(input_path),
        "type": file_type,
        "total_records": len(records),
        "valid_schema": len(valid_records),
        "parse_errors": parse_errors,
        "schema_issues": len(schema_issues),
        "exact_duplicates": len(exact_dupes),
        "near_duplicates": len(near_dupes),
        "total_duplicates_removed": len(dupe_indices),
        "cleaned_count": cleaned_count,
        "answer_length": {
            "min": min(lengths) if lengths else 0,
            "median": lengths_sorted[len(lengths)//2] if lengths else 0,
            "mean": sum(lengths)//len(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
        },
        "shallow_flags": len(shallow_flags),
        "avg_quality_score": round(avg_q, 1) if quality_scores else 0,
        "topic_coverage": dict(topic_counts),
        "unclassified": unclassified,
    }
    report_file = output_dir / f"{base}_qc_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"💾 QC report:        {report_file}")

    # ─── Summary verdict ─────────────────────────────────────────────────

    print(f"\n{'='*70}")
    print(f"📊 VERDICT")
    issues_found = []
    if parse_errors > 0:
        issues_found.append(f"{parse_errors} parse errors")
    if len(exact_dupes) > len(valid_records) * 0.02:
        issues_found.append(f"{len(exact_dupes)} exact duplicates (>{2}%)")
    if len(near_dupes) > len(valid_records) * 0.05:
        issues_found.append(f"{len(near_dupes)} near-duplicates (>{5}%)")
    if len(shallow_flags) > len(valid_records) * 0.05:
        issues_found.append(f"{len(shallow_flags)} shallow answers (>{5}%)")
    if quality_scores and avg_q < 2.0:
        issues_found.append(f"low domain specificity (avg={avg_q:.1f})")

    # Check topic imbalance
    if topic_counts:
        max_topic = max(topic_counts.values())
        min_topic = min(topic_counts.values()) if len(topic_counts) == len(topic_keywords) else 0
        if max_topic > 0 and min_topic / max_topic < 0.1:
            issues_found.append("severe topic imbalance")

    if not issues_found:
        print(f"  ✅ PASS — no major issues found")
    else:
        print(f"  ⚠️  ISSUES FOUND:")
        for issue in issues_found:
            print(f"    - {issue}")
    print(f"  📦 Clean dataset: {cleaned_count} records (from {len(valid_records)})")
    print(f"{'='*70}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Quality gate for synthetic training data")
    parser.add_argument("input_file", help="JSONL file to check")
    parser.add_argument("--sample", type=int, default=200, help="Sample size for manual review (default: 200)")
    parser.add_argument("--dedup-threshold", type=float, default=0.85, help="Near-duplicate similarity threshold (default: 0.85)")
    args = parser.parse_args()

    random.seed(42)
    run_qc(args.input_file, args.sample, args.dedup_threshold)


if __name__ == "__main__":
    main()
