"""
Test the fine-tuned Telco SLM with sample queries.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_PATH = PROJECT_ROOT / "models" / "telco-slm-v1-mlx" / "adapter"

TEST_PROMPTS = [
    "I'm seeing high CPU utilization on eNodeB ENB-5432. CPU is at 95%. What could be causing this?",
    "What is 5QI and how does it relate to QoS in 5G networks?",
    "Convert this intent to network configuration: Create a network slice for autonomous vehicles requiring ultra-low latency",
    "Explain the S1 interface in LTE networks.",
    "We have packet loss of 5% on the backhaul link to site ENB-1234. What are the troubleshooting steps?",
]


def main():
    from mlx_lm import load, generate

    print("=" * 60)
    print("TELCO SLM - Model Testing")
    print("=" * 60)

    if not ADAPTER_PATH.exists():
        print(f"Adapter not found at {ADAPTER_PATH}")
        print("Run train_mlx.py first!")
        sys.exit(1)

    print(f"\nLoading model: {MODEL}")
    print(f"Adapter: {ADAPTER_PATH}")

    model, tokenizer = load(MODEL, adapter_path=str(ADAPTER_PATH))

    system_prompt = (
        "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
        "You have deep knowledge of 3GPP standards, 5G/LTE network operations, "
        "RAN optimization, core network, transport, and IMS/VoLTE."
    )

    for i, prompt in enumerate(TEST_PROMPTS):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: {prompt[:80]}...")
        print("-" * 60)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        response = generate(
            model, tokenizer, prompt=text, max_tokens=512, verbose=False
        )
        print(response)

    print(f"\n{'='*60}")
    print("Testing complete!")

    # Interactive mode
    print("\nEntering interactive mode (type 'quit' to exit):")
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        response = generate(
            model, tokenizer, prompt=text, max_tokens=512, verbose=False
        )
        print(f"\nTelcoGPT: {response}")


if __name__ == "__main__":
    main()
