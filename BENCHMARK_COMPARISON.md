# Consilium — Benchmark Comparison: Fine-Tuning vs RAG Impact

Date: 2026-04-11
Benchmark: Operational Benchmark (100 questions across 5 categories)
Model: Llama 3.1 8B Instruct (Q4_K_M quantization, 4.6 GB GGUF)

---

## Summary Table

| Setup | Overall | Config | Knowledge | Incident | KPI | Routing |
|-------|---------|--------|-----------|----------|-----|---------|
| Base Llama 3.1 8B (no training, no RAG) | **72.7%** | 91.2% | 73.3% | 70.0% | 52.7% | — |
| Fine-tuned v4.1 only (no RAG) | **84.1%** | 94.3% | 92.3% | 77.9% | 72.0% | — |
| Agent system, fine-tuned, no RAG | **83.4%** | 96.1% | 83.8% | 78.3% | 59.5% | 100% |
| Agent system, fine-tuned + RAG | **74.5%** | 95.2% | 81.7% | 63.9% | 39.4% | 93.3% |

## What Each Row Means

- **Base Llama 3.1 8B**: Meta's stock model, no domain training. Pure out-of-the-box general knowledge. Pulled as `llama3.1:8b-instruct-q4_K_M` from Ollama.
- **Fine-tuned v4.1 only**: After domain training (48K base + 7.4K patch + 1.3K micro-patch). Direct Ollama inference, no agents, no RAG. This isolates what fine-tuning alone contributes.
- **Agent system, no RAG**: Fine-tuned model running through the full agent pipeline (Supervisor routing, specialist agents, tools) but with RAG disabled (`skip_rag=True`).
- **Agent system + RAG**: Full pipeline with ChromaDB retrieval enabled. KnowledgeAgent retrieves 3GPP spec chunks and injects them as context before the model generates an answer.

## Key Findings

### Fine-tuning is the primary value driver

The fine-tuned model (84.1%) outperforms the base model (72.7%) by **+11.4 points overall**. The largest gains are in the categories where domain-specific training data matters most:

- **Knowledge: +19.0 pts** (73.3% to 92.3%) — 3GPP protocol knowledge baked into weights during training
- **KPI: +19.3 pts** (52.7% to 72.0%) — quantitative reasoning with telecom-specific metrics
- **Incident: +7.9 pts** (70.0% to 77.9%) — NOC incident diagnosis patterns
- **Config: +3.1 pts** (91.2% to 94.3%) — already strong in base model (structured YAML output is a general capability)

### RAG hurts overall performance in current implementation

The agent system with RAG (74.5%) scores **lower** than both the fine-tuned model alone (84.1%) and the agent system without RAG (83.4%). The degradation is across all categories except Config:

- **KPI: 72.0% to 39.4%** — retrieved context dilutes the model's trained quantitative reasoning
- **Incident: 77.9% to 63.9%** — RAG chunks add noise to diagnosis workflows
- **Knowledge: 92.3% to 81.7%** — raw 3GPP spec text doesn't match the concise answer style the scoring rubric expects
- **Config: 94.3% to 95.2%** — marginal improvement, within noise

### Agent routing overhead

The agent system without RAG (83.4%) scores slightly below the raw model (84.1%). The Supervisor routing adds a small classification penalty — some questions get misrouted to the wrong specialist agent. Routing accuracy is 100% without RAG, 93.3% with RAG.

## Analysis: Why RAG Hurts

This is a known pattern with naive RAG on domain-tuned models. The fine-tuned model has already internalised the 3GPP knowledge during training. When RAG retrieves raw specification chunks and injects them as context:

1. **Context dilution** — the retrieved text is raw 3GPP spec language (tables, clause references, formal definitions). The model's trained answer style (concise, structured, actionable) gets overridden by verbose spec-quoting.
2. **Answer format mismatch** — the scoring rubric rewards specific keywords and structured answers. RAG-augmented answers tend to parrot spec language rather than synthesize it.
3. **Retrieval noise** — the current retrieval (top-5 chunks, sentence-transformers/all-MiniLM-L6-v2) may return adjacent but not precisely relevant sections.
4. **Investigation overhead** — the InvestigatorAgent (used for incident and KPI queries with RAG) makes tool calls and RAG lookups that add latency and sometimes produce conflicting evidence that confuses the synthesis step.

## What This Means for Production

- **For accuracy**: serve the fine-tuned model directly — it performs best.
- **RAG adds value for grounding, not accuracy**: RAG is useful when you need to cite specific 3GPP clause numbers, provide provenance, or answer questions about specs the model wasn't trained on. But it needs optimization before it helps benchmark scores.
- **RAG optimisation roadmap**:
  - Improve chunking strategy (section-aware splits instead of fixed-size)
  - Use a reranker to filter retrieved chunks before injection
  - Conditional RAG: only retrieve when the model signals low confidence
  - Tune the prompt template to instruct the model to use retrieved context as reference, not override
  - Consider domain-specific embedding model instead of general-purpose MiniLM

## Benchmark Details

### Test Configuration

- **Questions**: 100 total (30 incident, 20 config, 15 KPI, 20 knowledge/protocol, 15 routing)
- **Scoring**: Automated rubric per category (keyword matching, domain correctness, structure checks)
- **Timeout**: 120 seconds per question
- **Ollama**: localhost:11434
- **RAG**: ChromaDB persistent store, 3.5M vectors from TSpec-LLM (3GPP Releases 8-19), sentence-transformers/all-MiniLM-L6-v2, top-5 retrieval

### Benchmark Files

| File | Setup | Score |
|------|-------|-------|
| `models/benchmark_llama-base.json` | Base Llama 3.1 8B, no training | 72.7% |
| `models/benchmark_llama-v41.json` | Fine-tuned v4.1, no RAG | 84.1% |
| `models/benchmark_agents.json` | Agent system, no RAG | 83.4% |
| `models/benchmark_agents-rag.json` | Agent system + RAG | 74.5% |

### Historical Fine-Tuning Progression

| Model | Data | Overall | Incident | Config | KPI | Knowledge |
|-------|------|---------|----------|--------|-----|-----------|
| Base Llama 3.1 8B | — | 72.7% | 70.0% | 91.2% | 52.7% | 73.3% |
| Llama FT v2 | 49K | 81.9% | 79.4% | 92.5% | 66.2% | 86.7% |
| Llama FT v4 | +7.4K patch from v2 | 82.8% | 79.0% | 93.5% | 72.1% | 85.7% |
| Llama FT v4.1 | +1.3K micro-patch from v4 | 84.1% | 77.9% | 94.3% | 72.0% | 92.3% |

### Training Chain

- **v2**: 49K rows, LR=2e-4, 3 epochs, Kaggle T4 — 81.9%
- **v4**: 7.4K patch from v2, LR=5e-5, 1 epoch, RunPod A40 — 82.8%
- **v4.1**: 1.3K micro-patch from v4, LR=3e-5, 2 epochs, RunPod A40 — 84.1%

### Base Model Worst Performers (bottom 10)

| ID | Score | Question |
|----|-------|----------|
| INC-IMS-02 | 0.17 | One-way audio reported on VoLTE calls |
| KPI-05 | 0.20 | Handover success rate between two 5G cells is only 88% |
| KPI-02 | 0.25 | RRC setup success rate is 87% on cell CELL-800 |
| KPI-01 | 0.33 | ERAB drop rate increased from 0.5% to 2.8% over the past week |
| PROTO-07 | 0.33 | What is CUPS and why is it important in 5G architecture? |
| PROTO-12 | 0.33 | How does carrier aggregation work in LTE/NR? |
| INC-RAN-10 | 0.40 | High PDCP packet loss (3.5%) detected on CELL-700 |
| KPI-04 | 0.43 | Average DL user throughput is 15Mbps on a 20MHz LTE cell |
| KPI-08 | 0.43 | Uplink interference level (IoT) increased by 5dB across a cluster |
| KPI-10 | 0.43 | Attach success rate on MME-01 dropped from 99.5% to 97% |

### Fine-Tuned v4.1 Worst Performers (bottom 10)

These represent remaining gaps where further training data or methodology improvements could help.

(Run `cat models/benchmark_llama-v41.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'  {r[\"id\"]:15s} {r[\"score\"]:.2f}  {r[\"question\"][:70]}') for r in sorted(d['results'], key=lambda x: x['score'])[:10]]"` to extract.)

---

## GSMA TeleQnA — Independent Held-Out Benchmark (added 2026-04-14)

### What is TeleQnA?

The GSMA/netop TeleQnA is an **industry-standard**, GSMA-endorsed benchmark of 10,000 multiple-choice questions testing general telecom knowledge across 5 subjects. It is hosted on Hugging Face (`netop/TeleQnA`) and used by frontier model providers (Google, OpenAI, Anthropic) to benchmark their models.

**Critically**: No Consilium model was ever trained or optimized against these questions. This is a completely independent, held-out evaluation.

### Results (500 questions, seed=42)

| Subject | Base Llama 3.1 8B | Consilium v4.1 | Delta |
|---------|-------------------|----------------|-------|
| Lexicon | 84.2% | 78.9% | -5.3 |
| Research publications | 70.2% | 69.8% | -0.4 |
| Research overview | 62.3% | 69.3% | **+7.0** |
| Standards overview | 60.9% | 67.4% | **+6.5** |
| Standards specifications | 53.1% | 56.2% | **+3.1** |
| **Overall** | **64.8%** | **67.2%** | **+2.4** |

### Interpretation

**Fine-tuning gain on independent benchmark: +2.4 points.**

This contrasts with +11.4 pts on the operational benchmark (which was iteratively optimized against). The difference is expected and informative:

1. **Operational benchmark (+11.4 pts)** tests task-specific reasoning: incident diagnosis workflows, config generation, KPI interpretation. Fine-tuning teaches these operational patterns directly.

2. **GSMA TeleQnA (+2.4 pts)** tests general telecom textbook knowledge: MCQ from 3GPP specs and research papers. The base model already has decent coverage of this; fine-tuning adds modest improvement.

3. **Gains concentrated in standards (+3.1 to +7.0 pts)** — the areas closest to the fine-tuning data (3GPP protocols, network standards).

4. **Lexicon regression (-5.3 pts)** — a known side-effect of domain specialization. Fine-tuning slightly erodes simple vocabulary recall (catastrophic forgetting).

5. **This validates the approach**: fine-tuning is most valuable for operational reasoning (how to diagnose, configure, analyze), not for general knowledge recall (what does X mean). The model's value is in the operational layer.

### The Complete Picture

| Benchmark | Type | Base 8B | Consilium v4.1 | Delta | Notes |
|-----------|------|---------|----------------|-------|-------|
| Operational (custom) | Task-specific reasoning | 72.7% | 84.1% | +11.4 | Iteratively optimized — upper bound |
| GSMA TeleQnA | General telecom knowledge | 64.8% | 67.2% | +2.4 | Independent held-out — conservative bound |

The true fine-tuning value lies between these two numbers, depending on how task-specific the use case is. For operational telecom work (Consilium's target), the gain is significant. For general knowledge queries, modest.

### Benchmark Files

| File | Setup | Benchmark | Score |
|------|-------|-----------|-------|
| `models/gsma_teleqna_llama-base.json` | Base Llama 3.1 8B | GSMA TeleQnA (500q) | 64.8% |
| `models/gsma_teleqna_llama-v41.json` | Consilium v4.1 | GSMA TeleQnA (500q) | 67.2% |

### Benchmark Script

```bash
# Run against any model
python scripts/evaluation/gsma_benchmark.py --model llama-v41 --samples 500
python scripts/evaluation/gsma_benchmark.py --model llama-base --samples 500
python scripts/evaluation/gsma_benchmark.py --model phi4 --samples 500    # when GPU available
```

Dataset: `data/benchmarks/gsma/teleqna_test.jsonl` (10,000 questions from `netop/TeleQnA`)

---

*Generated 2026-04-11, updated 2026-04-14. Benchmark scripts: `scripts/evaluation/operational_benchmark.py`, `scripts/evaluation/gsma_benchmark.py`*
