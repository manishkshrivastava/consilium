# Agent Phase 3 — Options Analysis & 7B Dependency
## Date: 2026-03-19

---

## 1. Phase 3 Scope (Original Plan)

| Item | Description |
|------|-------------|
| Agent Factory | Auto-creates and saves new agent configs for unknown domains |
| Dynamic instructions | Supervisor writes custom instructions for Generic Agent |
| External tools | Network APIs, ticket system, config validator, KPI calculator |
| FastAPI endpoint | REST API for external access to agent system |
| Streamlit UI | Visual chat interface for demos and interactive use |
| Feedback loop | User ratings improve routing accuracy |

---

## 2. 7B Dependency Analysis

### Option A: Build FastAPI + Streamlit UI ✅ SELECTED

| Aspect | Detail |
|--------|--------|
| **What** | Web-based chat interface + REST API wrapping the agent system |
| **Depends on 7B?** | **No** — UI is model-agnostic. Works with current 1.5B+7B setup. When FT-7B arrives, just swap the model — UI stays the same |
| **Effort** | ~2-3 hours |
| **Value** | High — tangible, demo-able deliverable. Makes the system accessible beyond terminal |
| **Risk** | None — pure frontend/API work |

**Why selected:** Delivers immediate value regardless of model quality. Can demo the agentic architecture (routing, chaining, memory) visually even if SLM answers aren't perfect. When 7B arrives, the UI automatically benefits.

**Deliverables:**
- FastAPI server with `/query`, `/memory`, `/clear` endpoints
- Streamlit chat UI with agent indicators, source display, chain visualization
- Can be shared with colleagues for feedback

### Option B: Build External Tool Framework ⬜ NEXT PRIORITY

| Aspect | Detail |
|--------|--------|
| **What** | Define tool interfaces + mock implementations (ticket system, config validator, KPI calculator) |
| **Depends on 7B?** | **Partially** — tool invocation logic doesn't need 7B, but meaningful tool USE requires the agent to reason about when to call which tool |
| **Effort** | ~3-4 hours |
| **Value** | Medium — prepares infrastructure for real integrations, but mock tools aren't immediately useful |
| **Risk** | Low — but tools without a good reasoning model produce random tool calls |

**When to do:** After FT-7B is imported and validated. The 7B model will make better decisions about when and how to use tools.

**Planned tools:**
| Tool | Description | Mock → Real |
|------|-------------|-------------|
| TicketSystem | Create/update incident tickets | Mock JSON file → ServiceNow/Jira API |
| ConfigValidator | Check generated YAML against schema | Mock always-pass → JSON schema validation |
| KPICalculator | Erlang B, capacity formulas | Mock → actual calculations |
| NetworkAPI | Query live alarms, KPIs, topology | Mock → real NMS/OSS API |

### Option C: Wait for Colab 7B, Then Full Phase 3 ⬜ BLOCKED

| Aspect | Detail |
|--------|--------|
| **What** | Import FT-7B → run checklist → then build Agent Factory + dynamic instructions + feedback loop |
| **Depends on 7B?** | **Yes — fully blocked** |
| **Effort** | ~1 day after 7B arrives |
| **Value** | Very High — Agent Factory and dynamic instructions need quality reasoning to work properly |
| **Risk** | Colab may timeout, training may need multiple sessions |

**What's blocked:**
| Feature | Why It Needs 7B |
|---------|-----------------|
| **Agent Factory** | Creates new agents by writing instructions — 1.5B writes broken instructions → broken agents |
| **Dynamic instructions** | Supervisor customizes Generic Agent per query — needs reasoning to write good instructions |
| **Feedback loop** | Rating responses only useful if responses are sometimes good — with 1.5B, almost all incident responses are unreliable |

**When to do:** After FT-7B is imported, validated against 7B_TESTING_CHECKLIST.md, and benchmarked.

---

## 3. Execution Order

```
NOW        → Option A: FastAPI + Streamlit UI (no 7B dependency)

WHEN 7B    → Import FT-7B from Colab
ARRIVES      Run 7B_TESTING_CHECKLIST.md
             Re-benchmark (100 questions)

AFTER 7B   → Option B: External tool framework (with good reasoning model)
VALIDATED    Option C: Agent Factory + dynamic instructions + feedback loop
```

---

## 4. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-19 | Option A first (UI) | No 7B dependency, immediate demo value |
| 2026-03-19 | Option B after 7B | Tools need reasoning model to invoke correctly |
| 2026-03-19 | Option C last | Agent Factory needs quality model to create useful agents |

---

## 5. Current Status with Phase 3 Context

```
✅ Step 1:   Data Preparation (38K examples, 15K 3GPP docs)
✅ Step 2:   Fine-tuning v1→v2→v3 (val loss 2.5→0.44)
✅ Step 2.5: Ollama + Local Chat
✅ Step 4:   Operational Benchmark DONE (100 Qs: v3=61.4%, 7B=76.1%, Agents=83.4%)
✅ Step 5:   RAG Pipeline (3.5M vectors, retrieval works)
✅ Step 5.5: Training Data Improvement (47 scenarios, 25 configs, 6 domains)
✅ Step 6:   Agents Phase 1 (4 agents + Supervisor, routing 100%)
✅ Step 6:   Agents Phase 2 (conversation memory, multi-agent chaining, improved routing)
⚠️  BLOCKER: SLM 1.5B content quality unreliable (~30% accuracy, hallucination)
⚠️  WARNING: RAG + 1.5B doesn't synthesize — copies tables
⚠️  WARNING: Follow-up detection works but imperfect
🔄 Step 2b:  7B Training on Google Colab (in progress, ETA overnight)
🔄 Step 7:   FastAPI + Streamlit UI (Option A — IN PROGRESS)
⬜ Step 6:   Phase 3 Option B — External tools (after 7B validated)
⬜ Step 6:   Phase 3 Option C — Agent Factory + feedback (after 7B validated)
📋 WAITING: 7B Testing Checklist ready (7B_TESTING_CHECKLIST.md)
```
