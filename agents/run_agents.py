#!/usr/bin/env python3
"""
Telco SLM Agentic CLI (Phase 2)
================================
Interactive command-line interface for the TelcoGPT multi-agent system.
Now with conversation memory and multi-agent chaining.

Usage:
    python run_agents.py              # full mode (MLX + Ollama + RAG)
    python run_agents.py --skip-mlx   # Ollama-only mode (no local SLM)
    python run_agents.py --skip-rag   # skip RAG retriever

Author : Manish Kumar Shrivastava
Created: 2026-03-19
Updated: 2026-03-19 (Phase 2)
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.telco_agents import AgentOrchestrator

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


def print_banner():
    print(f"""
{CYAN}{BOLD}{'=' * 60}
   CONSILIUM  -  Domain-trained. Agent-driven. Self-evolving.
   Powered by Consilium v4.1 (Llama 3.1 8B)
{'=' * 60}{RESET}
{DIM}Commands:
  type your query and press Enter
  /quit or /exit  — leave
  /agents         — show agent info
  /clear          — clear conversation memory
  /memory         — show conversation history
  /chain          — test multi-agent chaining{RESET}
""")


def print_agent_info():
    print(f"""
{YELLOW}{BOLD}Registered Agents:{RESET}
  {GREEN}SupervisorAgent{RESET}  - Qwen 7B via Ollama    - classifies + plans agent execution
  {GREEN}IncidentAgent{RESET}    - Fine-tuned SLM (MLX)   - alarm diagnosis
  {GREEN}ConfigAgent{RESET}      - Fine-tuned SLM (MLX)   - YAML config generation
  {GREEN}KnowledgeAgent{RESET}   - RAG + Qwen 7B          - 3GPP grounded answers
  {GREEN}GenericAgent{RESET}     - Qwen 7B via Ollama      - general telecom chat

{YELLOW}{BOLD}Phase 2 Features:{RESET}
  {MAGENTA}Conversation Memory{RESET} — follow-up questions remember prior context
  {MAGENTA}Multi-Agent Chaining{RESET} — complex queries trigger multiple agents in sequence
  {MAGENTA}Follow-up Detection{RESET} — "can you elaborate?" routes to the same agent with context
""")


def main():
    parser = argparse.ArgumentParser(description="Consilium Agentic CLI (Phase 2)")
    parser.add_argument("--skip-mlx", action="store_true",
                       help="Skip loading the local MLX fine-tuned model")
    parser.add_argument("--skip-rag", action="store_true",
                       help="Skip loading the ChromaDB RAG retriever")
    args = parser.parse_args()

    print_banner()

    print(f"{DIM}Initialising agents — this may take a moment ...{RESET}\n")
    try:
        orchestrator = AgentOrchestrator(
            skip_mlx=args.skip_mlx, skip_rag=args.skip_rag
        )
    except Exception as exc:
        print(f"{RED}Failed to initialise orchestrator: {exc}{RESET}")
        sys.exit(1)

    print(f"{GREEN}Ready! Ask anything about telecom networks.{RESET}")
    print(f"{DIM}Conversation memory is active — follow-ups will have context.{RESET}\n")

    while True:
        try:
            query = input(f"{BOLD}You > {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Goodbye.{RESET}")
            break

        if not query:
            continue

        # Meta commands
        if query.lower() in ("/quit", "/exit", "quit", "exit"):
            print(f"{DIM}Goodbye.{RESET}")
            break

        if query.lower() == "/agents":
            print_agent_info()
            continue

        if query.lower() == "/clear":
            orchestrator.clear_memory()
            print(f"{MAGENTA}Conversation memory cleared.{RESET}\n")
            continue

        if query.lower() == "/memory":
            mem = orchestrator.memory
            if not mem.history:
                print(f"{DIM}No conversation history yet.{RESET}\n")
            else:
                print(f"\n{MAGENTA}{BOLD}Conversation History ({len(mem.history)} entries):{RESET}")
                for i, entry in enumerate(mem.history):
                    role = entry["role"].upper()
                    content = entry["content"][:100]
                    agent = entry.get("agent", "")
                    agent_str = f" [{agent}]" if agent else ""
                    print(f"  {DIM}{i+1}. [{role}]{agent_str}: {content}...{RESET}")
                print()
            continue

        if query.lower() == "/chain":
            print(f"{MAGENTA}Try these multi-agent queries:{RESET}")
            print(f'  "Diagnose high CPU on ENB-5432 and suggest config changes to prevent it"')
            print(f'  "What does 3GPP say about HARQ and generate a DRX config for low latency"')
            print(f'  "S1 failure on ENB-8000 — diagnose and explain the SCTP protocol involved"')
            print()
            continue

        # Run the query
        print(f"\n{DIM}Classifying query ...{RESET}")
        response = orchestrator.run(query)

        # Display results
        print(f"\n{YELLOW}Category : {response.category}{RESET}")
        print(f"{YELLOW}Agent    : {response.agent}{RESET}")
        print(f"{YELLOW}Time     : {response.elapsed_seconds}s{RESET}")

        # Show plan if multi-agent
        plan = response.metadata.get("plan", [])
        if len(plan) > 1:
            print(f"{MAGENTA}Chain    : {' → '.join(plan)}{RESET}")

        # Show if follow-up was detected
        if response.metadata.get("is_followup"):
            print(f"{MAGENTA}(Follow-up detected — using previous context){RESET}")

        # Show context usage
        if response.metadata.get("context_used"):
            print(f"{DIM}(Conversation context was provided to Supervisor){RESET}")

        if response.sources:
            sources_str = ", ".join(set(str(s) for s in response.sources[:5]))
            print(f"{YELLOW}Sources  : {sources_str}{RESET}")

        # Memory indicator
        mem_count = len(orchestrator.memory)
        print(f"{DIM}Memory   : {mem_count} entries{RESET}")

        print(f"\n{GREEN}{BOLD}Consilium >{RESET} {response.answer}\n")
        print(f"{DIM}{'- ' * 30}{RESET}\n")


if __name__ == "__main__":
    main()
