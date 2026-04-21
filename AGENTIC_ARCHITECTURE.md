# CONSILIUM — Network Intelligence Platform
## Architecture & System Design

---

## What is Consilium?

Consilium is an AI-powered network intelligence platform for telecom operations. It combines a domain-specialized language model with a multi-agent architecture to diagnose network incidents, generate configurations, explain 3GPP protocols, and investigate complex cross-domain issues.

Everything runs locally — zero cloud API dependency, zero cost per query, full data privacy.

**Consilium** (Latin: *deliberation, judgment, plan of action*) — domain-trained, agent-driven, self-evolving network intelligence.

---

## Core Design Principles

1. **Domain-first** — A fine-tuned telecom model, not a general-purpose LLM with a system prompt
2. **Fully local** — All inference on local hardware via Ollama, no API calls in production
3. **Agent-routed** — A Supervisor classifies and routes to specialist agents, not one model doing everything
4. **Tool-augmented** — The Investigator agent calls external tools (KPI, Alarms, Config) to gather evidence before diagnosing
5. **RAG-grounded** — Knowledge answers are grounded in 3GPP specifications, not hallucinated

---

## Architecture

```
                         ┌──────────────────┐
                         │    USER / API     │
                         │  Streamlit UI     │
                         │  CLI / REST API   │
                         └────────┬─────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                       │
│                     (LangGraph)                               │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                 SUPERVISOR AGENT                        │  │
│  │                                                        │  │
│  │  • Classifies user intent                              │  │
│  │  • Routes to specialist agent(s)                       │  │
│  │  • Chains multiple agents for complex queries          │  │
│  │  • Synthesizes final response                          │  │
│  │  • Maintains conversation memory (last 10 turns)       │  │
│  └─────┬────────┬────────┬────────┬────────┬─────────┘    │
│        │        │        │        │        │              │
│   ┌────┘   ┌────┘   ┌────┘   ┌────┘   ┌────┘              │
│   ▼        ▼        ▼        ▼        ▼                    │
│ ┌──────┐┌──────┐┌──────┐┌──────┐┌───────────┐             │
│ │INCID-││KNOW- ││CONFIG││GENER-││INVESTIGA- │             │
│ │ ENT  ││LEDGE ││      ││ IC   ││   TOR     │             │
│ │AGENT ││AGENT ││AGENT ││AGENT ││  AGENT    │             │
│ └──┬───┘└──┬───┘└──┬───┘└──┬───┘└─────┬─────┘             │
│    │       │       │       │          │                    │
└────┼───────┼───────┼───────┼──────────┼────────────────────┘
     │       │       │       │          │
     ▼       ▼       ▼       ▼          ▼
┌──────────────────────────────────────────────────────────────┐
│                       TOOLS LAYER                            │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────────────┐ │
│  │  FT-7B   │ │   RAG    │ │     OPERATIONAL TOOLS        │ │
│  │ (Ollama) │ │ (Local)  │ │                              │ │
│  │          │ │          │ │  • KPI Lookup                │ │
│  │ Llama    │ │ ChromaDB │ │  • Alarm Query               │ │
│  │ 3.1 8B   │ │ 3.5M     │ │  • Config Audit              │ │
│  │ QLoRA    │ │ vectors  │ │  • (Future: NMS/OSS APIs)    │ │
│  └──────────┘ └──────────┘ └──────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Agents

### Supervisor

The brain of the system. Receives every user query, classifies it into one of six categories, and routes to the appropriate specialist. For complex queries spanning multiple domains (e.g., "diagnose this alarm AND suggest config changes"), it chains agents sequentially and synthesizes a unified response.

**Routes to:** incident, knowledge, config, general, investigate, or multi-agent chain

**Conversation context handling:**
- Maintains last 10 turns of conversation memory
- Follow-up detection: short queries (≤8 words) inherit the previous agent's category
- Enriches follow-up queries with the previous answer (~500 chars) so the executing agent sees context
- Known limitation: only the last answer is passed as context. Multi-turn queries needing 2+ prior answers require a sliding context window (future improvement)

**Data-aware routing guardrail:**
- After built-in agents are checked, a guardrail detects if the query references specific network entities (SITE-, CELL-, "compare", "KPIs")
- If yes → routes to Investigator (needs real data from tools, not SLM memory)
- If no → proceeds to Registry/Factory (pure knowledge domain)
- This prevents Factory from creating agents that answer with fabricated network data
- See full 5-step routing order in Agent Factory section below

### Incident Agent

Diagnoses network faults across six telecom domains. Trained on structured NOC scenarios covering RAN, Core, Transport, IMS, Security, and Power domains. Produces decisive, specific diagnoses — names the network function, the protocol, the first check to run.

**Input:** Alarm text, KPI anomalies, symptom descriptions
**Output:** Severity, domain, root cause, resolution steps, escalation path

**Style:** No probability ranking, no generic "possible causes" lists. Names the specific cause first, then explains why.

**Domains covered:**
- **RAN** — handover failures, interference, capacity, SON/ANR, backhaul
- **Core** — AMF/SMF/UPF issues, registration, PDU session, slice management
- **Transport** — BGP, MPLS, DWDM, fiber, timing/sync, peering
- **IMS** — VoLTE/VoNR call failures, SIP error codes, P-CSCF/S-CSCF, codec negotiation
- **Security** — authentication, encryption, rogue device detection
- **Power** — battery backup, rectifier, solar/hybrid sites

### Knowledge Agent

Answers protocol and standards questions grounded in 3GPP specifications. Uses RAG to retrieve relevant specification chunks, then the fine-tuned model synthesizes a precise answer with exact terminology.

**Input:** Technical questions about standards, protocols, architecture
**Output:** Precise explanation with correct terminology, specification references where relevant

**Knowledge areas:**
- NSA vs SA architecture (EPC, 5GC, control plane distinctions)
- Synchronization signals (SSB, PSS, SSS)
- Carrier aggregation (PCell, SCell, component carrier)
- Core network functions (NRF registration lifecycle, AMF, SMF, UPF)
- Protocol stacks (NAS, RRC, NGAP, S1-AP, GTP, PFCP)
- 3GPP procedures (registration, handover, PDU session, bearer setup)

### Config Agent

Generates network configuration in YAML format from natural language intent. Trained on structured templates covering slicing, QoS, handover, SON, and more.

**Input:** Natural language configuration request
**Output:** Valid YAML configuration with parameter explanations

**Config types:**
- Network slicing (URLLC, eMBB, mMTC)
- Cell configuration and carrier aggregation
- Handover and mobility parameters
- QoS policies and DRX
- Core network (UPF, NRF, N3IWF, SEPP)
- SON, energy saving, MOCN sharing
- O-RAN xApp, MEC, NWDAF

### Investigator Agent

The most advanced agent — truly agentic. The only agent that queries external data at runtime. Plans a multi-step investigation, calls tool APIs to gather evidence, analyzes findings with guardrails, and produces a root cause diagnosis.

**Flow:**
1. Receives complex issue description
2. Plans investigation steps (which tools to call, in what order)
3. Executes tools: KPI Lookup → Alarm Query → Config Audit
4. Analyzes combined findings
5. Produces correlated diagnosis with evidence trail

**Input:** Complex or ambiguous issue needing investigation
**Output:** Investigation report with evidence, root cause, and remediation

**Tools available:**
| Tool | Purpose | Data Source |
|------|---------|-------------|
| KPI Lookup | Retrieve counter values, trends, thresholds | Network performance management |
| Alarm Query | Search active/historical alarms by site, severity, time | Fault management system |
| Config Audit | Check running config against baseline/best practice | Configuration management |

### Generic Agent

Last-resort fallback for queries that don't match any built-in or dynamic agent. Uses the SLM's general telecom knowledge without specialized context.

### Investigation Skills (Skill-Based Investigation)

The Investigator Agent uses a **skill-based architecture** rather than a single monolithic investigation step. Each skill is a specific capability with its own tools and analysis prompt:

| Skill | Tools Used | What It Does |
|---|---|---|
| **Triage** | alarm_query | Classify severity, domain, escalation path, urgency |
| **Diagnose** | alarm_query + kpi_lookup | Identify root cause by correlating alarms and KPIs |
| **Impact Assess** | kpi_lookup | Determine affected cells, users, SLA risk, spread |
| **Config Check** | config_audit | Rule out or confirm change-related faults |
| **Recommend** | (no tools — synthesizes prior skills) | Prioritized recovery actions with specific commands |

Skills are **chained** based on the query type:
- Alarm reported → triage → diagnose → impact → config check → recommend
- Degradation → diagnose → impact → config check → recommend
- Comparison → diagnose → impact → config check → recommend
- Config question → config check → diagnose → recommend
- General → triage → diagnose → recommend

**Current implementation (Tier 2 — built):**
- Individual skills are data-driven (each skill's tools, prompt, and output format are defined as data in `agents/investigation_skills.py`, not hardcoded methods). New skills can be added without code changes.
- Skill **chain selection** (which skills to run for a query) is keyword-matched against hardcoded patterns (e.g., "alarm" → full 5-skill chain, "compare" → 4-skill chain). This is the starting point.

**Resource model:** Each skill has two parts — a tool API call (10-50ms, near-zero CPU) and an SLM inference call (5-10 seconds, high CPU). The bottleneck is always SLM inference, not tool calls. A 5-skill investigation makes 6 SLM calls (~60 seconds total). Adding more tools (topology, alarm correlation, real NMS) adds milliseconds to tool calls but zero to SLM cost. The 4.6 GB model loads once in Ollama and stays resident — memory is constant regardless of skill count.

**Future evolution (Tier 3 — planned):**
- Skill chain selection evolves from usage. The system logs which chains worked for which query types, and the planner uses successful patterns instead of hardcoded keyword matching.
- Example: "For PORT_DOWN alarms, triage+diagnose+config_check worked 95% of the time but impact_assess added no value → auto-remove impact_assess from PORT_DOWN chain"

### Agent Factory (Dynamic Agents)

Makes Consilium self-evolving. When no built-in or saved agent matches a query, the Agent Factory:

1. Asks the SLM to infer the domain (name, keywords, expertise)
2. Builds a system prompt using a fixed template + SLM-generated domain parts
3. Saves as a **candidate** agent (not active — must earn promotion)
4. Uses it immediately for the current query
5. After 2+ successful uses → auto-promotes to **active**
6. After 30 days unused → auto-pruned

**Full routing order (5 steps):**

```
Step 1: Supervisor classifies query → category
    │
Step 2: BUILT-IN AGENTS (checked first, always)
    ├── "incident"    → IncidentAgent
    ├── "config"      → ConfigAgent
    ├── "knowledge"   → KnowledgeAgent (RAG if enabled)
    ├── "investigate"  → InvestigatorAgent (skill-based + tools)
    │
    └── No built-in match (general/knowledge with no handler)
            │
Step 3: DATA-AWARE ROUTING (guardrail)
            ├── Query mentions SITE-, CELL-, compare, KPIs?
            │     → YES: InvestigatorAgent (needs real data, not SLM memory)
            │
            └── NO: pure knowledge query
                    │
Step 4: REGISTRY CHECK
                    ├── Matching active/candidate agent? → Reuse it
                    │
                    └── No match
                            │
Step 5: AGENT FACTORY → creates candidate (only for pure knowledge domains)
                            │
                            └── Fallback: GenericAgent
```

**Why this order matters:**
- Built-in agents are always checked first — ConfigAgent handles "generate config" before Factory ever runs
- Data-aware routing prevents Factory from creating agents for queries that need real data
- Factory only creates agents for genuine knowledge domains (spectrum planning, billing, etc.) where SLM memory is the right data source
- This prevents agent explosion — most entity-specific queries go to Investigator, not new agents

**Domain canonicalization:** Word-level keyword overlap prevents creating duplicate agents for related domains (e.g., "spectrum planning" and "mmwave optimization" are recognized as the same domain).

**Storage:** SQLite database (`data/consilium.db`) with agent configs, states, versioning, and run logs.

See PLAN.md "Agent Factory Design" section for full architecture, lifecycle diagram, and schema.

---

## Self-Evolution — 3-Tier Model

Consilium evolves at three levels, all following the same lifecycle pattern (create candidate → use → promote if successful → prune if unused):

```
TIER 1: AGENTS (built — Agent Factory)
  Agent Factory creates new agents for unseen DOMAINS
  "Nobody handles spectrum planning" → creates SpectrumOptimizationAgent
  Lifecycle: candidate → active → disabled → pruned
  What's hardcoded: built-in agent list (Incident, Config, Knowledge, Investigator, Generic)
  What evolves: new domain agents created from usage

TIER 2: SKILLS (built — Skill Framework)
  Skills define specific CAPABILITIES within an agent
  "Investigator needs triage, diagnose, impact, config_check, recommend"
  Each skill's definition is data-driven (tools, prompt, output format)
  What's hardcoded: skill chain selection (keyword matching: "alarm"→5 skills, "compare"→4 skills)
  What evolves: skill definitions can be added/modified as data, no code changes

TIER 3: INVESTIGATION STRATEGIES (future — emerges from usage)
  Skill chain selection evolves from successful investigation patterns
  "For PORT_DOWN, triage+diagnose+config works 95% — skip impact_assess"
  Replaces hardcoded keyword matching with learned patterns
  What's hardcoded: nothing — fully emergent
  What evolves: which skills to chain for which query type
```

### What is fixed vs what evolves

| Layer | Fixed (human-defined) | Evolves (system-learned) |
|---|---|---|
| **Tools** | What APIs exist, what data they return | — |
| **Tool descriptions** | What each tool does (for SLM context) | — |
| **Skills** | Initially 5 built-in skills | New skills created for new task patterns |
| **Agents** | 5 built-in agents | New agents created by Agent Factory |
| **Skill chains** | Default chains per query type | Refined from investigation outcome logs |
| **Investigation plans** | — | Fully emergent from SLM + successful patterns |
| **SLM knowledge** | Trained weights (v4.1) | Improved via regression-driven retraining |

### The human's role

1. **Register tools** — tell the system what data sources exist (one-time)
2. **Review candidates** — optionally approve before promotion (quality gate)
3. **Add new tools** — when new data sources come online
4. **Retrain SLM** — periodic regression-driven patches when quality drifts

Everything else — what agents exist, what skills they have, how they investigate — the system discovers from usage.

---

## RAG Pipeline

Consilium has a local RAG pipeline built on 3GPP specifications for grounded knowledge answers.

| Component | Detail |
|-----------|--------|
| Source documents | 15,422 3GPP markdown files (Release 8-19) |
| Embedding model | all-MiniLM-L6-v2 |
| Vector store | ChromaDB (3.5M vectors, 64 GB, local) |
| Retrieval | Top-5 chunks per query |
| Framework | LlamaIndex |
| Status | Built and indexed. Disabled by default (`skip_rag=True`). Enable with `skip_rag=False` in `app/api_server.py` |

### How the SLM and RAG relate (important distinction)

The SLM and RAG are **completely separate systems** that complement each other:

| | SLM (Consilium v4.1) | RAG (ChromaDB) |
|---|---|---|
| **Contains** | Telecom knowledge baked into model weights from 49K training rows | Raw 3GPP specification text (TS 23.501, TS 38.300, etc.) from 15K documents |
| **Trained on** | Synthetic Q&A pairs (incidents, configs, KPI analysis, protocol explanations) | NOT trained — indexed for retrieval |
| **Used at** | Every query — generates all answers | Query time only — provides spec text as context to the SLM |
| **Without the other** | SLM answers from memory. Good for operations, but may fabricate spec references | RAG alone is just a search engine. Needs the SLM to synthesize answers from retrieved chunks |

**Together:** The SLM knows *how* to reason about telecom (from training). RAG knows *what* the specs actually say (from indexing). Combined: accurate answers with real specification references.

**The SLM was NOT trained on the ChromaDB data.** They are independent. This means:
- Enabling/disabling RAG doesn't change the SLM's behavior — it adds or removes spec-grounded context
- The SLM can hallucinate spec references when RAG is disabled (it generates from training memory)
- With RAG enabled, the SLM receives actual spec text and can cite correctly

---

## Fine-Tuned Model

Consilium uses a domain-specialized model, not a general LLM with a prompt.

| Property | Value |
|----------|-------|
| Base model | Meta Llama 3.1 8B Instruct |
| Fine-tuning method | QLoRA (r=16, alpha=32, 7 target modules) |
| Trainable parameters | 42M (0.5% of total) |
| Training data | ~49K examples: NOC incidents, configurations, KPI analysis, protocol knowledge, cross-domain troubleshooting |
| Inference format | GGUF Q4_K_M (~4.5 GB) via Ollama |
| Training hardware | RunPod A40 (48GB VRAM) |
| Inference hardware | MacBook Pro M4 Pro (24GB) |

### Training Data Composition

| Category | Description |
|----------|-------------|
| Incident diagnosis | NOC scenarios across RAN, Core, Transport, IMS, Security, Power |
| Configuration | YAML generation for 25+ config types |
| KPI analysis | Quantitative root cause analysis with thresholds, baselines, trends |
| Protocol knowledge | 3GPP protocol explanations with precise terminology |
| Cross-domain | Issues spanning RAN↔Transport, Core↔IMS, etc. |
| Cause codes | Specific failure cause interpretation (EMM, ESM, RRC, NAS) |

### Training Approach

The model is improved through regression-driven patch-tuning:
1. Benchmark the current model on 200+ evaluation questions
2. Identify specific regressions at the question level
3. Classify failure modes (e.g., terminology collapse, generic triage drift)
4. Generate targeted corrective data addressing each failure mode
5. Patch-tune from the current best model at low learning rate
6. Benchmark again — only ship if decision gate passes

This approach preserves existing strengths while surgically fixing weaknesses, rather than retraining from scratch each time.

---

## User Interface

### Streamlit Chat UI
- Dark theme with Consilium branding (clock/compass icon)
- Shows: agent used, category, response time
- Multi-agent chain visualization
- RAG source display
- Conversation memory indicator
- Sample queries in sidebar

### FastAPI Server
- `POST /query` — send query, get agent-routed response
- `GET /memory` — view conversation history
- `POST /clear` — reset conversation
- `GET /health` — system status

### CLI
- Interactive terminal chat with `/clear`, `/memory`, `/chain` commands

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language model | Meta Llama 3.1 8B Instruct + QLoRA |
| Model serving | Ollama (GGUF Q4_K_M) |
| Agent orchestration | LangGraph |
| RAG framework | LlamaIndex |
| Vector store | ChromaDB |
| Embeddings | all-MiniLM-L6-v2 (HuggingFace) |
| API server | FastAPI |
| Web UI | Streamlit |
| Fine-tuning | Unsloth (QLoRA) |
| Training infra | RunPod (A40 GPU) |
| Inference hardware | MacBook Pro M4 Pro 24GB |

**Cost:** $0/month for inference. Training runs cost ~$1-2 per session on RunPod spot instances.

---

## Workflow Examples

### 1. NOC Engineer — Active Alarm

> "ERAB setup success rate dropped from 99.1% to 92.3% on METRO_100 over 2 hours"

→ Supervisor routes to **Incident Agent**
→ Decisive diagnosis: S1-AP signaling congestion from MME overload, first check MME CPU and SCTP association count
→ 3 seconds, $0

### 2. Planning Engineer — Protocol Question

> "What's the difference between NSA Option 3 and Option 3x?"

→ Supervisor routes to **Knowledge Agent**
→ RAG retrieves 3GPP 37.340 chunks → model explains: Option 3 routes all user plane through MN (eNB→EPC), Option 3x splits user plane with SCG bearer direct to 5GC via SN (gNB). Names S1-U, X2, MCG/SCG bearer explicitly.
→ 5 seconds, $0

### 3. NOC Manager — Complex Investigation

> "South sector showing throughput degradation since Tuesday, need root cause"

→ Supervisor routes to **Investigator Agent**
→ Plans: KPI check → alarm check → config audit
→ KPI tool finds PRB at 95%, alarm tool finds RTWP active, config audit finds default interference thresholds
→ Diagnosis: external uplink interference, recommends RTWP threshold adjustment + frequency replanning
→ 15 seconds, $0

### 4. Config Engineer — New Slice

> "Create URLLC slice config for autonomous vehicle corridor"

→ Supervisor routes to **Config Agent**
→ Generates complete YAML: SST=2, latency budget 1ms, dedicated UPF, QoS flow with 5QI=80, isolation level "full"
→ 5 seconds, $0

---

## Agent Data Sources — Where Each Agent Gets Its Data

Understanding where each agent's answers come from is critical for knowing what to trust and what to verify.

| Agent | Data Source | What This Means | Trust Level |
|---|---|---|---|
| **Supervisor** | SLM weights only | Classifies intent from learned patterns. No external lookup | High for routing, not for content |
| **IncidentAgent** | SLM weights only | Diagnoses from 49K training patterns. Same answer regardless of actual network state | Good for general diagnosis, not site-specific |
| **ConfigAgent** | SLM weights only | Generates YAML from learned patterns. Not from real templates or vendor docs | Good for structure, verify parameter values |
| **KnowledgeAgent** | SLM + RAG (if enabled) | With RAG: retrieves real 3GPP spec text → accurate citations. Without RAG (current default): answers from memory, may fabricate spec references | High with RAG, medium without |
| **InvestigatorAgent** | SLM + Tool APIs | Only agent with external data. Calls data service at query time → gets cell-specific KPIs, alarms, config | Highest — data-grounded analysis |
| **Factory agents** | SLM weights only | Same model with specialized system prompt. No tools, no RAG, no external data | Same as GenericAgent with better framing |
| **GenericAgent** | SLM weights only | General telecom knowledge from training memory | Medium — useful but ungrounded |

### What "Tool API data" actually means (Investigator Agent)

The Investigator makes real HTTP calls to the Telecom Data Service (port 3003) at query time:

```
InvestigatorAgent → HTTP GET localhost:3003/kpi?cell_id=SITE-METRO-002-S2
                  → HTTP GET localhost:3003/alarms?site_id=SITE-METRO-002
                  → HTTP GET localhost:3003/config?cell_id=SITE-METRO-002-S2
```

**What "live" means:**
- Real API call — actual HTTP request/response at query time
- Real-time generated — data computed on demand with diurnal patterns and anomaly injection
- Deterministic — same cell + same hour = same data (not random)
- Correlated — alarms match KPI anomalies, config changes are realistic

**What "live" does NOT mean (current Tier 1):**
- Not from a real network
- Not from real NMS/OSS
- Not changing based on actual network events

**Path to truly live data:**
```
Current (Tier 1):  Synthetic data service → real API calls, generated data
Tier 2:            O-RAN/ONAP Docker → standards-compliant simulated data
Tier 3:            OAI/srsRAN → actual RF-level metrics from protocol stack
Production:        Vendor NMS/OSS → real network data
```

### Next improvement: Connect more agents to real data

Currently only the Investigator has external data access. The next phase should extend this:

| Agent | What it needs | How | Impact |
|---|---|---|---|
| **IncidentAgent** | Live KPIs for reported cell | Give tool access — query KPIs before diagnosing | Site-specific diagnosis instead of generic patterns |
| **ConfigAgent** | Current baseline config | Query config endpoint — show what's currently set | "Change X from current Y to Z" instead of generic YAML |
| **KnowledgeAgent** | 3GPP spec text | Enable RAG (`skip_rag=False`) — already built | Accurate spec citations instead of fabricated references |
| **Factory agents** | Domain-specific docs | RAG access to vendor/domain documentation | Grounded domain answers instead of SLM memory |

---

## Current Deployment Status (2026-04-08)

All agents now use **Consilium v4.1** (llama-telco-v41) through Ollama. The 1.5B MLX model and domain correction workaround have been retired. Code changes done, end-to-end testing pending.

| Change | Before | After |
|---|---|---|
| All agent inference | Qwen 1.5B (MLX) + Qwen 7B (Ollama) | Consilium v4.1 (Ollama only) |
| Domain correction | ~80 lines of keyword patching | Removed — v4.1 classifies correctly |
| MLX dependency | Required for Incident + Config agents | Not required |
| Model cost | $0 (two local models) | $0 (one local model) |

## Production Architecture

### Service Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    MacBook Pro M4 Pro 24GB                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Streamlit UI │  │ Consilium API│  │ Telecom Data Svc │  │
│  │  port 8501   │→ │  port 3002   │→ │    port 3003     │  │
│  │              │  │  (FastAPI)   │  │    (FastAPI)     │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────┘  │
│                           │                                  │
│                    ┌──────┴───────┐                          │
│                    │    Ollama    │                          │
│                    │  port 11434  │                          │
│                    │ llama-telco  │                          │
│                    │   -v41      │                          │
│                    │  (4.6 GB)   │                          │
│                    └──────────────┘                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   SQLite DB  │  │  ChromaDB   │                         │
│  │ consilium.db │  │  64 GB      │                         │
│  │ Agent Factory│  │  3.5M vec   │                         │
│  │  registry    │  │ (disabled)  │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

**Startup order:** Data Service (no deps) → Ollama (model load) → Consilium API (depends on Ollama + Data Service) → Streamlit UI (depends on API)

**Start commands:**
```bash
# Terminal 1: Data service
uvicorn app.telecom_data_service:app --port 3003

# Terminal 2: API server
TOKENIZERS_PARALLELISM=false uvicorn app.api_server:app --port 3002

# Terminal 3: Streamlit UI
streamlit run app/streamlit_ui.py
```

### Docker Compose (Production)

```yaml
services:
  ollama:         # port 11434, GPU-enabled, persistent volume
  consilium-api:  # port 3002, depends on ollama + data service
  telecom-data:   # port 3003, standalone
  streamlit-ui:   # port 8501, depends on consilium-api
```

All services have health checks (`/health`, 30s interval, 10s timeout, 3 retries, `unless-stopped` restart). See DEPLOYMENT_PLAYBOOK.md for full Docker Compose spec.

---

## Performance Characteristics

### Response Time Breakdown

| Component | Time | CPU | Memory |
|-----------|------|-----|--------|
| Tool API call (local) | 10-50ms | Near zero | Negligible |
| Tool API call (remote NMS) | 100-500ms | Near zero | Negligible |
| SLM inference (per call) | 5-10 seconds | **HIGH** | Constant ~5 GB (model resident in Ollama) |

**Key insight:** 99% of compute cost is SLM inference, not tool calls. Model loads once in Ollama and stays resident — memory is constant regardless of query volume.

### Investigation Cost Model

| Query Type | Skills Chained | SLM Calls | Tool Calls | Total Time |
|---|---|---|---|---|
| Simple alarm | triage + diagnose + recommend | 4 | 3 | ~40s |
| Full investigation | all 5 skills + synthesis | 6 | 5-7 | ~60s |
| Site comparison (2 sites) | 8 calls + synthesis | 7-9 | 8-12 | ~80s |
| Legacy (pre-skills) | plan + analyze | 2-3 | 3 | ~15-20s |

### Temperature Settings

| Temperature | Use Case |
|---|---|
| **0.0** | Automated incident triage (no human review) |
| **0.1** | Production fault diagnosis with human review |
| **0.2-0.3** (current) | Demo/pilot, knowledge Q&A, Agent Factory domain inference |
| **0.5+** | Never for production telecom |

---

## TMF API Compliance

The Telecom Data Service aligns with TM Forum Open APIs for interoperability with production OSS/BSS:

| TMF Standard | Domain | Current Endpoint | TMF Endpoint |
|---|---|---|---|
| **TMF628** | Performance Management | `GET /kpi` | `GET /tmf-api/performanceManagement/v4/measurementCollectionJob` |
| **TMF642** | Alarm Management | `GET /alarms` | `GET /tmf-api/alarmManagement/v4/alarm` |
| **TMF639** | Resource Inventory | `GET /config` | `GET /tmf-api/resourceInventoryManagement/v4/resource` |

**Implementation approach:** Adapter pattern — keep simple internal data format, add `tmf_adapter.py` that translates responses at API boundary. Tools use simple format internally; external API serves TMF-compliant responses. OpenAPI specs available at github.com/tmforum-apis/ (Apache 2.0).

---

## Known Limitations

| # | Limitation | Impact | Mitigation Path |
|---|---|---|---|
| 1 | No vendor-specific knowledge | Config uses generic 3GPP params, not Huawei MML/Ericsson MOM/Nokia CLI | Index vendor docs in RAG; add vendor-specific training data |
| 2 | FR2/mmWave parameter gaps | SCS defaults to 30 kHz (FR1), should be 120 kHz for FR2 | Add FR2-specific training rows |
| 3 | 8B model reasoning ceiling | Complex multi-step correlations (3+ faults) may be shallow | Accept for Tier 1; consider 70B or RAG augmentation |
| 4 | No real-time data | Data service synthetic, in-memory, resets on restart | Move to Tier 2 (O-RAN/ONAP Docker) or persistent storage |
| 5 | Single-user design | No concurrent sessions, no multi-tenant | Add session IDs, user auth, conversation isolation |
| 6 | No feedback loop | Agent Factory `success_signal` always True | Add thumbs up/down to UI, wire to `agent_runs.success_signal` |
| 7 | Factory data fabrication risk | Factory agents answer from SLM memory only | Data-aware routing guardrail (implemented) forces entity queries to Investigator |
| 8 | Skill chain selection hardcoded | Keyword matching may miss optimal chain for novel queries | Tier 3: log outcomes per chain, feed back to planner |
| 9 | Only Investigator has external data | Other agents answer from SLM training memory | Extend tools to IncidentAgent/ConfigAgent; enable RAG for Knowledge |
| 10 | RAG disabled by default | Knowledge falls to Generic/Factory; spec refs fabricated | Enable with `skip_rag=False` in api_server.py (ChromaDB 64 GB ready) |
| 11 | Tool-calling is prompt-based | Free-form JSON for tool calls; malformed JSON possible | Move to Llama 3.1 native function calling |
| 12 | Ollama model name hardcoded | `llama-telco-v41` hardcoded in `telco_agents.py` | Move to environment variable |
| 13 | Multi-turn context limited | Follow-ups see only previous response; 2+ prior answers lost | Sliding window of last 2-3 responses |

---

## Architectural Lessons Learned

### Lesson 1: Multi-Level Validation (Cell 331145 Incident)
- **What happened:** Only KPI endpoint validated cell IDs. Alarm endpoint accepted any ID (returned empty with no error). Config returned global baseline template for any cell.
- **Result:** Guardrail scored PARTIAL_DATA instead of NO_DATA → SLM fabricated realistic KPI values (170.5 Mbps, SINR 12.5 dB) for non-existent cell.
- **Fix:** All endpoints now validate entity IDs. Unknown IDs return explicit error + available IDs list.
- **Principle:** Validation must exist at EVERY endpoint. Default/template data is as dangerous as no data for SLM input.

### Lesson 2: Synthesis-Level Hallucination (Cell 4578203 Incident)
- **What happened:** `recommend` skill has no tools — tool-level guardrail didn't apply. Triage/diagnose correctly reported "no data", but synthesis step combined empty results and SLM fabricated a full S11/GTP-C diagnosis.
- **Fix:** Four-level guardrail architecture: Data service → Skill → Synthesis → Agent. Synthesis checks if ANY skill got real data before invoking SLM.
- **Principle:** Every code path that invokes the SLM is a potential guardrail bypass. Ask: "What happens if all inputs are empty?"

### Lesson 3: Data-Aware Routing (Compare Sites Incident)
- **What happened:** User asked "Compare SITE-X and SITE-Y". Factory created an agent that fabricated network performance numbers from SLM memory.
- **Fix:** Data-aware routing guardrail: queries mentioning SITE-, CELL-, compare, KPIs are forced to Investigator (which has real tool access).
- **Principle:** Any code path producing quantitative claims must either have tool access OR explicitly disclaim estimates.

### Lesson 4: Multi-Turn Context Loss (Nokia Follow-Up)
- **What happened:** User asked 3 sequential questions; third agent lost context from first two. Conversation memory was built for Supervisor only, not passed to executing agents.
- **Fix:** Follow-ups (≤8 words) inherit previous agent's category; enriched query includes prior response (~500 chars).
- **Remaining gap:** Only last answer is passed. Multi-turn queries needing 2+ prior answers need a sliding context window.

### Lesson 5: SLM Output Post-Processing (Factory Keywords)
- **What happened:** SLM generated compound keywords (`mmwave_dense_urban`) that didn't match user queries. Domain similarity missed "spectrum" vs "mmwave" overlap.
- **Fix:** Keyword expansion breaks compounds into individual words + word-level Jaccard similarity (30% threshold, 3 word minimum).
- **Principle:** Never trust SLM to generate well-formatted structured data; always post-process and normalize.

---

## Future Roadmap

### What's Built vs What's Next

| Capability | Status | Description |
|------------|--------|-------------|
| **Telecom Data Service (Tier 1)** | **BUILT** | FastAPI (port 3003), 30 cells, 10 sites, 4 active anomalies, correlated alarms |
| **4-Level Anti-Hallucination Guardrails** | **BUILT** | Data service → Skill → Synthesis → Agent level. 16 test cases validated |
| **Agent Factory** | **BUILT** | SQLite registry, hybrid prompt, candidate lifecycle, domain canonicalization |
| **Investigation Skills (5)** | **BUILT** | Triage, diagnose, impact, config check, recommend. Data-driven definitions |
| **Data-Aware Routing** | **BUILT** | Prevents Factory from fabricating network data |
| **Tool-calling reliability** | Partial | Prompt fixes + ID extraction done. Parameter validation + structured function calling remaining |
| **O-RAN / ONAP Simulators (Tier 2)** | Planned | Docker-based O-RAN sim-o1-interface and ONAP NF Simulator for 3GPP PM/FM/CM |
| **Live Protocol Stack (Tier 3)** | Research | OAI+FlexRIC or ns-O-RAN for real E2SM-KPM metrics |
| **Feedback loop** | Planned | User ratings improve routing accuracy and Agent Factory quality |
| **Persistent memory** | Planned | Database-backed conversation history across sessions |
| **Production hardening** | Documented | Auth, caching, monitoring, structured tool-use. Full playbook in DEPLOYMENT_PLAYBOOK.md |
| **TMF API compliance** | Designed | Adapter pattern for TMF628/642/639. See section above |

### External Tools Progression
```
Tier 1 (BUILT):    Synthetic data service → Real API calls → Architecture validated
Tier 2 (NEXT):     O-RAN/ONAP Docker simulators → Standards-compliant data → Demo-ready
Tier 3 (LATER):    OAI/srsRAN live protocol stack → RF-level KPIs → Research-grade
Production:        Vendor NMS/OSS → Live network → Operator deployment
```

See PLAN.md for full 21-step journey and DEPLOYMENT_PLAYBOOK.md for production deployment guide, security phases, and scaling recommendations.
