# CONSILIUM — Deployment Playbook
## Step 21: Production Hardening & Deployment Guide
### Status: Documented — implement when moving to production environment

---

## Overview

This document captures everything needed to take Consilium from the current development state (MacBook Pro, local Ollama, OneDrive) to a production deployment. It covers security, reliability, standards compliance, and scaling.

**Current state (dev):**
- All services run locally on MacBook Pro M4 Pro 24GB
- Consilium v4.1 via Ollama (port 11434)
- Agent API via FastAPI (port 3002)
- Telecom Data Service via FastAPI (port 3003)
- SQLite database for Agent Factory (data/consilium.db)
- No authentication, no caching, no monitoring

**Target state (prod):**
- Containerized deployment (Docker Compose or Kubernetes)
- Authenticated API access
- TMF-compliant data service (Tier 2)
- Monitoring and alerting
- Persistent storage
- Auto-recovery

---

## System Components & Files

| Component | File | Port | Purpose |
|-----------|------|------|---------|
| **SLM** | Ollama (`llama-telco-v41`) | 11434 | Domain-trained Llama 3.1 8B — all agent inference |
| **Agent API** | `app/api_server.py` | 3002 | FastAPI server — query endpoint, memory, health |
| **Data Service** | `app/telecom_data_service.py` | 3003 | Synthetic KPI/alarm/config data for tools |
| **Streamlit UI** | `app/streamlit_ui.py` | 8501 | Chat interface |
| **Agent System** | `agents/telco_agents.py` | — | Supervisor routing, built-in agents (Incident, Config, Knowledge, Generic) |
| **Investigator** | `agents/investigator.py` | — | Tool-based investigation with guardrails |
| **Tools** | `agents/tools.py` | — | KPI Lookup, Alarm Query, Config Audit (call data service) |
| **Agent Registry** | `agents/agent_registry.py` | — | SQLite-backed dynamic agent storage |
| **Agent Factory** | `agents/agent_factory.py` | — | Creates candidate agents for unseen domains |
| **Database** | `data/consilium.db` | — | SQLite — agent configs, states, run logs |
| **Model GGUF** | `models/telco-v41-Q4_K_M.gguf` | — | 4.6 GB quantized model file |

## How to Start (Development)

### Prerequisites
- Python 3.13+ with venv
- Ollama installed with `llama-telco-v41` model loaded
- Dependencies: `pip install fastapi uvicorn httpx streamlit`

### Startup Order (3 terminals required)

```bash
# Terminal 1: Data Service (start first — no dependencies)
cd "/path/to/Training SLM"
source .venv/bin/activate
uvicorn app.telecom_data_service:app --port 3003

# Terminal 2: Agent API (depends on Ollama + Data Service)
cd "/path/to/Training SLM"
source .venv/bin/activate
TOKENIZERS_PARALLELISM=false uvicorn app.api_server:app --port 3002

# Terminal 3: Streamlit UI (depends on Agent API)
cd "/path/to/Training SLM"
source .venv/bin/activate
streamlit run app/streamlit_ui.py
```

### Verify All Services Running

```bash
# Data Service health
curl -s http://localhost:3003/ | python3 -m json.tool

# Agent API health
curl -s http://localhost:3002/health | python3 -m json.tool

# Ollama model loaded
ollama list | grep llama-telco-v41

# Quick test
curl -s http://localhost:3002/query -H "Content-Type: application/json" \
  -d '{"query": "eNodeB CPU at 95%"}' | python3 -m json.tool | head -5
```

### Enabling RAG (optional — adds 3GPP spec grounding)

**What RAG does:** When enabled, the Knowledge Agent retrieves actual 3GPP specification text from ChromaDB and passes it to the SLM as context. The SLM then synthesizes answers grounded in real specs rather than generating from training memory.

**Important:** The SLM and RAG are completely separate systems. The SLM was trained on synthetic Q&A pairs, NOT on the ChromaDB data. RAG adds context at query time — it doesn't change the model.

**To enable:**
```python
# In app/api_server.py, line 34:
_orchestrator = AgentOrchestrator(skip_rag=False)  # Change True to False
```

**Requirements:**
- ChromaDB data must exist at `rag/vector_db/chroma_3gpp/` (64 GB, already built)
- Python packages: `chromadb`, `llama-index`, `sentence-transformers`
- Adds ~2-3 GB memory (embedding model on MPS/GPU)
- Adds ~10-15 seconds to startup (loading collection)

**Effect when enabled:**
- Knowledge queries get 3GPP spec text as context → accurate spec citations
- Investigator Agent uses RAG for 3GPP procedure references during investigation

**Effect when disabled (current):**
- Knowledge queries fall to Factory/Generic agents
- SLM answers from training memory — may fabricate spec section numbers

### Loading the Model into Ollama (first time or after Modelfile changes)

```bash
cd models/
# Create Ollama model from Modelfile
ollama create llama-telco-v41 -f Modelfile-v41
```

**Important:** The Modelfile contains the default system prompt, temperature, and context window. If you change any parameter in `Modelfile-v41`, you must re-run `ollama create` to apply the changes to the Ollama model.

**Current Modelfile-v41:**
```
FROM ./telco-v41-Q4_K_M.gguf
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 1024
SYSTEM "You are Consilium, a telecom network intelligence assistant. Analyze network data, diagnose issues, and provide actionable recommendations."
```

**Note on system prompt precedence:** The Modelfile system prompt is the default, but each agent overrides it with its own system prompt at runtime (e.g., Investigator has investigation-specific prompt, ConfigAgent has config-specific prompt). The Modelfile prompt is only used when Ollama is called directly without a system prompt override — which happens rarely in production. Still, keep it consistent with the branding.

### Configuration Reference (all tunable parameters)

| Parameter | Value | File | Purpose |
|---|---|---|---|
| **Model** | `llama-telco-v41` | `agents/telco_agents.py:584` | Ollama model name |
| **Temperature** | 0.3 | `models/Modelfile-v41` | Controls output randomness. See "Temperature Guide" below |
| **Top-p** | 0.9 | `models/Modelfile-v41` | Nucleus sampling threshold |
| **Context window** | 1024 tokens | `models/Modelfile-v41` | Max input+output tokens. Trained at 1024 |
| **Conversation memory** | 10 turns (20 entries) | `agents/telco_agents.py:630` | Sliding window of user+assistant messages |
| **Follow-up word threshold** | ≤8 words | `agents/telco_agents.py:751` | Short queries inherit previous category |
| **Tool call timeout** | 10 seconds | `agents/tools.py` | HTTP timeout for data service calls |
| **Investigator max steps** | 6 | `agents/investigator.py` | Max tool calls per investigation |
| **Agent promotion threshold** | 2 uses | `agents/agent_registry.py` | Min successful uses to promote candidate→active |
| **Agent promotion success rate** | 60% | `agents/agent_registry.py` | Min success rate for promotion |
| **Domain similarity threshold** | 0.3 + 3 words | `agents/agent_registry.py` | Prevents duplicate agent domains |
| **Agent prune age** | 30 days | `agents/agent_registry.py` | Unused candidates auto-pruned after this |
| **RAG enabled** | False | `app/api_server.py:34` | Set to True to enable 3GPP spec grounding |
| **RAG top-k** | 5 chunks | `agents/telco_agents.py:281` | Number of spec chunks retrieved per query |
| **Multi-agent triggers** | "and", "then", diagnose+config | `agents/telco_agents.py:780` | Keywords that trigger multi-agent chaining |
| **Data-aware routing** | SITE-, CELL-, compare, KPIs | `agents/telco_agents.py` | Forces entity-specific queries to Investigator instead of Factory |
| **Data service URL** | `http://localhost:3003` | `agents/tools.py` | Telecom data service endpoint |

### Query Routing Order (5 steps)

Understanding how queries are routed is critical for debugging and production tuning.

```
Step 1: Supervisor classifies → category (incident/config/knowledge/investigate/general)
Step 2: Built-in agents checked FIRST
        incident → IncidentAgent | config → ConfigAgent
        knowledge → KnowledgeAgent | investigate → InvestigatorAgent
Step 3: Data-aware guardrail (if no built-in match)
        Query mentions SITE-/CELL-/compare/KPIs? → Investigator (needs real data)
Step 4: Registry check (if no entity detected)
        Matching dynamic agent? → Reuse it
Step 5: Agent Factory (if no registry match)
        Creates candidate agent for pure knowledge domains only
        Fallback: GenericAgent
```

**Key principle:** Factory should ONLY create agents for pure knowledge questions where SLM memory is the right data source. Anything referencing specific network entities must go to Investigator for real data lookup. This prevents agent explosion and data fabrication.

### Temperature Guide — Production Settings

**Current setting: 0.3** — produces slightly varied but high-quality output. Same query can produce different analysis emphasis on different runs.

**Why outputs vary at temperature 0.3:** Each SLM inference call samples tokens probabilistically. With 5 skills × 2 sites = 10+ SLM calls, small variation in early skills propagates to final synthesis. The underlying tool data is identical (deterministic), but the SLM's interpretation varies.

**What production systems typically use:**

| Temperature | Behavior | Best for | Used by |
|---|---|---|---|
| **0.0** | Fully deterministic. Same input = same output every time | Incident diagnosis, automated actions, compliance-critical output | Financial systems, medical AI, automated NOC actions |
| **0.1** | Near-deterministic. Minimal variation | Production fault diagnosis where consistency matters | Most production telecom AI deployments |
| **0.2-0.3** | Slight variation but focused. Current Consilium setting | Demo, pilot, human-reviewed analysis | Dev/pilot environments, copilot tools |
| **0.5-0.7** | Moderate creativity. Wider range of expression | Knowledge Q&A, document generation, brainstorming | Customer-facing chatbots, content generation |
| **1.0+** | High randomness. Creative but unpredictable | Creative writing, exploration | Never used in production telecom |

**Recommendation for production deployment:**

| Use Case | Recommended Temperature | Rationale |
|---|---|---|
| Automated incident triage (no human review) | **0.0** | Must be deterministic — automated escalation based on output |
| Investigation with human review | **0.1** | Consistent enough for trust, slight variation acceptable |
| Config generation | **0.0** | YAML parameters must be exact — no creative interpretation |
| Knowledge Q&A | **0.2-0.3** | Slight variation makes answers more natural |
| Agent Factory domain inference | **0.3** | Needs some flexibility to recognize novel domains |

**How to change:** Edit `models/Modelfile-v41` and re-run `ollama create llama-telco-v41 -f Modelfile-v41`. Or set per-agent temperatures in code (currently all agents share one model temperature).

**Per-agent temperature (future):** Different agents could use different temperatures by passing `options: {"temperature": 0.0}` in the Ollama API call. Not currently implemented but straightforward to add.

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TOKENIZERS_PARALLELISM` | `false` | Suppress HuggingFace warning |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL (change for Docker) |
| `DATA_SERVICE_URL` | `http://localhost:3003` | Data service URL (in `agents/tools.py`) |

### Database Reset (if needed)

```bash
# Reset Agent Factory registry (removes all dynamic agents)
rm -f data/consilium.db
# DB auto-recreates on next startup
```

---

## Phase 1: Security & Reliability (Deploy First)

### 1.1 API Authentication

**What:** Both services (agent API port 3002, data service port 3003) are currently open with no authentication.

**Implementation:**
```
Option A (simple): API key in header
- Generate API keys, store in environment variables
- Middleware checks X-API-Key header on every request
- Reject requests without valid key

Option B (production): JWT tokens
- Add /auth/token endpoint
- Issue JWT with expiry
- Validate JWT on every request
- Role-based access (read-only vs admin)
```

**Files to modify:**
- `app/api_server.py` — add auth middleware
- `app/telecom_data_service.py` — add auth middleware
- New: `app/auth.py` — token generation and validation

**Priority:** P1 — must have before any external access

### 1.2 Request Logging with Correlation IDs

**What:** Currently no way to trace a request from user query → supervisor → tool calls → data service → response.

**Implementation:**
```
- Generate UUID correlation_id for each incoming request
- Pass through all internal calls (agent → tools → data service)
- Log at each step: timestamp, correlation_id, component, action, latency
- Store in structured format (JSON logs or log aggregation service)
```

**Log format:**
```json
{
  "timestamp": "2026-04-08T17:00:00Z",
  "correlation_id": "abc-123-def",
  "component": "investigator",
  "action": "tool_call",
  "tool": "kpi_lookup",
  "params": {"cell_id": "SITE-METRO-002-S2"},
  "latency_ms": 45,
  "status": "success"
}
```

**Files to modify:**
- `app/api_server.py` — generate correlation_id
- `agents/telco_agents.py` — pass correlation_id through orchestrator
- `agents/investigator.py` — log with correlation_id
- `agents/tools.py` — log tool calls with correlation_id
- `app/telecom_data_service.py` — log incoming requests with correlation_id

**Priority:** P1 — cannot debug production issues without this

### 1.3 Input Validation (Complete)

**What:** Alarm and config endpoints still accept invalid IDs silently. Only KPI endpoint has unknown-entity detection.

**Implementation:**
- Apply `_resolve_cells()` with error returns to `/alarms` and `/config` endpoints
- Add `/topology/validate` endpoint for pre-flight ID checks
- Return standard error format: `{"error": "unknown_cell_id", "message": "...", "available": [...]}`

**Files to modify:**
- `app/telecom_data_service.py` — alarm and config endpoints

**Priority:** P1 — prevents SLM from analyzing invalid data

### 1.4 Health Checks & Auto-Restart

**What:** If a service dies, nobody notices. No auto-recovery.

**Implementation (Docker):**
```yaml
# docker-compose.yml
services:
  consilium-api:
    build: .
    ports: ["3002:3002"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  telecom-data:
    build: ./app
    ports: ["3003:3003"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped
```

**Priority:** P2 — important for uptime but not a security risk

---

## Phase 2: SLM Reliability Hardening

### 2.1 Parameter Validation Layer

**What:** The SLM sometimes generates invalid tool parameters (e.g., `site_id=affected`). Currently caught by data service returning empty results + guardrails. A proper validation layer would reject before calling.

**Implementation:**
```python
# In agents/tools.py, before calling data service:
VALID_PREFIXES = ["SITE-", "CELL-"]
INVALID_VALUES = ["affected", "unknown", "target", "all", "any"]

def validate_params(params):
    cell_id = params.get("cell_id")
    site_id = params.get("site_id")
    if cell_id and (cell_id in INVALID_VALUES or not any(cell_id.startswith(p) for p in VALID_PREFIXES)):
        return {"error": f"Invalid cell_id: '{cell_id}'"}
    if site_id and (site_id in INVALID_VALUES or not any(site_id.startswith(p) for p in VALID_PREFIXES)):
        return {"error": f"Invalid site_id: '{site_id}'"}
    return None  # valid
```

**Priority:** P2 — guardrails already catch most cases

### 2.2 Structured Function Calling (Llama 3.1 Native)

**What:** Currently the Investigator asks the SLM to generate free-form JSON for tool calls. This is fragile — wrong parameter names, malformed JSON, placeholder values. Llama 3.1 has a native tool-use format built into its chat template.

**Implementation:**
```python
# Instead of:
prompt = "Create a JSON plan with tool calls..."
raw_json = ollama.generate(prompt)
plan = json.loads(raw_json)  # fragile

# Use Llama 3.1 tool-use format:
tools = [
    {
        "type": "function",
        "function": {
            "name": "kpi_lookup",
            "description": "Look up KPIs for a cell or site",
            "parameters": {
                "type": "object",
                "properties": {
                    "cell_id": {"type": "string", "description": "Cell ID (e.g., SITE-METRO-002-S2)"},
                    "site_id": {"type": "string", "description": "Site ID (e.g., SITE-METRO-002)"},
                    "region": {"type": "string", "description": "Region name (North, South, East, West)"},
                },
            },
        },
    },
    # ... alarm_query, config_audit
]

response = ollama.chat(
    model="llama-telco-v41",
    messages=[...],
    tools=tools,  # Llama 3.1 native tool-use
)
# Response contains structured tool_calls, not free-form JSON
```

**Impact:** Most significant reliability improvement. Eliminates JSON parsing failures, wrong parameter names, placeholder values.

**Effort:** 4-6 hours (refactor Investigator planning + tool execution)

**Priority:** P2 — biggest long-term reliability gain, but guardrails handle edge cases for now

### 2.3 Retry Logic

**What:** If a tool call returns `invalid_param` error, the system should re-plan with the error message instead of analyzing empty data.

**Implementation:**
```python
# In investigator.py, after tool execution:
for finding in findings:
    if "error" in finding["result"]:
        # Re-plan with error context
        retry_prompt = f"Tool {finding['tool']} returned error: {finding['result']['error']}. "
        retry_prompt += "Adjust your parameters and try again."
        new_plan = self._parse_plan(self.ollama.generate(retry_prompt))
        # Execute retry plan...
```

**Priority:** P3 — nice to have, guardrails already prevent hallucination

### 2.4 Cross-Reference Tool Results

**What:** If KPIs show DEGRADED but alarms show 0 active, the system should flag the inconsistency instead of accepting both at face value.

**Implementation:** Add to `_assess_data_quality()`:
```python
if kpi_degraded > 0 and alarm_count == 0:
    data_quality["warning"] = "KPIs degraded but no alarms — possible monitoring gap"
```

**Priority:** P3

### 2.5 Confidence Scoring

**What:** Rate investigation quality based on data completeness.

**Implementation:**
```python
confidence = 0
if kpi_cells > 0: confidence += 30
if alarm_count > 0: confidence += 25
if config_changes > 0: confidence += 20
if kpi_degraded > 0: confidence += 15  # found something
if tools_with_data >= 3: confidence += 10
# Report confidence in response header
```

**Priority:** P3

---

## Phase 3: TMF API Compliance (Tier 2)

### 3.1 Why TMF Compliance Matters

TM Forum Open APIs are the industry standard for telecom OSS/BSS integration. If Consilium connects to a real operator's NMS/OSS, those systems likely expose TMF APIs. Demo audiences and standards bodies expect TMF-compliant interfaces.

### 3.2 APIs to Implement

| TMF API | Standard URL | Current Custom URL | What Changes |
|---------|-------------|-------------------|-------------|
| **TMF628** Performance Management | `GET /tmf-api/performanceManagement/v4/measurementCollectionJob` | `GET /kpi` | URL, response schema, pagination |
| **TMF642** Alarm Management | `GET /tmf-api/alarmManagement/v4/alarm` | `GET /alarms` | URL, response schema (perceivedSeverity, probableCause, correlatedAlarm) |
| **TMF639** Resource Inventory | `GET /tmf-api/resourceInventoryManagement/v4/resource` | `GET /config` | URL, response schema, resource hierarchy |

### 3.3 TMF Response Schema Examples

**TMF642 Alarm (standard format):**
```json
{
  "id": "ALM-100000",
  "href": "/tmf-api/alarmManagement/v4/alarm/ALM-100000",
  "alarmType": "equipmentAlarm",
  "perceivedSeverity": "major",
  "probableCause": "externalInterference",
  "specificProblem": "Uplink interference increased by 15dB",
  "alarmRaisedTime": "2026-04-08T08:55:17Z",
  "alarmClearedTime": null,
  "state": "raised",
  "alarmedObject": {
    "id": "SITE-METRO-002-S2",
    "href": "/tmf-api/resourceInventoryManagement/v4/resource/SITE-METRO-002-S2"
  },
  "correlatedAlarm": [
    {"id": "ALM-100001", "href": "..."}
  ]
}
```

**TMF628 Performance (standard format):**
```json
{
  "id": "PM-001",
  "href": "/tmf-api/performanceManagement/v4/measurementCollectionJob/PM-001",
  "granularity": "15min",
  "reportingPeriod": "2026-04-08T14:00:00Z/2026-04-08T14:15:00Z",
  "performanceIndicatorGroupSpecification": "RAN_KPI",
  "performanceIndicatorSpecification": [
    {"name": "SINR", "value": "0.1", "unit": "dB"},
    {"name": "DL_THROUGHPUT", "value": "12.2", "unit": "Mbps"},
    {"name": "PRB_UTIL_DL", "value": "42.7", "unit": "%"}
  ],
  "objectInstance": "SITE-METRO-002-S2"
}
```

### 3.4 Implementation Approach

**Option A (adapter pattern — recommended):**
Keep the current internal data format. Add a TMF adapter layer that translates responses to TMF format at the API boundary. Tools continue to use the simple internal format.

```
Tool → Internal API (simple JSON) → TMF Adapter → External API (TMF-compliant JSON)
```

**Option B (full rewrite):**
Rewrite the data service to use TMF schemas internally. More work, more correct, but slower.

**Recommendation:** Option A. Build a `tmf_adapter.py` that wraps the existing endpoints with TMF-compliant URLs and response transformation. Internal tools stay simple.

### 3.5 TMF API Source References

| Resource | URL | License |
|----------|-----|---------|
| TMF628 Performance OpenAPI spec | github.com/tmforum-apis/TMF628_Performance | Apache 2.0 |
| TMF642 Alarm OpenAPI spec | github.com/tmforum-apis/TMF642_AlarmManagement | Apache 2.0 |
| TMF639 Resource Inventory spec | github.com/tmforum-apis/TMF639_ResourceInventory | Apache 2.0 |
| FIWARE TM Forum Docker APIs | github.com/FIWARE-TMForum/docker-tmf-apis | Apache 2.0 |

---

## Phase 4: External Tool Integration (Tier 2 — Docker Simulators)

### 4.1 O-RAN SC sim-o1-interface

**What it provides:** Simulated O-RAN network elements with management plane via NETCONF/YANG and VES events.

**Data types:**
- PM data in 3GPP TS 32.435 XML format (15-min granularity)
- Fault notifications via NETCONF + VES
- Configuration via NETCONF/YANG with O-RAN defined models

**Deployment:**
```bash
# Docker deployment
docker pull nexus3.o-ran-sc.org:10001/o-ran-sc/nts-ng-o-ran-du:latest
# NTS Manager creates/destroys simulated network functions
# Exposes VES events to VES Collector
```

**Integration with Consilium:**
- VES Collector receives PM/fault events → stores in database
- Consilium tools query the database instead of synthetic generator
- Data follows actual 3GPP/O-RAN standards

**URL:** github.com/o-ran-sc/sim-o1-interface

### 4.2 ONAP NF Simulator VES Client

**What it provides:** REST-triggered VES event generation with customizable templates.

**Key features:**
- `POST /simulator/start` — periodic event sending
- `POST /simulator/event` — single event
- Template management with dynamic data keywords: `#RandomInteger`, `#Timestamp`, `#Increment`
- Pre-installed templates: notification, registration, cmNotification

**Deployment:**
```bash
docker-compose -f docker-compose.yml up -d
# Exposes REST API on port 5000
# Events sent to configured VES Collector
```

**URL:** github.com/onap/integration-simulators-nf-simulator-ves-client

### 4.3 Open5GS + Prometheus

**What it provides:** Real 5G core network metrics.

**Deployment:**
```bash
# Docker deployment
docker-compose -f docker-compose.yml up -d
# Prometheus metrics on configurable port (default 9090)
# Info API for UE/gNB/session data
```

**Metrics available:** AMF registration count, SMF session count, UPF throughput, NRF discovery latency

**URL:** open5gs.org/open5gs/docs/tutorial/04-metrics-prometheus/

### 4.4 Integration Architecture (Tier 2)

```
                    ┌─────────────────────────────────┐
                    │        Consilium Agent System       │
                    │         (port 3002)              │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────┴──────────────────┐
                    │      TMF Adapter Layer           │
                    │   (translates to/from TMF)       │
                    └──────────────┬──────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
    ┌─────────┴───────┐  ┌────────┴────────┐  ┌────────┴────────┐
    │  O-RAN SC sim   │  │  ONAP NF Sim    │  │  Open5GS +      │
    │  (NETCONF/VES)  │  │  (VES events)   │  │  Prometheus      │
    │  Docker         │  │  Docker          │  │  Docker          │
    └─────────────────┘  └─────────────────┘  └─────────────────┘
           PM data           Fault events        Core metrics
```

---

## Phase 5: Live Protocol Stack (Tier 3 — Research)

### 5.1 When to Use Tier 3

- Customer demos requiring live RF-level data
- Research into closed-loop automation (xApps, rApps)
- Academic papers requiring real protocol stack evidence
- Proof that Consilium works with actual gNB metrics, not just simulated patterns

### 5.2 Options

| Option | What It Gives | Prerequisites | Effort |
|--------|---------------|---------------|--------|
| **OAI + FlexRIC** | Real gNB with E2SM-KPM metrics (RSRP, MCS, BLER, throughput). Python xApp SDK | RF hardware or RF simulator, Linux, real-time kernel | High |
| **ns-O-RAN** | Full 5G NR simulation with KPMs to near-RT RIC via E2AP | ns-3 C++ compilation, significant compute | High |
| **srsRAN** | Real-time MAC/NGAP/RRC metrics via JSON websocket | RF hardware or ZMQ-based simulation | High |
| **5G-LENA** | Detailed PHY/MAC traces: SINR, RSRP, RSRQ, TB sizes | ns-3 C++ environment | High |

### 5.3 OAI + FlexRIC Integration Path

```
OAI gNB (RF simulator mode)
    │
    E2AP (SCTP)
    │
    ▼
FlexRIC near-RT RIC
    │
    xApp SDK (Python)
    │
    ▼
Consilium Data Adapter
    │
    ▼
Consilium Tools (KPI/Alarm/Config)
```

**KPMs available via E2SM-KPM:**
- DRB.PdcpSduVolumeDL/UL
- DRB.RlcSduDelayDl
- DRB.UEThpDl/UL
- RRU.PrbTotDl/UL
- RSRP, MCS, BLER, CQI

### 5.4 Production NMS/OSS Integration

**Ultimate target:** Connect to real operator NMS systems.

| Vendor | System | API Type | Access |
|--------|--------|----------|--------|
| Nokia | NetAct | REST / CORBA | Enterprise license required |
| Ericsson | ENM | REST | Enterprise license required |
| Huawei | iManager | SOAP / REST | Enterprise license required |
| Vendor D | NMS Platform | REST | Enterprise license required |

**No vendor provides free sandbox access.** Tiers 1-3 are stepping stones.

---

## Phase 6: Operational Infrastructure

### 6.1 Response Caching

**What:** Same KPI query hitting data service repeatedly. KPI data doesn't change every second.

**Implementation:**
```python
from functools import lru_cache
from datetime import datetime

# Cache KPI results for 5 minutes
@lru_cache(maxsize=256)
def get_cached_kpi(cell_id: str, hour: int, cache_key: int):
    return generate_kpi(cell_id, hour)

# cache_key = current_minute // 5 (refreshes every 5 min)
```

### 6.2 Rate Limiting

**Implementation:**
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.get("/kpi")
@limiter.limit("60/minute")
def get_kpi(...):
    ...
```

### 6.3 Skill-Based Investigation — Resource Cost Model

Each skill execution has two parts with very different resource profiles:

| Component | Time | CPU | Memory | What's happening |
|---|---|---|---|---|
| **Tool API call** | 10-50ms (local) / 100-500ms (remote NMS) | Near zero | Negligible | HTTP request to data service — no AI involved |
| **SLM inference** | 5-10 seconds | **HIGH** (matrix multiplications per token) | Constant ~5 GB (model stays loaded) | Ollama generates 200-400 tokens of analysis |

**Key insight:** 99% of compute cost is SLM inference, not tool calls. Adding more tools (topology, alarm correlation, real NMS) adds milliseconds. Each additional SLM inference call adds 5-10 seconds of high CPU.

**Cost per investigation type:**

| Query Type | Skills Chained | SLM Calls | Tool Calls | Total Time | CPU Impact |
|---|---|---|---|---|---|
| Simple alarm | triage + diagnose + recommend | 3 + 1 synthesis = 4 | 3 | ~40s | High for 40s |
| Full alarm | triage + diagnose + impact + config + recommend | 5 + 1 synthesis = 6 | 5-7 | ~60s | High for 60s |
| Comparison (2 sites) | diagnose×2 + impact×2 + config×2 + recommend | 6-8 + 1 synthesis = 7-9 | 8-12 | ~80s | High for 80s |
| Legacy (pre-skills) | plan + analyze | 2-3 | 3 | ~15-20s | High for 15-20s |

**Model stays loaded in memory (Ollama):** The 4.6 GB model loads once and stays resident. Memory does NOT increase per skill call. Only inference CPU spikes per call.

**The bottleneck is always SLM inference calls, not tool API calls.** Optimization levers:

| Approach | What it does | Impact |
|---|---|---|
| GPU inference (NVIDIA) | Runs model on GPU instead of CPU | 5-10x faster per inference call |
| Combine skills | Merge triage+diagnose into one SLM call | 1 fewer inference per investigation |
| Rule-based triage | Classify severity by alarm keywords, skip SLM | 1 fewer inference (saves ~8s) |
| Parallel skills | Run independent skills simultaneously | Same total CPU but faster wall time |
| Smaller model for simple skills | Use 3B for triage/impact, 8B for diagnose/recommend | Less compute per simple skill |

**Production recommendation:** For concurrent users, GPU inference (via NVIDIA NIM or Ollama with CUDA) is the primary scaling lever. The number of tools and external APIs has minimal impact on resource usage.

### 6.4 Monitoring Dashboard

**Stack:** Prometheus + Grafana

**Metrics to track:**
- Agent response time (P50, P95, P99)
- Tool call success rate per tool
- Supervisor routing accuracy
- SLM inference latency
- Agent Factory: candidates created, promoted, pruned
- Data service: requests/sec, error rate
- Ollama: GPU utilization, model load time

### 6.4 Data Service Persistent Storage

**What:** Currently all data is in-memory. Resets on restart.

**Implementation:**
- Move cell topology, alarms, config to SQLite or PostgreSQL
- Historical data retention (not just current hour)
- Configurable anomaly injection via API (for testing)
- `POST /admin/anomaly` — add/remove anomalies dynamically

### 6.5 Docker Compose (Full Stack)

```yaml
version: "3.8"

services:
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes:
      - ollama-models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  consilium-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports: ["3002:3002"]
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - DATA_SERVICE_URL=http://telecom-data:3003
      - DB_PATH=/data/consilium.db
    volumes:
      - consilium-data:/data
    depends_on:
      - ollama
      - telecom-data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3002/health"]
      interval: 30s
      retries: 3
    restart: unless-stopped

  telecom-data:
    build:
      context: .
      dockerfile: Dockerfile.data
    ports: ["3003:3003"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3003/health"]
      interval: 30s
      retries: 3
    restart: unless-stopped

  streamlit:
    build:
      context: .
      dockerfile: Dockerfile.ui
    ports: ["8501:8501"]
    environment:
      - API_URL=http://consilium-api:3002
    depends_on:
      - consilium-api
    restart: unless-stopped

volumes:
  ollama-models:
  consilium-data:
```

---

## Known Issues & Lessons Learned (from development testing)

These issues were found and fixed during development. They document failure patterns that could recur if code is modified or extended.

### Lesson 1: SLM Hallucination on Empty Tool Results (Cell 331145 Incident)

**What happened:** User queried a non-existent cell (331145). The KPI endpoint returned an error (had validation), but alarm endpoint returned empty results (no error) and config endpoint returned a global baseline template (no error, had data). The guardrail scored this as PARTIAL_DATA instead of NO_DATA, and the SLM fabricated realistic-looking KPI values (170.5 Mbps, SINR 12.5 dB) that didn't exist.

**Root cause:** Only one of three endpoints had unknown-entity validation. The guardrail is only as strong as the weakest endpoint.

**Fix applied:** All three endpoints (KPI, alarm, config) now validate cell_id/site_id against the topology. Unknown IDs return explicit error with available IDs. Systematic validation run tested 16 input combinations across all endpoints.

**Production lesson:** After adding validation to ANY endpoint, run systematic validation across ALL endpoints with every type of invalid input (fake IDs, empty strings, placeholder values like "affected"). Never assume one endpoint's fix covers the system.

### Lesson 2: Agent Factory Compound Keywords

**What happened:** The SLM generated compound keywords like `mmwave_dense_urban` and `spectrum_optimization` instead of individual words. When a related query came in with "mmWave frequency band planning", the keyword matcher couldn't find overlap because `mmwave_dense_urban` as a string doesn't contain `mmwave` as a match — it's a single compound token.

**Root cause:** 8B SLMs don't naturally produce atomic keywords. They generate descriptive phrases.

**Fix applied:** Keyword expansion in `agent_factory.py` — breaks compound terms into individual words using underscore/hyphen splitting. Also adds words from domain name and description. A query keyword set of `{mmwave, frequency, band, planning}` now overlaps with agent keyword set `{mmwave, spectrum, optimization, dense, urban}`.

**Production lesson:** Never trust the SLM to generate well-formatted structured data (keywords, parameter names, JSON). Always post-process and normalize SLM outputs before storing or matching.

### Lesson 3: Agent Reuse Wrong Code Path

**What happened:** When a similar query came in, `find_by_keywords` (the fast registry lookup) failed to match because the stored keywords were compounds. The system fell through to the Agent Factory, which called `find_similar_domain` (the deeper similarity check) and found the existing agent. But because it returned through the factory code path instead of the registry reuse path, the UI label said "candidate — first use" even though it was reusing an existing agent.

**Root cause:** Two code paths could return the same agent — the registry reuse path (correct labels) and the factory duplicate-detection path (wrong labels). They weren't aligned.

**Fix applied:** Labels now show actual state and use count from the database (e.g., "active — uses: 2"). After keyword expansion fix and DB reset, the registry path matches correctly on the first try.

**Detailed trace of what happened:**
```
First run of "mmWave frequency band planning":
1. find_by_keywords checked registry — SpectrumOptimizationAgent had 1 use,
   keywords were compounds: ["spectrum_optimization", "mmwave_dense_urban"]
2. Query words: {"mmwave", "frequency", "band", "planning"}
   Agent words: {"spectrum_optimization", "mmwave_dense_urban"} → overlap = 0
   (compound strings don't match individual words)
3. find_by_keywords returned None → fell to Factory
4. Factory called find_similar_domain → found overlap through word-level check
5. Factory returned existing agent (no duplicate) — but through factory code path
6. Label showed "candidate — first use" instead of "candidate — reuse"

Why it works after fix:
1. Keyword expansion breaks compounds: "mmwave_dense_urban" → {"mmwave", "dense", "urban"}
2. After 2 uses, agent promoted to active with expanded keywords in DB
3. find_by_keywords matches on first try → takes registry reuse path → correct label
```

**Production lesson:** When two code paths can produce the same outcome, ensure they produce identical user-visible output. Test the labels, not just the behavior.

### Lesson 4: SLM Domain Accuracy Gaps (Vendor-Specific and FR2/mmWave)

**What happened:** User asked for "Huawei mmWave config parameters." The SLM generated YAML config with several inaccuracies:
- n257 described as "26.5-27.5 GHz (QZSS L-band)" — QZSS L-band is satellite (~1.2 GHz), not mmWave. n257 is actually 26.5-29.5 GHz.
- `carrier_bandwidth_mhz: 4000` — 4 GHz is too high for a single carrier. Typical n257 is 100-400 MHz.
- `subcarrier_spacing_khz: 30` — wrong for FR2 mmWave. Should be 120 kHz per 3GPP.
- Parameter names are generic 3GPP, not Huawei-specific (real Huawei uses MML commands like `SET NRCELL`, `SET NRDUCELLBEAM`, parameter names like `BeamFormingMode`).

**Root cause:** The SLM (v4.1) was trained on general telecom data (49K rows + corrective patches). It has no vendor-specific training data (Huawei MML, Ericsson MOM, Nokia NetAct CLI). It also has weak coverage of FR2/mmWave specifics — most training data is FR1/LTE focused.

**What's NOT wrong:** The routing worked correctly (knowledge → config on follow-up), the response structure is good (YAML format, parameter grouping), and the general concepts are right (beamforming, SRS, handover margins).

**What IS wrong:** Specific parameter values and vendor terminology. This is an SLM training data gap, not a system architecture issue.

**How to fix (future):**
- Index vendor documentation in RAG (Huawei Product Documentation, Ericsson CPI, Nokia MOP)
- Add vendor-specific training data (MML commands, MOM parameters, CLI syntax)
- Add FR2/mmWave-specific training rows with correct SCS (120 kHz), bandwidth (100-400 MHz), beam management parameters

**Production lesson:** An 8B domain-trained SLM gives correct general telecom answers but should NOT be trusted for vendor-specific CLI commands or FR2 parameter values without vendor documentation in the RAG pipeline. Always flag vendor-specific outputs with a disclaimer until vendor data is indexed.

### Lesson 5: Context Loss Across Agent Switches (Nokia Follow-Up Bug)

**What happened:** User asked 3 questions in sequence:
1. "mmWave band planning?" → SpectrumOptimizationAgent (good answer)
2. "Huawei config for this?" → ConfigAgent (good — generated mmWave YAML)
3. "if the equipment is Nokia?" → GenericAgent (BAD — gave generic RRC counters, completely lost mmWave config context)

**Root cause:** This was a **bug, not a limitation**. The conversation memory was built for the Supervisor (to classify follow-ups) but never extended to the executing agents. Each agent only sees its own query in isolation. When the conversation hopped SpectrumAgent → ConfigAgent → GenericAgent, the third agent had no knowledge of the mmWave discussion.

**Why it was missed:** All test scenarios during development were single-turn queries. We never tested a multi-turn conversation that crosses agent boundaries until this real usage.

**Fix applied:**
- Short follow-ups (≤8 words like "if Nokia?") now inherit the previous agent's category instead of being reclassified. So "if Nokia?" inherits "config" from the Huawei question.
- Added follow-up indicators: "if the", "same for", "how about", "and for", "but for"
- The enriched query includes the previous answer (~500 chars) so the executing agent sees the context.

**What the fix covers:** Turns 2 and 3 of a conversation (follow-up sees last answer). Handles ~80% of real multi-turn conversations.

**What the fix does NOT cover:** Turn 4+ where the user needs context from 2+ prior answers (e.g., "compare the Huawei and Nokia configs" needs both turns 2 and 3). This requires a sliding context window of last 2-3 responses.

**Context window cost:** Enriching the query adds ~125 tokens from the last answer. SLM has 1024-token context window (set during training). This leaves ~575 tokens for the SLM to generate its answer — sufficient for structured responses. The cost is SLM context window space, not RAM or GPU. If this becomes limiting, options are: summarize prior turns, or retrain with `max_seq_length=2048`.

**Architectural lesson:** When a system evolves from single-agent to multi-agent, conversation context must evolve too. Memory designed for classification (Supervisor) is not the same as memory needed for execution (agents). Test multi-turn conversations that cross agent boundaries — single-turn tests will never catch this.

### Lesson 7: Factory Agent Fabricated Network Data (Compare Sites Incident)

**What happened:** User asked "Compare performance of SITE-METRO-001 and SITE-METRO-002." The Supervisor classified it as `general` (not `investigate`). No built-in agent matched. Factory created `SitePerformanceComparisonAgent` and the SLM fabricated specific numbers (2.8M sessions, 4.1 Gbps, 3.1s call setup) that came from training memory, not from real data.

**Root cause:** Two problems: (1) "Compare" was not in the Supervisor's investigate keywords, so it missed routing to Investigator. (2) The Factory has no guardrails — it creates agents and lets them answer from SLM memory without any data validation. Guardrails only existed on the Investigator.

**Fixes applied:**
1. Added "compare performance", "compare SITE-", "which site needs attention" to Supervisor's investigate classification
2. Added data-aware routing guardrail: before Factory runs, check if query mentions specific entities (SITE-, CELL-, compare, KPIs). If yes → force to Investigator.
3. Factory now only handles pure knowledge queries where SLM memory is appropriate

**Production lesson:** Any agent that produces quantitative claims (KPI values, throughput, session counts) MUST either have tool access to real data OR explicitly disclaim "these are estimated values from training patterns." Guardrails cannot be implemented on just one agent — every path that can produce data claims needs validation.

### Lesson 9: Synthesis Hallucination — Skills Without Tools Bypass Guardrails (Cell 4578203)

**What happened:** User asked "investigate cell id 4578203" (non-existent). Skills triage and diagnose correctly detected "Unknown cell_id" from tools and skipped SLM analysis. But the `recommend` skill has `tools: []` (it synthesizes from prior skills, doesn't call its own tools). The tool-level guardrail didn't apply to it. It ran the SLM which fabricated an entire S11/GTP-C diagnosis with specific commands, KPI values, and user counts — none of which existed.

**Root cause:** Guardrails only checked "did tools return data?" at the individual skill level. Skills without tools (like recommend) bypassed this check entirely. The synthesis step then combined all skill outputs — including "no data available" messages — and sent them to the SLM, which fabricated a plausible analysis.

**This is the THIRD time the same pattern appeared:**

| Incident | What slipped through | Level |
|---|---|---|
| Cell 331145 | Config endpoint returned template for fake ID | Tool level |
| Site 31203 | `_extract_params` returned empty, tools queried all cells | Parameter level |
| Cell 4578203 | `recommend` has no tools, synthesis ran on empty results | Synthesis level |

**Fix applied:** Added synthesis-level guardrail in `_investigate_with_skills()`. Before calling the SLM for final synthesis, checks: "Did ANY data-gathering skill actually get real data?" If all data skills returned "no_data" and only tool-less skills (recommend) completed, skip synthesis entirely and return guardrail response.

**Four-level guardrail architecture (all now implemented):**
```
Level 1: Data service    → validates entity IDs, returns errors for unknown
Level 2: Skill level     → each skill checks if its tools returned data
Level 3: Synthesis level → checks if ANY skill got real data before combining
Level 4: Agent level     → _assess_data_quality in legacy investigation path
```

**Production lesson:** Guardrails must exist at EVERY level where the SLM can be called. Every new code path (new skill, new agent, new synthesis step) is a potential guardrail bypass. When adding any component that invokes the SLM, ask: "What happens if all inputs are empty? Will the SLM fabricate?" If yes, add a check before the SLM call.

### Lesson 10: Data Service Returns Global Defaults for Any Cell

**What happened:** The config endpoint returned a global baseline parameter template for ANY cell_id, even non-existent ones. This meant the guardrail saw "config has data" and counted it as tools_with_data, scoring PARTIAL_DATA instead of NO_DATA.

**Fix applied:** Config endpoint validates cell_id before returning data. Guardrail also changed: config baseline without overrides no longer counts as "has data".

**Production lesson:** Default/template data is as dangerous as no data for an SLM — it gives the model something to hallucinate around. Only return data that's specific to the queried entity.

---

## Deployment Checklist

### Before First Deployment
- [ ] Create Dockerfiles for each service
- [ ] Set up docker-compose.yml
- [ ] Load llama-telco-v41 model into Ollama container
- [ ] Test all services communicate within Docker network
- [ ] Add API authentication (at minimum: API keys)
- [ ] Add request logging with correlation IDs
- [x] Apply input validation to alarm and config endpoints (done — cell 331145 fix)
- [x] Anti-hallucination guardrails in Investigator (done — _assess_data_quality)
- [x] Agent Factory keyword expansion and domain canonicalization (done)
- [ ] Test health checks and auto-restart
- [ ] Verify Agent Factory SQLite persists across container restarts
- [ ] Run systematic validation: 16 test cases across all endpoints with invalid inputs

### Before External Access
- [ ] Enable HTTPS (TLS termination via reverse proxy)
- [ ] Set up rate limiting
- [ ] Configure CORS if UI is served from different origin
- [ ] Audit all endpoints for input validation
- [ ] Set up log aggregation (ELK or CloudWatch)

### Before Production Traffic
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Define SLA metrics and alerting thresholds
- [ ] Run load test (concurrent users, response time under load)
- [ ] Set up backup for SQLite database
- [ ] Document runbook for common failure scenarios

### For Tier 2 Upgrade
- [ ] Deploy O-RAN SC sim-o1-interface Docker container
- [ ] Deploy ONAP NF Simulator VES Client
- [ ] Build TMF adapter layer (tmf_adapter.py)
- [ ] Refactor tool endpoints to TMF-compliant URLs
- [ ] Validate TMF response schemas against OpenAPI specs
- [ ] Test Investigator Agent with TMF-format data

### For Tier 3 Upgrade
- [ ] Set up OAI gNB in RF simulator mode
- [ ] Deploy FlexRIC with Python xApp SDK
- [ ] Build E2SM-KPM data adapter for Consilium tools
- [ ] Validate real-time KPM flow to agent system

---

## Rollback Plan

### Model Rollback
If v4.1 causes issues in production, roll back to v4 or v2:
```bash
# v4 rollback
ollama create llama-telco-v4 -f models/Modelfile-v4
# Update agents/telco_agents.py: model="llama-telco-v4"

# v2 rollback (last known stable before v4)
ollama create llama-telco-v2 -f models/Modelfile-llama-telco-v2
# Update agents/telco_agents.py: model="llama-telco-v2"
```

### Agent Factory Rollback
If dynamic agents cause issues:
```bash
# Disable all dynamic agents
python3 -c "
from agents.agent_registry import AgentRegistry
r = AgentRegistry()
for a in r.list_agents():
    r.disable_agent(a['id'])
print('All dynamic agents disabled')
"
# System falls back to built-in agents + GenericAgent
```

### Data Service Rollback
If the data service causes issues, tools fall back gracefully:
- `agents/tools.py` returns "Data service unavailable" message
- Investigator guardrail catches empty results → no hallucination

---

## Python Dependencies

```
# Core
fastapi
uvicorn
httpx
streamlit
pydantic

# ML/NLP (for benchmark scripts, not needed for production)
unsloth
torch
transformers
datasets

# RAG (if enabled)
llama-index
chromadb
sentence-transformers
```

---

## Model Artifacts

| File | Size | Purpose | Where Used |
|------|------|---------|-----------|
| `models/telco-v41-Q4_K_M.gguf` | 4.6 GB | Production model | Ollama |
| `models/telco-v41-adapter.zip` | 151 MB | LoRA adapter backup | For retraining |
| `models/telco-v4-Q4_K_M.gguf` | 4.6 GB | Previous model (rollback) | Ollama |
| `models/telco-v4-adapter.zip` | 158 MB | Previous adapter (rollback) | For retraining |
| `models/llama-telco-v2-adapter.zip` | 160 MB | Original base adapter | For retraining |
| `models/benchmark_llama-v41.json` | — | Benchmark results (84.1%) | Reference |
| `data/consilium.db` | — | Agent Factory SQLite | Runtime |

---

## Known Limitations (Current State)

These are inherent limitations of the current system that users and operators should be aware of.

| Limitation | Impact | Mitigation Path |
|------------|--------|-----------------|
| **No vendor-specific knowledge** | Config generation uses generic 3GPP parameter names, not Huawei MML/Ericsson MOM/Nokia CLI. Vendor CLI output may have wrong syntax | Index vendor documentation in RAG. Add vendor-specific training data |
| **FR2/mmWave parameter gaps** | SCS defaults to 30 kHz (FR1), should be 120 kHz for FR2. Bandwidth values may be unrealistic for mmWave | Add FR2-specific training rows with correct SCS, bandwidth, beam parameters |
| **8B model reasoning ceiling** | Complex multi-step correlations (3+ interacting faults) may produce shallow analysis | Accept for Tier 1. Consider 70B model or RAG augmentation for complex cases |
| **No real-time data** | Data service is synthetic with in-memory state. Resets on restart | Move to Tier 2 (O-RAN/ONAP Docker) or persistent storage |
| **Single-user design** | No concurrent session handling, no multi-tenant support | Add session IDs, user authentication, conversation isolation |
| **No feedback loop** | Agent Factory `success_signal` is always True — no user feedback mechanism | Add thumbs up/down to Streamlit UI, wire to `agent_runs.success_signal` |
| **Factory agents can fabricate data** | Factory-created agents answer from SLM memory only. If a data query reaches Factory instead of Investigator, it generates plausible but fake numbers | Data-aware routing guardrail (implemented): queries mentioning SITE-, CELL-, compare, KPIs are forced to Investigator before Factory runs. Factory only handles pure knowledge queries |
| **Skill chain selection is hardcoded (Tier 2)** | Skill planner uses keyword matching to select which skills to chain (e.g., "alarm" → 5 skills, "compare" → 4 skills, "config" → 3 skills). Individual skills are data-driven but chain selection is not. May not choose optimal chain for novel query types | Tier 3 (future): log investigation outcomes per chain. Feed successful patterns back to planner. Chain selection evolves from usage, replacing hardcoded keyword matching |
| **Only Investigator has external data** | Incident, Config, Generic, and Factory agents answer purely from SLM training memory. No live data, no RAG, no tool calls. Same answer regardless of actual network state | Extend tool access to IncidentAgent (query KPIs before diagnosing) and ConfigAgent (query current config before generating). Enable RAG for KnowledgeAgent |
| **RAG disabled by default** | Knowledge Agent falls to Generic/Factory without RAG. 3GPP spec references may be fabricated because the SLM was NOT trained on ChromaDB data — they are separate systems. SLM knows how to reason (from training), RAG knows what specs say (from indexing) | Enable RAG with `skip_rag=False` in api_server.py. ChromaDB is built (64 GB, 3.5M vectors at `rag/vector_db/chroma_3gpp/`). Adds ~2-3 GB memory + startup time |
| **Tool-calling is prompt-based** | SLM generates free-form JSON for tool calls. Malformed JSON and wrong params still possible | Move to Llama 3.1 native function calling (Phase 2.2 in this playbook) |
| **Ollama model name hardcoded** | Model name `llama-telco-v41` is hardcoded in `telco_agents.py` | Move to environment variable for easier model swaps |
| **Multi-turn context limited to last answer** | Follow-ups see only the previous response. "Compare both configs" after 2 config queries will fail — needs context from 2 prior answers | Pass sliding window of last 2-3 responses. Cost: ~200-300 extra tokens from 1024 context window |
| **1024 token context window** | Trained with `max_seq_length=1024`. Limits how much conversation context + query + answer fits | Sufficient for current use. Retrain with 2048 if multi-turn context becomes critical |
