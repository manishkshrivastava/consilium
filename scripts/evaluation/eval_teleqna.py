"""
Evaluate TelcoGPT vs base model on TeleQnA benchmark.
Runs a sample of questions and compares accuracy.
"""

import json
import re
import time
from pathlib import Path
from datasets import load_from_disk

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TELEQNA_PATH = PROJECT_ROOT / "data" / "raw" / "teleqna" / "dataset"
ADAPTER_PATH = PROJECT_ROOT / "models" / "telco-slm-v1-mlx" / "adapter"
BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

# How many questions to evaluate (full=10000, quick=100)
N_SAMPLES = 100


def extract_answer(response: str, num_choices: int) -> int:
    """Extract the answer index from model response."""
    # Look for patterns like "1", "Answer: 1", "option 1", "A)", etc.
    response = response.strip()

    # Try to find a number 0-9 at the start
    match = re.search(r'\b([0-9])\b', response[:50])
    if match:
        return int(match.group(1))

    # Try letter-based answers (A=0, B=1, C=2, etc.)
    match = re.search(r'\b([A-E])\b', response[:50])
    if match:
        return ord(match.group(1)) - ord('A')

    return -1  # Could not parse


def format_question(question: str, choices: list) -> str:
    """Format a TeleQnA question as a prompt."""
    prompt = f"{question}\n\nChoices:\n"
    for i, choice in enumerate(choices):
        prompt += f"  {i}: {choice}\n"
    prompt += "\nAnswer with ONLY the number of the correct choice (0, 1, 2, etc.)."
    return prompt


def evaluate_model(model, tokenizer, dataset, model_name: str):
    """Run evaluation on a model."""
    correct = 0
    total = 0
    by_subject = {}

    for i in range(min(N_SAMPLES, len(dataset))):
        item = dataset[i]
        question = item["question"]
        choices = item["choices"]
        correct_answer = item["answer"]
        subject = item["subject"]

        prompt = format_question(question, choices)

        messages = [
            {"role": "system", "content": "You are a telecom expert. Answer multiple choice questions by responding with ONLY the number of the correct answer."},
            {"role": "user", "content": prompt},
        ]

        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        from mlx_lm import generate
        response = generate(model, tokenizer, prompt=text, max_tokens=20, verbose=False)
        predicted = extract_answer(response, len(choices))

        is_correct = (predicted == correct_answer)
        if is_correct:
            correct += 1
        total += 1

        # Track by subject
        if subject not in by_subject:
            by_subject[subject] = {"correct": 0, "total": 0}
        by_subject[subject]["total"] += 1
        if is_correct:
            by_subject[subject]["correct"] += 1

        if (i + 1) % 25 == 0:
            print(f"  [{model_name}] {i+1}/{N_SAMPLES} — accuracy so far: {correct}/{total} ({100*correct/total:.1f}%)")

    return correct, total, by_subject


def main():
    print("=" * 60)
    print("TELCO SLM — TeleQnA Benchmark Evaluation")
    print(f"Evaluating {N_SAMPLES} questions")
    print("=" * 60)

    # Load dataset
    ds = load_from_disk(str(TELEQNA_PATH))
    dataset = ds["test"] if "test" in ds else ds[list(ds.keys())[0]]
    print(f"\nDataset loaded: {len(dataset)} total questions")

    from mlx_lm import load

    # 1. Evaluate base model (no fine-tuning)
    print(f"\n{'='*60}")
    print(f"[1/2] Evaluating BASE model: {BASE_MODEL}")
    print(f"{'='*60}")
    base_model, base_tokenizer = load(BASE_MODEL)
    base_correct, base_total, base_by_subject = evaluate_model(
        base_model, base_tokenizer, dataset, "BASE"
    )
    # Free memory
    del base_model
    import gc; gc.collect()

    # 2. Evaluate fine-tuned model
    print(f"\n{'='*60}")
    print(f"[2/2] Evaluating FINE-TUNED model: TelcoGPT")
    print(f"{'='*60}")
    ft_model, ft_tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER_PATH))
    ft_correct, ft_total, ft_by_subject = evaluate_model(
        ft_model, ft_tokenizer, dataset, "TELCOGPT"
    )

    # Results
    print(f"\n{'='*60}")
    print(f"RESULTS — TeleQnA ({N_SAMPLES} questions)")
    print(f"{'='*60}")
    print(f"\n  Base Qwen 2.5 1.5B:  {base_correct}/{base_total} ({100*base_correct/base_total:.1f}%)")
    print(f"  TelcoGPT (fine-tuned): {ft_correct}/{ft_total} ({100*ft_correct/ft_total:.1f}%)")

    improvement = (ft_correct - base_correct) / max(base_correct, 1) * 100
    print(f"\n  Improvement: {'+' if improvement >= 0 else ''}{improvement:.1f}%")

    # By subject
    print(f"\n  By Subject:")
    print(f"  {'Subject':<25} {'Base':>10} {'TelcoGPT':>10} {'Delta':>10}")
    print(f"  {'-'*55}")
    all_subjects = set(list(base_by_subject.keys()) + list(ft_by_subject.keys()))
    for subj in sorted(all_subjects):
        b = base_by_subject.get(subj, {"correct": 0, "total": 0})
        f = ft_by_subject.get(subj, {"correct": 0, "total": 0})
        b_pct = f"{100*b['correct']/b['total']:.0f}%" if b['total'] > 0 else "N/A"
        f_pct = f"{100*f['correct']/f['total']:.0f}%" if f['total'] > 0 else "N/A"
        delta = f['correct'] - b['correct'] if b['total'] > 0 and f['total'] > 0 else 0
        print(f"  {subj:<25} {b_pct:>10} {f_pct:>10} {'+' if delta >= 0 else ''}{delta:>9}")

    # Save results
    results = {
        "benchmark": "TeleQnA",
        "n_samples": N_SAMPLES,
        "base_model": BASE_MODEL,
        "base_accuracy": base_correct / base_total,
        "finetuned_accuracy": ft_correct / ft_total,
        "base_by_subject": {k: v["correct"]/v["total"] for k, v in base_by_subject.items()},
        "finetuned_by_subject": {k: v["correct"]/v["total"] for k, v in ft_by_subject.items()},
    }

    results_path = PROJECT_ROOT / "models" / "telco-slm-v1-mlx" / "eval_teleqna.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {results_path}")


if __name__ == "__main__":
    main()
