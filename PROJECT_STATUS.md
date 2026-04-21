# Consilium — Network Intelligence Platform
## Project Status (Updated: 2026-03-23)

---

## Phase 1: Data Engineering ✅

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 1.1 | Download 3GPP specs (tspec_llm) | ✅ Done | ~1000+ spec sections |
| 1.2 | Prepare training data (03_prepare_training_data.py) | ✅ Done | 34,189 examples |
| 1.3 | Expand synthetic data (04, 05 scripts) | ✅ Done | NOC, KPI, intent-to-config |
| 1.4 | Expert responses collection (ChatGPT/Claude) | ✅ Done | expert_responses.jsonl |
| 1.5 | v2 data: Domain tagging + cleanup (06_clean_training_data.py) | ✅ Done | 27,552 records tagged [RAN]/[Core]/[Transport]/[IMS] |
| 1.6 | v2 data: Protocol knowledge generation | ✅ Done | 96 Q&A pairs (O-RAN, MIMO, N4, CA, etc.) |
| 1.7 | v2 data: KPI analysis generation | ✅ Done | 116 Q&A pairs (throughput, handover, paging, etc.) |
| 1.8 | v3 data: MCQ contamination removal | ✅ Done | Removed 92 MCQ-format records |
| 1.9 | v3 data: Final combined dataset (07_combine_v2_data.py) | ✅ Done | **34,309 records → train_v3.jsonl** |

**Data files:**
- `data/processed/train.jsonl` — v1 original (34,189)
- `data/v2_cleaned_train.jsonl` — v2 domain-tagged (34,189)
- `data/v2_protocol_knowledge.jsonl` — protocol additions (96)
- `data/v2_kpi_analysis.jsonl` — KPI additions (116)
- `data/train_v3.jsonl` — **final v3 dataset (34,309)**

---

## Phase 2: 1.5B Model (Exploratory) ✅

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 2.1 | Fine-tune Qwen 2.5-1.5B (v1, v2, v3) | ✅ Done | MLX on Mac M4 Pro |
| 2.2 | Ollama local chat | ✅ Done | telco-slm-base model |
| 2.3 | Evaluate on TeleQnA | ✅ Done | 54% (regressed from 58% base) |
| 2.4 | Evaluate on Operational Benchmark | ✅ Done | v3=61.4% |
| 2.5 | Conclusion: 1.5B too small | ✅ Done | See SLM_LIMITATIONS_ANALYSIS.md |

**Outcome:** 1.5B model has fundamental quality issues — domain bleeding, hallucination, can't reason. Moved to 7B.

---

## Phase 3: 7B Model Fine-tuning ✅ (v3 in progress)

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 3.1 | v1 training on Kaggle T4 (Account 1) | ✅ Done | 1400 steps, backup adapter |
| 3.2 | v1 training on Kaggle T4 (Account 3) | ✅ Done | 2000/2137 steps, loss ~0.35 |
| 3.3 | v1 model conversion (PEFT→HF→GGUF→Ollama) | ✅ Done | telco-7b-ft in Ollama |
| 3.4 | v1 benchmark | ✅ Done | **79.3%** (incident 76.6%, config 92.5%, KPI 65.2%, knowledge 80.9%) |
| 3.5 | v2 training on Kaggle T4 (Account 3) | ✅ Done | 1500/2151 steps |
| 3.6 | v2 model conversion + benchmark | ✅ Done | **77.8%** (MCQ contamination hurt KPI: 48.8%) |
| 3.7 | v3 data preparation (MCQ removal) | ✅ Done | 34,309 clean records |
| 3.8 | v3 training on RunPod A40 | 🔄 Running | 2145 steps, ~2hrs, ~$1 cost |
| 3.9 | v3 model conversion + benchmark | ⬜ Next | Target: 85%+ |

**Conversion pipeline (proven, repeatable):**
```
PEFT adapter → merge_and_unload() → Full HF model (15GB fp16)
→ convert_hf_to_gguf.py → GGUF f16 (15.2GB)
→ llama-quantize Q4_K_M → GGUF Q4 (4.5GB)
→ ollama create → telco-7b-v3 (servable locally)
```

**Benchmark comparison:**

| Model | Overall | Incident | Config | KPI | Knowledge |
|-------|---------|----------|--------|-----|-----------|
| Base Qwen 7B | 76.1% | 71.6% | 91.5% | 52.4% | 85.3% |
| FT v1 (2000 steps) | **79.3%** | 76.6% | 92.5% | 65.2% | 80.9% |
| FT v2 (1500 steps) | 77.8% | **80.9%** | 90.3% | 48.8% | 82.3% |
| FT v3 (2145 steps) | ⬜ Pending | — | — | — | — |

---

## Phase 4: Evaluation Framework ✅

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 4.1 | TeleQnA benchmark (10K public Q&A) | ✅ Done | eval_teleqna.py |
| 4.2 | Operational benchmark (100 Qs, 5 categories) | ✅ Done | operational_benchmark.py |
| 4.3 | Base 7B baseline | ✅ Done | 76.1% |
| 4.4 | FT v1 evaluation | ✅ Done | 79.3% |
| 4.5 | FT v2 evaluation | ✅ Done | 77.8% |
| 4.6 | FT v3 evaluation | ⬜ Next | After v3 training completes |
| 4.7 | Failure analysis + data improvement cycle | ✅ Done | Identified MCQ contamination, KPI weakness, catastrophic forgetting |

---

## Phase 5: RAG Pipeline ✅

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 5.1 | ChromaDB vector store | ✅ Done | 3.5M vectors from 3GPP specs |
| 5.2 | Retrieval integration | ✅ Done | Works with InvestigatorAgent |
| 5.3 | 3GPP reference citations | ✅ Done | Agent cites spec sections |

---

## Phase 6: Agent System ✅ (core done, advanced features pending)

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 6.1 | Phase 1: 5 agents + Supervisor | ✅ Done | Incident, Config, Healing, Optimization, Knowledge |
| 6.2 | Phase 2: Memory, chaining, routing fixes | ✅ Done | 100% routing accuracy |
| 6.3 | Phase 3B: InvestigatorAgent + mock tools | ✅ Done | KPI + Alarm + Config Audit tools |
| 6.4 | Phase 3B-ii: RAG integration | ✅ Done | 3GPP references in investigations |
| 6.5 | Phase 3B-iii: 3-tool planning guaranteed | ✅ Done | Always uses KPI, Alarm, Config tools |
| 6.6 | Phase 3B-iv: Connect real NMS/OSS APIs | ⬜ Pending | Replace mock tools with real data |
| 6.7 | Phase 3C: Agent Factory + feedback loop | ⬜ Pending | Dynamic agent creation |
| 6.8 | Agent benchmark | ✅ Done | 83.4% with full agent system |

---

## Phase 7: Consilium UI ✅

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 7.1 | FastAPI backend | ✅ Done | API server |
| 7.2 | Streamlit frontend | ✅ Done | Light theme, Consilium branding |
| 7.3 | Custom icon | ✅ Done | app/assets/consilium_icon.png |

---

## Phase 8: Integration + Validation ⬜

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| 8.1 | v3 model conversion (PEFT→GGUF→Ollama) | ⬜ After v3 training | ~30 min |
| 8.2 | v3 benchmark (target 85%+) | ⬜ After conversion | ~30 min |
| 8.3 | Replace base 7B with FT-7B in agents | ⬜ After benchmark passes | Update Ollama model name |
| 8.4 | Re-run agent benchmark with FT-7B | ⬜ After integration | Target: 90%+ (was 83.4% with base) |
| 8.5 | End-to-end Consilium demo validation | ⬜ Final step | UI → Agent → FT-7B → RAG → Response |

---

## Blockers

| Blocker | Status | Impact |
|---------|--------|--------|
| 1.5B model too small | ✅ Resolved | Replaced with 7B |
| 7B training infrastructure | ✅ Resolved | Kaggle → RunPod A40 |
| MCQ contamination in v2 | ✅ Resolved | Removed in v3 dataset |
| v3 benchmark pending | 🔄 In progress | Training on RunPod, ~2hrs |
| Mock tools in agents | ⚠️ Open | Need real NMS/OSS API connections |

---

## Infrastructure

| Resource | Details |
|----------|---------|
| **Dev machine** | MacBook Pro M4 Pro, 24GB RAM |
| **Training (current)** | RunPod A40 (48GB VRAM), CA-MTL-1, $0.40/hr |
| **Training (previous)** | Kaggle T4 x2 (free, 3 accounts) |
| **Local inference** | Ollama on Mac (Q4_K_M, ~9s/response) |
| **Vector DB** | ChromaDB (local) |
| **UI** | Streamlit + FastAPI |

---

## Key Learnings (see AI_ML_LEARNING.md for details)

1. **Loss plateau** — more steps doesn't help after convergence; improve data instead
2. **Catastrophic forgetting** — fine-tuning on narrow data hurts general knowledge
3. **Data quality > quantity** — 189 KPI examples in 34K total = weakest category
4. **MCQ contamination** — raw spec test procedures leak into model's output format
5. **Prompt engineering has limits** — stricter prompts made model worse (-1.9%)
6. **Evaluation-driven iteration** — benchmark → analyze → improve data → retrain
7. **Datacenter matters** — Israel pod: 170 KB/s; Montreal pod: 100+ MB/s
8. **Checkpoint strategy** — always save frequently, Kaggle has 12hr timeout
