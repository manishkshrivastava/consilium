# Agent Phase 2 — Changes and Modifications Log
## Date: 2026-03-19

---

## 1. Overview

Phase 2 adds **conversation memory** and **multi-agent chaining** to the agentic framework built in Phase 1. It also fixes critical routing issues discovered during Phase 1 testing.

**Files modified:**
- `agents/telco_agents.py` — Core framework (5 major changes)
- `agents/run_agents.py` — Interactive CLI (rewritten for Phase 2)

---

## 2. Change 1: Conversation Memory (NEW)

### What was added
`ConversationMemory` class in `telco_agents.py`

### Why
Phase 1 had no conversation context. Each query was independent. Follow-up questions like "what are the resolution steps for this?" had no idea what "this" referred to.

### How it works
```
User: "VoLTE failure 12% in South region"
  → Stored in memory as {role: "user", content: "VoLTE failure..."}

Assistant: "Severity: Critical, Domain: IMS..."
  → Stored as {role: "assistant", content: "...", agent: "IncidentAgent", category: "incident"}

User: "what are the resolution steps for this?"
  → Memory provides last 3 turns as context to Supervisor
  → Follow-up detected → query enriched with prior VoLTE answer
  → Resolution steps now reference VoLTE specifically
```

### Technical details
- Stores last 10 turns (configurable via `max_turns`)
- Each entry has: role, content, agent name, category
- `get_context_summary()` returns last 3 turns as text for Supervisor
- `get_last_response()` returns the most recent assistant response
- `/clear` command resets memory, `/memory` shows history

### Limitations
- Memory is in-process only — lost when CLI exits
- No long-term persistence (would need database for production)
- Context summary is truncated to keep Supervisor prompts short

---

## 3. Change 2: Multi-Agent Chaining (NEW)

### What was added
`plan_agents()` method in `SupervisorAgent` + chaining logic in `AgentOrchestrator.run()`

### Why
Complex queries like "Diagnose high CPU on ENB-5432 AND suggest config changes" need multiple agents working in sequence — first IncidentAgent diagnoses, then ConfigAgent generates a fix.

### How it works
```
User: "Diagnose high CPU and suggest config changes"
  → Supervisor detects multi-step: ["incident", "config"]
  → Step 1: IncidentAgent diagnoses → output stored
  → Step 2: ConfigAgent receives diagnosis as context → generates config
  → Combined output returned to user
```

### Smart triggering
Multi-agent planning only activates when query contains:
- " and " (e.g., "diagnose AND configure")
- " then " (e.g., "first check THEN fix")
- Both "diagnose" and "config" keywords
- Both "explain" and "generate" keywords

Simple queries bypass planning entirely — classification goes directly to routing.

### Technical details
- `plan_agents()` asks 7B Supervisor to return a JSON array: `["incident", "config"]`
- Each agent in the chain receives the previous agent's output as context
- Final response combines all agent outputs with `---` separator
- Agent names shown as "Chain: IncidentAgent → ConfigAgent"

### Test result
```
Query: "Diagnose high CPU on ENB-5432 and suggest config changes"
Plan:  ["incident", "config"]  ✅
Chain: IncidentAgent → ConfigAgent ✅
```

### Limitations
- Config generation quality still limited by 1.5B SLM (hallucination in chained output)
- Maximum 3 agents in a chain (practical limit)
- No error recovery — if first agent fails, chain continues with bad context

---

## 4. Change 3: Improved Supervisor Classification (FIXED)

### What was changed
`CLASSIFICATION_PROMPT` in `SupervisorAgent` rewritten with explicit rules

### Why
Phase 1 testing revealed misclassification:
- "whats the domain where IMS belongs to?" → classified as "incident" (wrong, should be "knowledge")
- "can you provide the network topology?" → classified as "incident" (wrong, should be "knowledge")
- "what are the resolution steps for this?" → no follow-up detection

### Before (Phase 1)
```
Categories:
- incident : alarms, faults, outages, degradation, troubleshooting
- knowledge : 3GPP specs, standards, protocol details, architecture questions
- config : network configuration, parameter changes, CLI/YAML commands
- general : greetings, off-topic, general telecom chat
```

### After (Phase 2)
```
Categories:
- incident : active alarms, current faults, live outages, "failure rate is X%"
- knowledge : explaining concepts, architecture, topology, "what is", "how does",
              "what nodes", "what are the components"
- config : generate configuration, YAML commands, "configure", "set up"
- general : greetings, off-topic, opinions
- followup : references previous answer ("this", "elaborate", "more details")

IMPORTANT RULES:
- "what nodes" or "what topology" → KNOWLEDGE, not incident
- "elaborate" or "tell me more" → FOLLOWUP
- Only "incident" if there is a CURRENT active alarm being reported
```

### Impact

| Query | Phase 1 | Phase 2 |
|-------|---------|---------|
| "whats the domain where IMS belongs to?" | incident ❌ | **knowledge** ✅ |
| "can you provide the network topology?" | incident ❌ | **knowledge** ✅ |
| "What is the N4 interface?" | knowledge ✅ | knowledge ✅ |
| "VoLTE failure rate 10%" | incident ✅ | incident ✅ |
| "Generate VoNR QoS config" | config ✅ | config ✅ |
| "what are the resolution steps for this?" | incident ❌ | **followup/enriched** ✅ |

---

## 5. Change 4: Fixed Plan vs Classification Conflict (FIXED)

### What was changed
Routing logic in `AgentOrchestrator.run()` — plan no longer overrides classification

### Why
Critical bug: `plan_agents()` was called for EVERY query, and its result overrode the Supervisor's classification. This caused:
```
Supervisor: classified as "knowledge" ✅
plan_agents: returned ["incident"] ❌
Routing: used plan → sent to IncidentAgent ❌
```

### Before (Phase 1)
```python
# Called for EVERY query — plan overrides classification
plan = self.supervisor.plan_agents(query, context)
if len(plan) <= 1:
    answer = self._run_single_agent(plan[0], query)  # Uses PLAN, not CATEGORY
```

### After (Phase 2)
```python
# Only plan for complex queries with "and"/"then"
if needs_planning:
    plan = self.supervisor.plan_agents(query, context)
else:
    plan = [category]  # Use classification directly

if len(plan) <= 1:
    answer = self._run_single_agent(category, query)  # Uses CATEGORY
```

### Impact
- Simple queries: Classification → direct routing (no planning overhead)
- Complex queries ("diagnose AND configure"): Planning → multi-agent chain
- No more plan overriding correct classification

---

## 6. Change 5: Follow-up Detection (NEW)

### What was added
Keyword-based follow-up detection in `AgentOrchestrator.run()` before Supervisor classification

### Why
The Supervisor often couldn't detect follow-up questions. "What are the resolution steps for this?" was classified as "incident" instead of being recognized as a follow-up to the previous VoLTE discussion.

### How it works
```python
followup_indicators = [
    "this", "that", "the above", "elaborate", "more detail",
    "tell me more", "what about", "can you explain",
    "resolution steps for this", "how to fix this", "what nodes",
    "contextualise", "my network", "for this issue", "regarding this",
    "based on that", "following up", "as mentioned",
]

# If conversation has history AND query contains followup indicator:
# → Enrich query with previous answer as context
# → Then classify the enriched query
```

### Test result
```
Query 1: "RACH failure rate exceeds 15% on cell CELL-45678"
  → IncidentAgent: PRACH, interference, coverage causes ✅

Query 2: "what are the resolution steps for this?"
  → Follow-up detected ✅
  → Enriched with RACH context ✅
  → Response mentions PRACH-specific resolution ✅ (before: generic S1/Core)
```

### Limitations
- Keyword matching is simple — can false-positive on queries like "explain this protocol"
- Enrichment truncates prior answer to 500 chars — may lose detail
- Supervisor still sometimes re-classifies instead of using "followup" category

---

## 7. Change 6: Updated Interactive CLI (REWRITTEN)

### What was changed
`agents/run_agents.py` — fully rewritten for Phase 2

### New commands

| Command | What It Does |
|---------|-------------|
| `/clear` | Clears conversation memory |
| `/memory` | Shows conversation history (entries, roles, agents) |
| `/chain` | Shows example multi-agent chain queries |
| `/agents` | Shows registered agents (updated with Phase 2 features) |
| `/quit` | Exit |

### New UI elements

| Element | What It Shows |
|---------|-------------|
| `Memory: X entries` | Number of conversation turns stored |
| `Chain: incident → config` | Multi-agent execution sequence |
| `(Follow-up detected)` | When follow-up keyword matching triggered |
| `(Conversation context was provided)` | When memory context sent to Supervisor |

---

## 8. Summary: Before vs After

| Feature | Phase 1 | Phase 2 |
|---------|---------|---------|
| Conversation memory | ❌ None | ✅ Last 10 turns |
| Follow-up questions | ❌ Treated as new queries | ✅ Detected + enriched with context |
| Multi-agent chaining | ❌ Single agent only | ✅ Chain 2+ agents sequentially |
| Supervisor classification | Basic 4 categories | Improved 5 categories + rules |
| Plan vs classification | Plan overrides classification (bug) | Classification is primary, plan only for complex |
| CLI commands | /quit, /agents | + /clear, /memory, /chain |

---

## 9. Known Issues Remaining

| Issue | Root Cause | Fix Requires |
|-------|-----------|-------------|
| 1.5B SLM content quality | Model too small for accurate reasoning | Fine-tuned 7B from Colab |
| Domain misclassification by SLM | 1.5B can't separate RAN/Core/IMS/Transport | Fine-tuned 7B |
| Hallucinated concepts (WAP, LBBW) | 1.5B invents plausible-sounding terms | Fine-tuned 7B |
| Config hallucination in chains | 1.5B can't generate config from diagnosis context | Fine-tuned 7B |
| Follow-up sometimes misroutes | Keyword matching is imperfect | Better Supervisor or 7B training |
| RAG embedding conflict | ChromaDB collection created with different embedding function | Minor code fix needed |
| Memory not persisted | In-process only, lost on exit | Database storage (Phase 3) |

---

## 10. Files Changed

| File | Lines Changed | Summary |
|------|-------------|---------|
| `agents/telco_agents.py` | +120 new, ~40 modified | ConversationMemory class, plan_agents(), improved Supervisor prompt, fixed routing, follow-up detection |
| `agents/run_agents.py` | Rewritten (127 lines) | Phase 2 UI with memory/chain/follow-up indicators |

---

## 11. Testing Commands

```bash
# Start the Phase 2 CLI
cd "Library/CloudStorage/OneDrive-Personal/Training SLM"
source .venv/bin/activate
TOKENIZERS_PARALLELISM=false python agents/run_agents.py --skip-rag

# Test conversation memory
> VoLTE failure 12% in South region
> what are the resolution steps for this?

# Test multi-agent chaining
> Diagnose high CPU on ENB-5432 and suggest config changes

# Test improved routing
> whats the domain where IMS belongs to?
> What is the N4 interface in 5G?

# View memory
> /memory

# Clear and start fresh
> /clear
```
