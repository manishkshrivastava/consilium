# Consilium vs GSMA Whitepaper — Alignment Analysis
*Comparing Consilium (Network Intelligence Platform) against GSMA 6G Community Whitepaper: "AI Agents and Agentic Protocols for Telecom Networks" (February 2026)*

*Contributors: Deutsche Telekom, BT, Vodafone, Huawei, IBM, Nokia, Khalifa University, GSMA*

---

## Executive Summary

The GSMA whitepaper defines the **industry vision for telecom AI agents in the 6G era (2030+)**. Consilium is a **2026 prototype** that demonstrates many of the core concepts at a smaller scale. Our architecture is fundamentally aligned with the GSMA direction — multi-agent, domain-specific LLM, RAG-augmented, tool-using agents. The gaps are in production-readiness: governance, real-time constraints, multi-vendor interoperability, and safety guardrails.

**Key validation from the paper:**
- *"56% of telecom operators are already using AI agents in production"* — Consilium fits this wave
- *"Domain relevance of data frequently can outweigh sheer dataset size"* (Section 6.2.1.2) — We proved this: 34K relevant data (79.3%) beat 66K academic data (17.8%)
- *"Parameter-efficient fine-tuning strategies provide practical alternatives to full retraining"* (Section 6.2.2.2) — Our QLoRA approach is exactly this
- *"Constrained, well-managed agents frequently outperform theoretically superior but poorly governed systems"* (Section 6.2.3) — Validates focusing on agent system over model scaling

---

## 1. Where Consilium is ALIGNED with GSMA Vision

### 1.1 Multi-Agent Architecture
**GSMA says:** *"Telecom use cases usually don't involve a single autonomous agent acting in isolation, but rather require multiple agents with specific roles, e.g., monitoring, reasoning, decision-making, and execution, to coordinate across domains."* (Section 4)

**Consilium has:**
- 5 specialized agents: Incident Diagnosis, Config Generation, Network Healing, Optimization, Knowledge Base
- Supervisor agent for routing and coordination
- 100% routing accuracy on benchmark

### 1.2 Domain-Specific LLM Fine-Tuning
**GSMA says:** *"Training or fine-tuning models to be telecom-aware and systematically testing them on representative tasks are essential."* (Section 3) *"Lightweight adaptation techniques frequently outperform monolithic retraining."* (Section 6.2.2.2)

**Consilium has:**
- Qwen 2.5-7B fine-tuned with QLoRA (0.53% parameters)
- 34K domain-specific training examples
- Benchmark: 79.3% on 100 operational questions
- Proved 1.5B model insufficient (61.4%), 7B is the sweet spot

### 1.3 Intent-Based Interaction
**GSMA says:** *"Agents must interact with users, operators, and other agents through high-level intents, rather than fixed instructions. Intents describe desired outcomes or goals."* (Section 6.1.3)

**Consilium has:**
- Natural language input: "eNodeB CPU at 97%, what should I do?"
- Supervisor interprets intent → routes to correct agent
- Agent decomposes into investigation steps

### 1.4 Tool Invocation
**GSMA says:** *"A key capability of agents is autonomous tool invocation and use. In telecom environments, tools include management APIs, AI services, and third-party applications."* (Section 6.1.8)

**Consilium has:**
- InvestigatorAgent with KPI Query, Alarm Correlation, Config Audit tools
- 3-tool planning guaranteed for every investigation
- Currently mock tools (real NMS/OSS API integration pending)

### 1.5 Knowledge Retrieval (RAG)
**GSMA says:** *"Agents must access internal and external knowledge sources dynamically, including network data, logs, policies, and historical records."* (Section 6.1.9)

**Consilium has:**
- ChromaDB vector store with 3.5M vectors from 3GPP specifications
- RAG integrated into InvestigatorAgent
- Agent cites specific 3GPP spec sections in responses

### 1.6 Data Relevance Over Volume
**GSMA says:** *"Domain relevance of data frequently can outweigh sheer dataset size or model scale. Targeted and semantically aligned datasets may yield higher task performance than indiscriminate large-scale corpora."* (Section 6.2.1.2)

**Consilium validated this empirically:**
- v1 (34K domain-relevant data): **79.3%** benchmark score
- v4 (66K clean public academic data): **17.8%** benchmark score
- Operational NOC scenarios > academic 3GPP Q&A

### 1.7 On-Premise Deployment
**GSMA says:** *"Hosting models locally addresses privacy, latency, and customization requirements."* (Section 6.2.3.2)

**Consilium has:**
- Model runs locally via Ollama on MacBook M4 Pro (24GB RAM)
- 4.5 GB quantized model (Q4_K_M)
- ~9 seconds per response, no cloud dependency
- Full data sovereignty — no external API calls for inference

---

## 2. Where Consilium is PARTIALLY Aligned

### 2.1 Cross-Domain Coordination
**GSMA says:** *"Decisions made in one domain usually will have cascading effects in others. For example, mobility management impacting transport congestion."* (Section 2.2)

**Consilium status:** Supervisor routes to correct domain agent, but agents don't collaborate on cross-domain issues. A RAN throughput problem caused by transport congestion would require manual correlation.

**Gap:** Need cross-agent communication and cascading investigation workflows.

### 2.2 Continuous Evaluation
**GSMA says:** *"Agent systems necessitate continuous behavioural evaluation, extending beyond traditional accuracy metrics to include: task completion success rates, policy and safety compliance, hallucination or reasoning failure frequency."* (Section 6.2.2.3)

**Consilium status:** 100-question benchmark exists but is run manually, one-time.

**Gap:** Need automated, continuous evaluation pipeline with drift detection.

### 2.3 Human-in-the-Loop
**GSMA says:** *"Human-in-the-loop mechanisms are an integral part of telecom planning, enabling escalation and approval when decisions exceed predefined autonomy limits."* (Section 8)

**Consilium status:** UI shows recommendations for human review.

**Gap:** No formal escalation workflow, no autonomy limits, no approval gates before actions.

### 2.4 Model Lifecycle Management
**GSMA says:** *"Robust version control, explicit dependency management and clear tracking of model provenance become essential."* (Section 6.2.2.1)

**Consilium status:** We've iterated v1→v4 with clear tracking of what changed and why.

**Gap:** No automated pipeline for retraining, versioning, A/B testing, or rollback.

### 2.5 Structured Action Vocabulary
**GSMA says:** *"Telecom agents may operate over a constrained and well-defined set of actions with explicit semantics, preconditions, and effects."* (Section 7)

**Consilium status:** TeleYAML for config generation provides structured output.

**Gap:** Other agents output free-text recommendations without formal action definitions.

---

## 3. Where Consilium is NOT Aligned (Significant Gaps)

### 3.1 QoS-Aware Agent Communication
**GSMA requirement:** *"Telecom-ready agentic systems must support QoS-aware agent communication, where latency, reliability, and resource allocation can be managed on a per-message basis."* (Section 6.1.2)

**Consilium gap:** Agents communicate via Python function calls within a single process. No network-level communication, no QoS differentiation.

**Relevance:** Low for current prototype. Critical for production deployment.

### 3.2 Agent Governance & Discovery
**GSMA requirement:** *"Agentic systems must support agent registration, update, discovery, and de-registration through centralized or distributed authorities."* (Section 6.1.4)

**Consilium gap:** Agents are hardcoded in the supervisor. No dynamic registration, discovery, or trust mechanism.

**Relevance:** Medium — needed when scaling beyond single NOC.

### 3.3 Semantic-Aware Agentic Protocols
**GSMA requirement:** *"Semantic-aware protocols aim to bridge this gap by integrating protocol-level interaction with telecom-native semantic models."* (Section 7)

**Consilium gap:** No telecom-specific agentic protocol. Uses standard LangGraph orchestration.

**Relevance:** Low for prototype. This is an industry-wide gap — no one has implemented this yet. The paper positions it as a future standardization requirement.

### 3.4 Multi-Vendor Interoperability
**GSMA requirement:** *"Agents must interact across heterogeneous systems while preserving vendor neutrality and operational independence."* (Section 5)

**Consilium gap:** Single-vendor system (one model, one framework, one deployment).

**Relevance:** Medium — relevant when integrating with real multi-vendor NOC.

### 3.5 Federated Multi-Agent Coordination
**GSMA requirement:** *"Specialized agents operate under partial knowledge and local constraints, making coordination essential."* (Section 8)

**Consilium gap:** All agents are co-located in one process with shared context.

**Relevance:** Low for prototype. Critical for production multi-site deployment.

### 3.6 Real-Time Constraints
**GSMA requirement:** *"Some decisions require millisecond responsiveness (e.g., radio control and fault mitigation)."* (Section 8)

**Consilium gap:** 8-9 second response time per query. LLM-based agents are inherently slow for real-time radio control.

**Relevance:** The paper acknowledges this requires different approaches for different time scales. Consilium targets the "minutes to hours" planning scale, not millisecond radio control.

### 3.7 Safety Guardrails
**GSMA requirement:** *"Constraints imposed by spectrum regulations, safety margins, security requirements, and strict compliance to standards cannot be violated without severe operational or legal consequences."* (Section 8)

**Consilium gap:** No formal constraint checking before recommendations. Agent could suggest a config that violates regulatory limits.

**Relevance:** High — critical for any production deployment.

---

## 4. Architectural Comparison

```
GSMA Vision (6G, 2030):
┌─────────────────────────────────────────────┐
│  Distributed Multi-Agent System              │
│  ├── Agents across RAN, Core, Transport     │
│  ├── Federated across operators/vendors     │
│  ├── Semantic-aware agentic protocols       │
│  ├── QoS-differentiated communication       │
│  ├── Real-time + planning timescales        │
│  ├── Formal governance & trust              │
│  ├── Constraint-aware autonomous actions    │
│  └── Continuous evaluation & lifecycle mgmt │
└─────────────────────────────────────────────┘

Consilium (Prototype, 2026):
┌─────────────────────────────────────────────┐
│  Local Multi-Agent System                    │
│  ├── 5 specialized agents + Supervisor      │
│  ├── Single deployment (one NOC)            │
│  ├── LangGraph orchestration                │
│  ├── Python function call communication     │
│  ├── Advisory (minutes) timescale           │
│  ├── No formal governance                   │
│  ├── Recommendations (not autonomous)       │
│  └── Manual benchmark evaluation            │
└─────────────────────────────────────────────┘

Shared Foundation:
├── Domain-specific fine-tuned LLM (QLoRA)
├── Multi-agent with specialized roles
├── RAG for knowledge retrieval
├── Tool invocation for network data
├── Intent-based natural language interaction
└── On-premise/edge deployment capable
```

---

## 5. Prioritized Roadmap Based on GSMA Alignment

### Phase 1: Quick Wins (align with paper's emphasis on systems engineering)
1. **Connect real NMS/OSS APIs** — Replace mock tools with live network data
2. **Add safety guardrails** — Constraint validation before config recommendations
3. **Improve cross-domain reasoning** — Enable agents to trigger cross-domain investigations

### Phase 2: Production Readiness
4. **Human-in-the-loop workflows** — Approval gates for high-impact actions
5. **Continuous evaluation pipeline** — Automated benchmarking with drift detection
6. **Model lifecycle management** — Version control, A/B testing, rollback

### Phase 3: Scale (toward GSMA vision)
7. **Agent governance** — Registration, discovery, trust mechanisms
8. **Multi-vendor integration** — Standardized interfaces for heterogeneous NMS
9. **Structured action vocabulary** — Formal action definitions with preconditions/effects

### Not Needed Yet
- Semantic-aware agentic protocols (industry-wide gap, future standardization)
- QoS-aware agent communication (needed at production scale, not prototype)
- Federated multi-site coordination (future multi-operator scenario)

---

## 6. Key Quotes from the Paper That Validate Consilium

> *"Constrained, well-managed agents frequently outperform theoretically superior but poorly governed systems."* — Validates our focus on agent quality over model size

> *"Domain relevance of data frequently can outweigh sheer dataset size or model scale."* — We proved this: 34K relevant > 66K academic

> *"Lightweight adaptation techniques frequently outperform monolithic retraining due to reduced latency and improved maintainability."* — Our QLoRA approach is exactly this

> *"Even large language models or large telecom models, when used in isolation, lack the ability to plan, act, and adapt over extended operational lifecycles."* — This is why we built the agent system, not just the model

> *"Agentic AI success is therefore primarily an exercise in AI systems engineering rather than only model scaling."* — Our next focus should be the agent system, not more training iterations

---

*Analysis date: 2026-03-25*
*Whitepaper: GSMA 6G Community, February 2026*
*Consilium version: v1 model (79.3%), Phase 6 agents*
