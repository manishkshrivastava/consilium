"""
GSMA TeleQnA — Per-subject comparison across models.
Runs 200 questions per subject for each model, produces a clean comparison table.

Usage:
  python scripts/evaluation/gsma_by_subject.py
  python scripts/evaluation/gsma_by_subject.py --models llama-base llama-v41
  python scripts/evaluation/gsma_by_subject.py --models claude-sonnet
  python scripts/evaluation/gsma_by_subject.py --per-subject 100  # fewer questions per subject
"""

import json
import os
import re
import sys
import time
import random
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TELEQNA_PATH = PROJECT_ROOT / "data" / "benchmarks" / "gsma" / "teleqna_test.jsonl"
ENV_PATH = PROJECT_ROOT / ".env"

SEED = 42

OLLAMA_MODELS = {
    "llama-v41":   ("llama-telco-v41",              "Consilium v4.1"),
    "llama-base":  ("llama3.1:8b-instruct-q4_K_M",  "Llama 3.1 8B base"),
}

CLAUDE_MODELS = {
    "claude-sonnet": ("claude-sonnet-4-6",  "Claude Sonnet 4.6"),
}

ALL_MODELS = {**OLLAMA_MODELS, **CLAUDE_MODELS}

SUBJECTS = [
    "Lexicon",
    "Research overview",
    "Research publications",
    "Standards overview",
    "Standards specifications",
]


def load_api_key() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return ""


def format_mcq_prompt(question: str, choices: list[str]) -> str:
    prompt = f"{question}\n\n"
    for i, choice in enumerate(choices):
        prompt += f"  {i}) {choice}\n"
    prompt += "\nRespond with ONLY the number of the correct answer (e.g., 0, 1, 2, 3, or 4). Do not explain."
    return prompt


def extract_answer(response: str, num_choices: int) -> int:
    response = response.strip()
    match = re.match(r'^(\d)', response)
    if match:
        val = int(match.group(1))
        if 0 <= val < num_choices:
            return val
    match = re.search(r'(?:answer|option|choice)[:\s]+(\d)', response, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        if 0 <= val < num_choices:
            return val
    match = re.search(r'\b(\d)\b', response[:50])
    if match:
        val = int(match.group(1))
        if 0 <= val < num_choices:
            return val
    return -1


def query_ollama(model_name: str, system: str, prompt: str) -> str:
    import httpx
    try:
        resp = httpx.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"num_predict": 20, "temperature": 0.1},
            },
            timeout=60,
            verify=False,
        )
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"


def query_claude(client, model_name: str, system: str, prompt: str) -> str:
    try:
        resp = client.messages.create(
            model=model_name,
            max_tokens=20,
            temperature=0.1,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    except Exception as e:
        if "rate" in str(e).lower() or "429" in str(e):
            time.sleep(5)
            try:
                resp = client.messages.create(
                    model=model_name,
                    max_tokens=20,
                    temperature=0.1,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.content[0].text
            except Exception as e2:
                return f"ERROR: {e2}"
        return f"ERROR: {e}"


def run_subject(model_key: str, model_id: str, questions: list[dict], is_claude: bool) -> dict:
    """Run questions and return {correct, total, elapsed}."""
    system = (
        "You are a telecommunications expert. Answer multiple-choice questions "
        "by responding with ONLY the number of the correct answer. "
        "Do not provide explanations."
    )

    client = None
    if is_claude:
        import anthropic
        client = anthropic.Anthropic(api_key=load_api_key())

    correct = 0
    total = 0
    total_elapsed = 0

    for i, q in enumerate(questions):
        start = time.time()
        prompt = format_mcq_prompt(q["question"], q["choices"])

        if is_claude:
            answer_text = query_claude(client, model_id, system, prompt)
        else:
            answer_text = query_ollama(model_id, system, prompt)

        elapsed = time.time() - start
        total_elapsed += elapsed

        predicted = extract_answer(answer_text, len(q["choices"]))
        if predicted == q["answer"]:
            correct += 1
        total += 1

        if (i + 1) % 50 == 0:
            pct = 100 * correct / total
            print(f"    [{i+1}/{len(questions)}] {correct}/{total} ({pct:.1f}%)")

    return {"correct": correct, "total": total, "elapsed": total_elapsed}


def main():
    parser = argparse.ArgumentParser(description="GSMA TeleQnA — Per-subject comparison")
    parser.add_argument("--models", nargs="+", choices=list(ALL_MODELS.keys()),
                        default=["llama-base", "llama-v41", "claude-sonnet"],
                        help="Models to compare")
    parser.add_argument("--per-subject", type=int, default=200,
                        help="Questions per subject (default 200)")
    args = parser.parse_args()

    # Load dataset
    questions_by_subject = {s: [] for s in SUBJECTS}
    with open(TELEQNA_PATH) as f:
        for line in f:
            row = json.loads(line)
            subj = row.get("subject", "")
            if subj in questions_by_subject:
                questions_by_subject[subj].append(row)

    # Sample per subject
    for subj in SUBJECTS:
        all_q = questions_by_subject[subj]
        n = min(args.per_subject, len(all_q))
        random.seed(SEED)
        questions_by_subject[subj] = random.sample(all_q, n)
        print(f"  {subj}: {n} questions sampled from {len(all_q)}")

    # Run each model x subject
    # results[model_key][subject] = {correct, total, elapsed}
    results = {}

    for model_key in args.models:
        model_id, label = ALL_MODELS[model_key]
        is_claude = model_key in CLAUDE_MODELS
        results[model_key] = {}

        print(f"\n{'='*60}")
        print(f"Running: {label} ({model_id})")
        print(f"{'='*60}")

        for subj in SUBJECTS:
            qs = questions_by_subject[subj]
            print(f"\n  [{subj}] — {len(qs)} questions")
            r = run_subject(model_key, model_id, qs, is_claude)
            results[model_key][subj] = r
            acc = 100 * r["correct"] / r["total"]
            print(f"  Result: {r['correct']}/{r['total']} ({acc:.1f}%) in {r['elapsed']:.0f}s")

    # Print comparison table
    print(f"\n\n{'='*80}")
    print(f"GSMA TeleQnA — PER-SUBJECT COMPARISON ({args.per_subject} questions/subject)")
    print(f"{'='*80}")

    # Header
    model_labels = [ALL_MODELS[m][1] for m in args.models]
    header = f"{'Subject':<28}"
    for label in model_labels:
        header += f" {label:>18}"
    print(f"\n{header}")
    print(f"{'-' * (28 + 19 * len(args.models))}")

    # Rows
    totals = {m: {"correct": 0, "total": 0} for m in args.models}
    for subj in SUBJECTS:
        row = f"{subj:<28}"
        for model_key in args.models:
            r = results[model_key][subj]
            acc = 100 * r["correct"] / r["total"]
            row += f" {acc:>17.1f}%"
            totals[model_key]["correct"] += r["correct"]
            totals[model_key]["total"] += r["total"]
        print(row)

    # Overall
    print(f"{'-' * (28 + 19 * len(args.models))}")
    row = f"{'OVERALL':<28}"
    for model_key in args.models:
        t = totals[model_key]
        acc = 100 * t["correct"] / t["total"]
        row += f" {acc:>17.1f}%"
    print(row)

    # Delta rows (if more than 1 model)
    if len(args.models) >= 2:
        print(f"\n{'--- Deltas vs Base ---'}")
        base_key = args.models[0]
        for model_key in args.models[1:]:
            label = ALL_MODELS[model_key][1]
            print(f"\n  {label} vs {ALL_MODELS[base_key][1]}:")
            for subj in SUBJECTS:
                base_acc = 100 * results[base_key][subj]["correct"] / results[base_key][subj]["total"]
                model_acc = 100 * results[model_key][subj]["correct"] / results[model_key][subj]["total"]
                delta = model_acc - base_acc
                marker = "+" if delta >= 0 else ""
                print(f"    {subj:<28} {marker}{delta:.1f} pts")
            base_total_acc = 100 * totals[base_key]["correct"] / totals[base_key]["total"]
            model_total_acc = 100 * totals[model_key]["correct"] / totals[model_key]["total"]
            delta = model_total_acc - base_total_acc
            marker = "+" if delta >= 0 else ""
            print(f"    {'OVERALL':<28} {marker}{delta:.1f} pts")

    # Save full results
    output = {
        "benchmark": "GSMA TeleQnA — Per Subject",
        "per_subject_sample": args.per_subject,
        "seed": SEED,
        "models": args.models,
        "results": {
            model_key: {
                "label": ALL_MODELS[model_key][1],
                "by_subject": {
                    subj: {
                        "accuracy": r["correct"] / r["total"],
                        "correct": r["correct"],
                        "total": r["total"],
                    }
                    for subj, r in results[model_key].items()
                },
                "overall": {
                    "accuracy": totals[model_key]["correct"] / totals[model_key]["total"],
                    "correct": totals[model_key]["correct"],
                    "total": totals[model_key]["total"],
                },
            }
            for model_key in args.models
        },
    }

    output_path = PROJECT_ROOT / "models" / "gsma_teleqna_by_subject.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
