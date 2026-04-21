"""
GSMA TeleQnA Benchmark — Industry-standard telecom evaluation.

Runs models against the GSMA/netop TeleQnA dataset (10,000 multiple-choice questions)
across 5 subject areas: Standards specs, Standards overview, Research publications,
Research overview, Lexicon.

This is an INDEPENDENT, HELD-OUT evaluation — no Consilium model was trained or
optimized against these questions. Results are directly comparable to published
GSMA leaderboard scores.

Usage:
  python scripts/evaluation/gsma_benchmark.py --model llama-v41     # Fine-tuned Consilium v4.1
  python scripts/evaluation/gsma_benchmark.py --model llama-base    # Base Llama 3.1 8B
  python scripts/evaluation/gsma_benchmark.py --model phi4          # Phi-4 14B
  python scripts/evaluation/gsma_benchmark.py --model llama-v41 --samples 500   # Quick run
  python scripts/evaluation/gsma_benchmark.py --model llama-v41 --samples 0     # All 10,000
  python scripts/evaluation/gsma_benchmark.py --model claude-sonnet             # Claude Sonnet 4.6
  python scripts/evaluation/gsma_benchmark.py --model claude-haiku              # Claude Haiku 4.5
"""

import json
import os
import re
import sys
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TELEQNA_PATH = PROJECT_ROOT / "data" / "benchmarks" / "gsma" / "teleqna_test.jsonl"
ENV_PATH = PROJECT_ROOT / ".env"

# Model name mapping — same convention as operational_benchmark.py
# Ollama models
OLLAMA_MODELS = {
    "llama-v41":    ("llama-telco-v41",             "Consilium v4.1 (Llama 3.1 8B, fine-tuned, 162 steps)"),
    "llama-v4":     ("llama-telco-v4",              "Llama 3.1 8B (v4, fine-tuned, 461 steps)"),
    "llama-v3":     ("llama-telco-v3",              "Llama 3.1 8B (v3, fine-tuned)"),
    "llama-v2":     ("llama-telco-v2",              "Llama 3.1 8B (v2, fine-tuned)"),
    "llama-base":   ("llama3.1:8b-instruct-q4_K_M", "Llama 3.1 8B Instruct (base, no fine-tuning)"),
    "phi4":         ("phi4:14b",                     "Microsoft Phi-4 14B (base, no fine-tuning)"),
    "7b":           ("qwen2.5:7b-instruct",          "Qwen 2.5 7B Instruct (base, no fine-tuning)"),
}

# Claude API models
CLAUDE_MODELS = {
    "claude-sonnet": ("claude-sonnet-4-6",  "Claude Sonnet 4.6 (Anthropic API)"),
    "claude-haiku":  ("claude-haiku-4-5-20251001", "Claude Haiku 4.5 (Anthropic API)"),
}

MODEL_MAP = {**OLLAMA_MODELS, **CLAUDE_MODELS}


@dataclass
class QuestionResult:
    id: int
    subject: str
    question: str
    correct_answer: int
    predicted_answer: int
    is_correct: bool
    elapsed: float


def load_teleqna(path: Path) -> list[dict]:
    """Load TeleQnA dataset from JSONL."""
    questions = []
    with open(path) as f:
        for line in f:
            questions.append(json.loads(line))
    return questions


def format_mcq_prompt(question: str, choices: list[str]) -> str:
    """Format a multiple-choice question for the model."""
    prompt = f"{question}\n\n"
    for i, choice in enumerate(choices):
        prompt += f"  {i}) {choice}\n"
    prompt += "\nRespond with ONLY the number of the correct answer (e.g., 0, 1, 2, 3, or 4). Do not explain."
    return prompt


def extract_answer(response: str, num_choices: int) -> int:
    """Extract answer index from model response."""
    response = response.strip()

    # Try to find a bare digit at the very start (most common for well-prompted models)
    match = re.match(r'^(\d)', response)
    if match:
        val = int(match.group(1))
        if 0 <= val < num_choices:
            return val

    # Look for "Answer: N" or "answer is N" patterns
    match = re.search(r'(?:answer|option|choice)[:\s]+(\d)', response, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        if 0 <= val < num_choices:
            return val

    # Try any single digit in first 50 chars
    match = re.search(r'\b(\d)\b', response[:50])
    if match:
        val = int(match.group(1))
        if 0 <= val < num_choices:
            return val

    # Try letter-based (A=0, B=1, ...)
    match = re.search(r'\b([A-E])\b', response[:50])
    if match:
        val = ord(match.group(1)) - ord('A')
        if 0 <= val < num_choices:
            return val

    return -1  # Could not parse


def load_api_key() -> str:
    """Load Anthropic API key from .env file."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return ""


def run_benchmark_claude(model_name: str, questions: list[dict]) -> list[QuestionResult]:
    """Run TeleQnA benchmark against a Claude model via Anthropic API."""
    import anthropic

    api_key = load_api_key()
    if not api_key:
        print("ERROR: No ANTHROPIC_API_KEY found in environment or .env file")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    system = (
        "You are a telecommunications expert. Answer multiple-choice questions "
        "by responding with ONLY the number of the correct answer. "
        "Do not provide explanations."
    )

    results = []
    for i, q in enumerate(questions):
        start = time.time()
        prompt = format_mcq_prompt(q["question"], q["choices"])

        try:
            resp = client.messages.create(
                model=model_name,
                max_tokens=20,
                temperature=0.1,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            answer_text = resp.content[0].text
        except Exception as e:
            answer_text = f"ERROR: {e}"
            # Rate limit handling — wait and retry once
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
                    answer_text = resp.content[0].text
                except Exception as e2:
                    answer_text = f"ERROR: {e2}"

        elapsed = time.time() - start
        predicted = extract_answer(answer_text, len(q["choices"]))
        correct_answer = q["answer"]
        is_correct = (predicted == correct_answer)

        results.append(QuestionResult(
            id=i,
            subject=q.get("subject", "unknown"),
            question=q["question"],
            correct_answer=correct_answer,
            predicted_answer=predicted,
            is_correct=is_correct,
            elapsed=elapsed,
        ))

        correct_so_far = sum(1 for r in results if r.is_correct)
        if (i + 1) % 25 == 0 or (i + 1) == len(questions):
            pct = 100 * correct_so_far / len(results)
            print(f"  [{i+1}/{len(questions)}] accuracy: {correct_so_far}/{len(results)} ({pct:.1f}%) — {q['subject'][:20]} — {elapsed:.1f}s")

    return results


def run_benchmark_ollama(model_name: str, questions: list[dict]) -> list[QuestionResult]:
    """Run TeleQnA benchmark against an Ollama model."""
    import httpx

    system = (
        "You are a telecommunications expert. Answer multiple-choice questions "
        "by responding with ONLY the number of the correct answer. "
        "Do not provide explanations."
    )

    results = []
    for i, q in enumerate(questions):
        start = time.time()
        prompt = format_mcq_prompt(q["question"], q["choices"])

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
            answer_text = resp.json().get("message", {}).get("content", "")
        except Exception as e:
            answer_text = f"ERROR: {e}"

        elapsed = time.time() - start
        predicted = extract_answer(answer_text, len(q["choices"]))
        correct_answer = q["answer"]
        is_correct = (predicted == correct_answer)

        results.append(QuestionResult(
            id=i,
            subject=q.get("subject", "unknown"),
            question=q["question"],
            correct_answer=correct_answer,
            predicted_answer=predicted,
            is_correct=is_correct,
            elapsed=elapsed,
        ))

        # Progress output every 25 questions
        correct_so_far = sum(1 for r in results if r.is_correct)
        if (i + 1) % 25 == 0 or (i + 1) == len(questions):
            pct = 100 * correct_so_far / len(results)
            print(f"  [{i+1}/{len(questions)}] accuracy: {correct_so_far}/{len(results)} ({pct:.1f}%) — {q['subject'][:20]} — {elapsed:.1f}s")

    return results


def print_summary(results: list[QuestionResult], model_label: str) -> dict:
    """Print and return benchmark summary."""
    print(f"\n{'='*70}")
    print(f"GSMA TeleQnA BENCHMARK RESULTS: {model_label}")
    print(f"{'='*70}")

    total = len(results)
    correct = sum(1 for r in results if r.is_correct)
    unparsed = sum(1 for r in results if r.predicted_answer == -1)

    print(f"\nOverall: {correct}/{total} ({100*correct/total:.1f}%)")
    if unparsed > 0:
        print(f"Unparsed responses: {unparsed} (counted as wrong)")

    # By subject
    subjects = {}
    for r in results:
        if r.subject not in subjects:
            subjects[r.subject] = {"correct": 0, "total": 0, "elapsed": 0}
        subjects[r.subject]["total"] += 1
        subjects[r.subject]["elapsed"] += r.elapsed
        if r.is_correct:
            subjects[r.subject]["correct"] += 1

    print(f"\n{'Subject':<30} {'Score':>10} {'Count':>6} {'Accuracy':>10} {'Avg Time':>10}")
    print(f"{'-'*66}")
    for subj in sorted(subjects.keys()):
        s = subjects[subj]
        acc = s["correct"] / s["total"] if s["total"] > 0 else 0
        avg_t = s["elapsed"] / s["total"] if s["total"] > 0 else 0
        print(f"{subj:<30} {s['correct']:>4}/{s['total']:<5} {s['total']:>4}   {acc:>8.1%}   {avg_t:>8.1f}s")

    # Worst subjects
    print(f"\n--- Hardest Subjects ---")
    sorted_subj = sorted(subjects.items(), key=lambda x: x[1]["correct"]/max(x[1]["total"],1))
    for subj, s in sorted_subj[:3]:
        acc = s["correct"] / s["total"] if s["total"] > 0 else 0
        print(f"  {subj}: {acc:.1%} ({s['correct']}/{s['total']})")

    summary = {
        "benchmark": "GSMA TeleQnA",
        "benchmark_source": "huggingface.co/datasets/netop/TeleQnA",
        "model": model_label,
        "total_questions": total,
        "overall_accuracy": correct / total,
        "correct": correct,
        "unparsed": unparsed,
        "by_subject": {
            subj: {
                "accuracy": s["correct"] / s["total"],
                "correct": s["correct"],
                "total": s["total"],
            }
            for subj, s in subjects.items()
        },
        "results": [asdict(r) for r in results],
    }

    return summary


def main():
    parser = argparse.ArgumentParser(description="GSMA TeleQnA Benchmark")
    parser.add_argument("--model", choices=list(MODEL_MAP.keys()), required=True,
                        help="Model to test")
    parser.add_argument("--samples", type=int, default=500,
                        help="Number of questions to evaluate (0=all 10,000)")
    parser.add_argument("--subject", type=str, default=None,
                        help="Filter to a specific subject (e.g., 'Lexicon', 'Standards specifications')")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for sampling (ensures reproducible subset)")
    args = parser.parse_args()

    # Load dataset
    if not TELEQNA_PATH.exists():
        print(f"ERROR: TeleQnA dataset not found at {TELEQNA_PATH}")
        print(f"Download it first: python -c \"from datasets import load_dataset; ds = load_dataset('netop/TeleQnA'); ds['test'].to_json('{TELEQNA_PATH}')\"")
        sys.exit(1)

    questions = load_teleqna(TELEQNA_PATH)
    print(f"Loaded {len(questions)} TeleQnA questions")

    # Filter by subject if specified
    if args.subject:
        questions = [q for q in questions if q.get("subject", "").lower() == args.subject.lower()]
        print(f"Filtered to subject '{args.subject}': {len(questions)} questions")

    # Sample if needed
    if args.samples > 0 and args.samples < len(questions):
        import random
        random.seed(args.seed)
        questions = random.sample(questions, args.samples)
        print(f"Sampled {args.samples} questions (seed={args.seed})")

    model_id, label = MODEL_MAP[args.model]
    is_claude = args.model in CLAUDE_MODELS

    print(f"\n{'='*70}")
    print(f"GSMA TeleQnA Benchmark — {len(questions)} questions")
    print(f"Model: {label}")
    print(f"Backend: {'Anthropic API' if is_claude else 'Ollama'} ({model_id})")
    print(f"{'='*70}\n")

    # Run benchmark
    if is_claude:
        results = run_benchmark_claude(model_id, questions)
    else:
        results = run_benchmark_ollama(model_id, questions)
    summary = print_summary(results, label)

    # Save results
    output_path = PROJECT_ROOT / "models" / f"gsma_teleqna_{args.model}.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # Also save a comparison-friendly one-liner
    print(f"\n--- Quick comparison line ---")
    print(f"{args.model}: {summary['overall_accuracy']:.1%} ({summary['correct']}/{summary['total_questions']})")


if __name__ == "__main__":
    main()
