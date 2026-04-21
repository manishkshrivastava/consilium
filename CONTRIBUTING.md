# Contributing to Consilium

Thanks for your interest in contributing. Consilium is a telecom-domain SLM + multi-agent system, and contributions from both telecom practitioners and ML engineers are welcome.

## How to Contribute

### Report bugs or suggest features
Open an [Issue](https://github.com/manishkshrivastava/consilium/issues). Check existing issues first to avoid duplicates.

### Ask questions or discuss ideas
Use [Discussions](https://github.com/manishkshrivastava/consilium/discussions) for open-ended conversations, architecture ideas, or questions about the approach.

### Submit code
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run the benchmark to check for regressions: `python scripts/evaluation/operational_benchmark.py --model llama-telco-v41`
5. Commit and push to your fork
6. Open a Pull Request with a clear description of what changed and why

### Good first issues
Look for issues labelled [`good first issue`](https://github.com/manishkshrivastava/consilium/labels/good%20first%20issue) — these are scoped, well-defined tasks with guidance on which files to modify.

## What's Most Useful Right Now

- **RAG improvements** — reranker integration, conditional triggering, better chunking
- **Benchmark contributions** — run Consilium against new eval sets, test on different hardware
- **Model comparisons** — fine-tune or benchmark other base models (Phi-4, Qwen, Mistral)
- **Tool integrations** — connect to real or simulated NMS data sources (O-RAN, ONAP, open-source simulators)
- **Training data** — if you have telecom domain expertise, help review or generate training examples

## Guidelines

- Keep PRs focused — one feature or fix per PR
- Include benchmark results if your change affects model output or agent behavior
- No proprietary data, vendor-specific credentials, or API keys in commits
- Use environment variables for any secrets (`os.environ.get(...)`)

## Setup for Development

```bash
git clone https://github.com/manishkshrivastava/consilium.git
cd consilium
pip install -r requirements.txt

# You need Ollama running with the model loaded
ollama pull llama3.1:8b-instruct-q4_K_M  # base model for comparison
```

## Questions?

Open a [Discussion](https://github.com/manishkshrivastava/consilium/discussions) or reach out via Issues.
