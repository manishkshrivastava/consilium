"""
GSMA TeleQnA Generation Benchmark — Free-text evaluation (no MCQ options).

Unlike the standard MCQ benchmark (gsma_benchmark.py), this strips the answer
choices and asks the model to answer freely. This tests GENERATION (produce the
right answer) rather than RECOGNITION (pick from options).

Scoring: Extract key concepts from the correct answer choice and its explanation,
then check how many appear in the model's free-text response.

This is a more realistic evaluation of how the model performs in actual agent
usage, where no options are provided.

Usage:
  python scripts/evaluation/gsma_generation_benchmark.py --model llama-v41
  python scripts/evaluation/gsma_generation_benchmark.py --model llama-base
  python scripts/evaluation/gsma_generation_benchmark.py --model llama-v41 --samples 200
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

OLLAMA_MODELS = {
    "llama-v41":  ("llama-telco-v41",              "Consilium v4.1 (Llama 3.1 8B, fine-tuned)"),
    "llama-v4":   ("llama-telco-v4",               "Llama 3.1 8B (v4, fine-tuned)"),
    "llama-v2":   ("llama-telco-v2",               "Llama 3.1 8B (v2, fine-tuned)"),
    "llama-base": ("llama3.1:8b-instruct-q4_K_M",  "Llama 3.1 8B Instruct (base, no fine-tuning)"),
    "phi4":       ("phi4:14b",                      "Microsoft Phi-4 14B (base, no fine-tuning)"),
}


@dataclass
class GenerationResult:
    id: int
    subject: str
    question: str
    correct_answer_text: str
    explanation: str
    key_concepts: list
    model_answer: str
    concepts_found: list
    concepts_missing: list
    score: float  # 0.0 to 1.0
    elapsed: float


def load_teleqna(path: Path) -> list[dict]:
    """Load TeleQnA dataset from JSONL."""
    questions = []
    with open(path) as f:
        for line in f:
            questions.append(json.loads(line))
    return questions


def extract_key_concepts(correct_choice: str, explanation: str) -> list[str]:
    """Extract key concepts from the correct answer and its explanation.

    Strategy: split into meaningful terms/phrases, filter out stopwords
    and very short/generic words. Keep domain-specific terms.
    """
    # Combine correct answer and explanation
    text = f"{correct_choice} {explanation}".lower()

    # Remove common stopwords and filler
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "ought",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "each",
        "every", "both", "few", "more", "most", "other", "some", "such", "no",
        "nor", "not", "only", "own", "same", "so", "than", "too", "very",
        "just", "because", "but", "and", "or", "if", "while", "that", "this",
        "these", "those", "it", "its", "which", "what", "who", "whom",
        "used", "using", "uses", "also", "however", "therefore", "thus",
        "based", "provides", "allows", "enables", "refers", "involves",
        "known", "called", "defined", "described", "according", "specific",
        "given", "ensure", "ensure", "order", "purpose", "following",
    }

    # Extract words (keep alphanumeric + hyphens)
    words = re.findall(r'[a-z0-9][\w\-]*[a-z0-9]|[a-z0-9]', text)

    # Filter: keep words that are domain-meaningful
    concepts = []
    seen = set()
    for word in words:
        if word in stopwords or len(word) < 3:
            continue
        if word in seen:
            continue
        seen.add(word)
        concepts.append(word)

    # Also extract multi-word terms (2-grams from the correct choice)
    choice_words = re.findall(r'[a-z0-9][\w\-]*[a-z0-9]|[a-z0-9]', correct_choice.lower())
    for i in range(len(choice_words) - 1):
        bigram = f"{choice_words[i]} {choice_words[i+1]}"
        if choice_words[i] not in stopwords and choice_words[i+1] not in stopwords:
            if bigram not in seen and len(choice_words[i]) >= 3 and len(choice_words[i+1]) >= 3:
                seen.add(bigram)
                concepts.append(bigram)

    # Cap at 15 concepts to avoid over-penalizing
    return concepts[:15]


def score_generation(model_answer: str, key_concepts: list[str]) -> tuple[float, list, list]:
    """Score a free-text answer against key concepts.

    Returns (score, found_concepts, missing_concepts).
    """
    answer_lower = model_answer.lower()

    found = []
    missing = []
    for concept in key_concepts:
        if concept in answer_lower:
            found.append(concept)
        else:
            missing.append(concept)

    if not key_concepts:
        return 0.0, found, missing

    score = len(found) / len(key_concepts)
    return score, found, missing


def run_benchmark_ollama(model_name: str, questions: list[dict]) -> list[GenerationResult]:
    """Run generation benchmark against an Ollama model."""
    import httpx

    system = (
        "You are a telecommunications expert. Answer the question accurately and concisely. "
        "Provide specific technical details, protocol names, and standard references where relevant."
    )

    results = []
    for i, q in enumerate(questions):
        start = time.time()

        # No options — just the question
        prompt = q["question"]

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
                    "options": {"num_predict": 300, "temperature": 0.2},
                },
                timeout=120,
                verify=False,
            )
            answer_text = resp.json().get("message", {}).get("content", "")
        except Exception as e:
            answer_text = f"ERROR: {e}"

        elapsed = time.time() - start

        # Get correct answer text and explanation
        correct_idx = q["answer"]
        correct_text = q["choices"][correct_idx] if correct_idx < len(q["choices"]) else ""
        explanation = q.get("explaination", q.get("explanation", ""))

        # Extract key concepts and score
        concepts = extract_key_concepts(correct_text, explanation)
        score, found, missing = score_generation(answer_text, concepts)

        results.append(GenerationResult(
            id=i,
            subject=q.get("subject", "unknown"),
            question=q["question"],
            correct_answer_text=correct_text,
            explanation=explanation,
            key_concepts=concepts,
            model_answer=answer_text[:500],
            concepts_found=found,
            concepts_missing=missing,
            score=score,
            elapsed=elapsed,
        ))

        # Progress
        if (i + 1) % 25 == 0 or (i + 1) == len(questions):
            avg_score = sum(r.score for r in results) / len(results)
            print(f"  [{i+1}/{len(questions)}] avg score: {avg_score:.1%} — {q['subject'][:20]} — {score:.1%} ({len(found)}/{len(concepts)}) — {elapsed:.1f}s")

    return results


def print_summary(results: list[GenerationResult], model_label: str) -> dict:
    """Print and return benchmark summary."""
    print(f"\n{'='*70}")
    print(f"GSMA TeleQnA GENERATION BENCHMARK: {model_label}")
    print(f"{'='*70}")

    total = len(results)
    avg_score = sum(r.score for r in results) / total
    avg_concepts = sum(len(r.key_concepts) for r in results) / total
    avg_found = sum(len(r.concepts_found) for r in results) / total

    print(f"\nOverall: {avg_score:.1%} concept coverage ({avg_found:.1f}/{avg_concepts:.1f} concepts per question)")

    # By subject
    subjects = {}
    for r in results:
        if r.subject not in subjects:
            subjects[r.subject] = []
        subjects[r.subject].append(r)

    print(f"\n{'Subject':<30} {'Avg Score':>10} {'Count':>6} {'Avg Found':>10} {'Avg Time':>10}")
    print(f"{'-'*66}")
    for subj in sorted(subjects.keys()):
        rs = subjects[subj]
        avg = sum(r.score for r in rs) / len(rs)
        avg_f = sum(len(r.concepts_found) for r in rs) / len(rs)
        avg_t = sum(r.elapsed for r in rs) / len(rs)
        print(f"{subj:<30} {avg:>8.1%}   {len(rs):>4}   {avg_f:>8.1f}   {avg_t:>8.1f}s")

    # Worst 10 questions
    print(f"\n--- Worst 10 Questions ---")
    worst = sorted(results, key=lambda r: r.score)[:10]
    for r in worst:
        print(f"  [{r.id}] {r.score:.1%} ({len(r.concepts_found)}/{len(r.key_concepts)}) — {r.question[:65]}")
        if r.concepts_missing[:3]:
            print(f"         missing: {', '.join(r.concepts_missing[:3])}")

    # Best 5 questions
    print(f"\n--- Best 5 Questions ---")
    best = sorted(results, key=lambda r: r.score, reverse=True)[:5]
    for r in best:
        print(f"  [{r.id}] {r.score:.1%} ({len(r.concepts_found)}/{len(r.key_concepts)}) — {r.question[:65]}")

    summary = {
        "benchmark": "GSMA TeleQnA (Generation)",
        "benchmark_source": "huggingface.co/datasets/netop/TeleQnA",
        "evaluation_method": "Free-text generation, scored by key concept coverage from correct answer + explanation",
        "model": model_label,
        "total_questions": total,
        "overall_score": avg_score,
        "avg_concepts_per_question": avg_concepts,
        "avg_concepts_found": avg_found,
        "by_subject": {
            subj: {
                "score": sum(r.score for r in rs) / len(rs),
                "count": len(rs),
                "avg_concepts_found": sum(len(r.concepts_found) for r in rs) / len(rs),
            }
            for subj, rs in subjects.items()
        },
        "results": [asdict(r) for r in results],
    }

    return summary


def main():
    parser = argparse.ArgumentParser(description="GSMA TeleQnA Generation Benchmark")
    parser.add_argument("--model", choices=list(OLLAMA_MODELS.keys()), required=True,
                        help="Model to test")
    parser.add_argument("--samples", type=int, default=200,
                        help="Number of questions (0=all, default=200)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for sampling")
    args = parser.parse_args()

    if not TELEQNA_PATH.exists():
        print(f"ERROR: TeleQnA dataset not found at {TELEQNA_PATH}")
        sys.exit(1)

    questions = load_teleqna(TELEQNA_PATH)
    print(f"Loaded {len(questions)} TeleQnA questions")

    if args.samples > 0 and args.samples < len(questions):
        import random
        random.seed(args.seed)
        questions = random.sample(questions, args.samples)
        print(f"Sampled {args.samples} questions (seed={args.seed})")

    model_id, label = OLLAMA_MODELS[args.model]

    print(f"\n{'='*70}")
    print(f"GSMA TeleQnA GENERATION Benchmark — {len(questions)} questions")
    print(f"Model: {label}")
    print(f"Method: Free-text generation (no MCQ options)")
    print(f"Scoring: Key concept coverage from correct answer + explanation")
    print(f"{'='*70}\n")

    results = run_benchmark_ollama(model_id, questions)
    summary = print_summary(results, label)

    output_path = PROJECT_ROOT / "models" / f"gsma_generation_{args.model}.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # Comparison line
    print(f"\n--- Quick comparison ---")
    print(f"{args.model}: {summary['overall_score']:.1%} concept coverage (generation)")


if __name__ == "__main__":
    main()
