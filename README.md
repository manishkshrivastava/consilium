# Consilium

**Domain-trained. Agent-driven. Self-evolving.**

A domain-specialized Small Language Model for telecom network operations, built on Llama 3.1 8B and fine-tuned with QLoRA on 49K+ telecom examples. Consilium pairs the fine-tuned SLM with a multi-agent architecture — 6 specialist agents, 5 investigation skills, 3 tool interfaces, and RAG over 3GPP specifications — to deliver structured, grounded answers for network incident diagnosis, configuration generation, standards Q&A, and root-cause investigation.

Everything runs locally. Zero cloud dependency. Zero operational cost.

---

## Benchmarks

### Operational Benchmark (100 task-specific questions)

| Setup | Overall | Config | Knowledge | Incident | KPI |
|-------|---------|--------|-----------|----------|-----|
| Base Llama 3.1 8B | 72.7% | 91.2% | 73.3% | 70.0% | 52.7% |
| **Consilium v4.1** | **84.1%** | **94.3%** | **92.3%** | **77.9%** | **72.0%** |
| Delta | **+11.4** | +3.1 | +19.0 | +7.9 | +19.3 |

### GSMA TeleQnA — Independent Held-Out (500 questions, industry-standard)

| Subject | Base 8B | Consilium v4.1 | Delta |
|---------|---------|----------------|-------|
| Standards overview | 60.9% | 67.4% | **+6.5** |
| Standards specifications | 53.1% | 56.2% | +3.1 |
| Research overview | 62.3% | 69.3% | **+7.0** |
| **Overall** | **64.8%** | **67.2%** | **+2.4** |

No Consilium model was trained or optimized against GSMA TeleQnA. This is a completely independent evaluation using the GSMA/netop benchmark (10,000 MCQs from 3GPP specs and research papers).

---

## Architecture

```text
User Query
    │
    ▼
┌─────────────────────────────┐
│   SUPERVISOR AGENT          │
│   Classifies → Routes       │
│   (incident | investigate | │
│    knowledge | config |     │
│    general | followup)      │
└──────────┬──────────────────┘
           │
    ┌──────┼──────┬──────────┬──────────┐
    ▼      ▼      ▼          ▼          ▼
┌───────┐┌─────┐┌─────────┐┌────────┐┌───────┐
│Incident││Config││Knowledge││Investi-││Generic│
│ Agent  ││Agent ││ Agent   ││ gator  ││ Agent │
│        ││     ││  + RAG  ││Agent   ││       │
│SLM-only││YAML ││3.5M vec ││5 skills││Fallbk │
└───────┘└─────┘└─────────┘│3 tools │└───────┘
                            │+ RAG   │
                            └────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
                ┌───────┐ ┌─────────┐ ┌────────┐
                │Triage │ │Diagnose │ │Recommend│
                │       │ │         │ │        │
                │alarm  │ │alarm +  │ │synthe- │
                │query  │ │kpi +    │ │sis     │
                └───┬───┘ │config   │ └────────┘
                    │     └─────────┘
                    ▼
              ┌──────────┐  ┌────────────┐
              │Impact    │  │Config      │
              │Assess    │  │Check       │
              │kpi_lookup│  │config_audit│
              └──────────┘  └────────────┘
```

Plus **Agent Factory** — dynamically creates new specialist agents for unseen knowledge domains. SQLite-backed lifecycle: candidate → active → pruned.

### Agents

| Agent | Role | Data Sources |
|-------|------|-------------|
| **Supervisor** | Classifies queries, routes to specialists, plans multi-agent chains | SLM-only |
| **Incident** | Diagnoses alarms/faults across 6 domains (RAN, Core, Transport, IMS, Security, Power) | SLM-only |
| **Config** | Generates network configuration YAML from natural language | SLM-only |
| **Knowledge** | Answers 3GPP/standards questions grounded in specifications | RAG (ChromaDB, 3.5M vectors) |
| **Investigator** | Multi-step root cause investigation with tool calls and skill chains | 3 tools + 5 skills + RAG |
| **Generic** | Fallback for unmatched queries | SLM-only |

### Investigation Skills

| Skill | Tools | Output |
|-------|-------|--------|
| **Triage** | alarm_query | severity, domain, escalation, urgency |
| **Diagnose** | alarm_query + kpi_lookup | root cause, evidence, confidence |
| **Impact Assess** | kpi_lookup | cells/users affected, SLA risk |
| **Config Check** | config_audit | change correlation, rollback recommendation |
| **Recommend** | _(synthesis)_ | prioritized recovery actions |

Skills chain automatically based on query type: alarm → `triage → diagnose → impact → config_check → recommend`

### Tools

| Tool | Endpoint | Data |
|------|----------|------|
| **kpi_lookup** | /kpi | Throughput, PRB utilization, SINR, ERAB drop rate, handover success |
| **alarm_query** | /alarms | Active/historical alarms with severity, time, probable cause |
| **config_audit** | /config | Configuration baselines, recent changes, deviations |

---

## Training Pipeline

```text
3GPP TSpec-LLM (15K docs)           Synthetic NOC/Config data
        │                                      │
        ▼                                      ▼
   49K base training examples (v2: QLoRA, Kaggle T4)
        │
        ▼
   +7.4K patch (v4: targeted corrections, RunPod A40)
        │
        ▼
   +1.3K micro-patch (v4.1: 4-category precision fix, RunPod A40)
        │
        ▼
   Consilium v4.1 — 84.1% operational, 67.2% GSMA
```

| Version | Data | Method | Score |
|---------|------|--------|-------|
| v2 | 49K rows | QLoRA, LR=2e-4, 3 epochs | 81.9% |
| v4 | +7.4K patch | QLoRA, LR=5e-5, 1 epoch | 82.8% |
| v4.1 | +1.3K micro-patch | QLoRA, LR=3e-5, 2 epochs | **84.1%** |

Fine-tuning approach: iterative patching rather than full retraining. Each version patches the previous one's weakest categories without losing prior gains.

---

## Quick Start

### Prerequisites

- Python 3.11+ (for manual setup)
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (for containerized setup)
- [Ollama](https://ollama.ai) installed and running (if running manually)
- 8 GB+ RAM (16 GB recommended)

### 🐳 Option 1: Docker Setup (Recommended for API server)
The easiest way to run the Consilium API and Ollama together without manually installing dependencies is using Docker Compose.

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone [https://github.com/manishkshrivastava/consilium.git](https://github.com/manishkshrivastava/consilium.git)
   cd consilium
   ```

2. Build and start the containers in detached mode:
   ```bash
   docker-compose up --build -d
   ```

3. The FastAPI server will be available at `http://localhost:8000`.
4. Ollama will run in the background on port `11434`.

**Pulling Models:**
If you need to pull a model into the Ollama container for the first time, run this command while the containers are running:
```bash
docker exec -it consilium_ollama ollama run llama3.1:8b-instruct-q4_K_M
```

To stop the application, run:
```bash
docker-compose down
```

### Option 2: Manual Setup

**1. Clone and install**
```bash
git clone [https://github.com/manishkshrivastava/consilium.git](https://github.com/manishkshrivastava/consilium.git)
cd consilium
pip install -r requirements.txt
```

**2. Load the model into Ollama**
```bash
# If you have the GGUF file:
ollama create llama-telco-v41 -f models/Modelfile-v41

# Or pull the base model for comparison:
ollama pull llama3.1:8b-instruct-q4_K_M
```

**3. Run the CLI**
```bash
python agents/run_agents.py
```
Commands: `/agents` (list agents), `/memory` (show conversation history), `/chain` (show multi-agent plans), `/quit`

**4. Run the API server**
```bash
python app/api_server.py
```
Endpoints:
- `POST /query` — send a query
- `GET /health` — health check
- `GET /memory` — conversation history
- `GET /` — agent list and system info

**5. Run the Web UI**
```bash
streamlit run app/streamlit_ui.py
```

**6. Build the RAG index (optional)**
```bash
# Download 3GPP specs
python scripts/data_prep/01_download_tspec.py

# Build ChromaDB vector store
python scripts/rag/build_index.py
```

---

## Evaluation

### Run the operational benchmark

```bash
python scripts/evaluation/operational_benchmark.py --model llama-telco-v41
python scripts/evaluation/operational_benchmark.py --model llama3.1:8b-instruct-q4_K_M
```

### Run the GSMA TeleQnA benchmark

```bash
python scripts/evaluation/gsma_benchmark.py --model llama-v41 --samples 500
python scripts/evaluation/gsma_by_subject.py  # Per-subject breakdown
```

---

## Project Structure

```text
consilium/
├── agents/                     # Multi-agent system
│   ├── telco_agents.py         # 6 agents + orchestrator + supervisor
│   ├── investigator.py         # Agentic investigation with skill chains
│   ├── investigation_skills.py # 5 investigation skills (triage→recommend)
│   ├── tools.py                # KPI, Alarm, Config tool interfaces
│   ├── agent_factory.py        # Dynamic agent creation for new domains
│   ├── agent_registry.py       # SQLite-backed agent lifecycle management
│   └── run_agents.py           # Interactive CLI
├── app/                        # Serving layer
│   ├── api_server.py           # FastAPI REST API
│   ├── streamlit_ui.py         # Web UI
│   └── telecom_data_service.py # Mock/real data service
├── scripts/
│   ├── data_prep/              # 13-step data preparation pipeline
│   ├── training/               # MLX + QLoRA training scripts
│   ├── evaluation/             # Operational + GSMA benchmarks
│   └── rag/                    # RAG index building and querying
├── models/                     # Modelfiles, benchmark results, configs
├── notebooks/                  # Kaggle/RunPod/Colab training notebooks
└── configs/                    # Training configurations
```

---

## Key Design Decisions

**Why fine-tune an 8B model instead of using a frontier model?**
Runs locally with zero cost and zero latency to an API. For operational telecom tasks, the fine-tuned 8B outperforms the base model by +11.4 pts — closing most of the gap to much larger models at a fraction of the cost.

**Why iterative patching instead of full retraining?**
Each version patches the previous one's weakest categories (v4 patched v2's regressions, v4.1 micro-patched v4's last 4 weak spots). This preserves prior gains while targeting specific gaps — faster and more controlled than retraining from scratch.

**Why multi-agent instead of a single model?**
Different telecom tasks need different contexts. The Investigator needs tools and skill chains. The Knowledge agent needs RAG. The Config agent needs structured YAML output. A single prompt can't optimize for all of these. The Supervisor routes to the right specialist.

**Why RAG is disabled by default?**
Current RAG implementation hurts accuracy (74.5% vs 84.1% without). The fine-tuned model already internalizes 3GPP knowledge. RAG will be re-enabled after reranker integration, conditional triggering, and improved chunking.

---

## Honest Limitations

- All tools use synthetic data — mock KPIs, alarms, and configs
- Closed-loop automation not tested
- Single laptop scale — not benchmarked for production throughput
- Agent Factory works for knowledge domains only (not data-driven queries)
- Training data includes LLM-generated content
- No customer evaluation to date

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Base Model | Llama 3.1 8B Instruct |
| Fine-tuning | QLoRA (4-bit, PEFT) |
| Inference | Ollama (local, Q4_K_M quantization) |
| RAG | ChromaDB + sentence-transformers (all-MiniLM-L6-v2) |
| Agents | Custom Python (LangGraph-inspired orchestration) |
| API | FastAPI |
| Web UI | Streamlit |
| Persistence | SQLite (agent registry) |
| Training Infra | Kaggle T4, RunPod A40 |

---

## License

Apache 2.0

---

## Contributing

Issues and pull requests welcome. See [Discussions](https://github.com/manishkshrivastava/consilium/discussions) for ideas and Q&A.

If you're working in telecom AI, network operations, or SLM fine-tuning — I'd love to hear from you.
