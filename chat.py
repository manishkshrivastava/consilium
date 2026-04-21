#!/usr/bin/env python3
"""
Consilium v3 — Interactive Chat
Run: python chat.py
"""

from mlx_lm import load, generate

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER = "models/telco-slm-v3-mlx/adapter"

SYSTEM_PROMPT = (
    "You are Consilium, an intelligent telecom network assistant specialized in telecommunications. "
    "You have deep knowledge of 3GPP standards (Release 8-19), 5G/LTE network operations, "
    "RAN optimization, core network architecture, transport networking, IMS/VoLTE, "
    "and network security. You assist network engineers with alarm diagnostics, "
    "root cause analysis, troubleshooting steps, network configuration generation, "
    "KPI analysis, and 3GPP standards interpretation."
)

print("Loading Consilium v3...")
model, tokenizer = load(MODEL, adapter_path=ADAPTER)
print("Ready! Type 'quit' to exit.\n")

while True:
    try:
        user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nBye!")
        break

    if user_input.lower() in ("quit", "exit", "q"):
        print("Bye!")
        break

    if not user_input:
        continue

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    print("\nConsilium:", end="", flush=True)
    response = generate(model, tokenizer, prompt=text, max_tokens=500, verbose=False)
    print(response)
    print()
