# CONSILIUM — Policy Framework & Governance for Agentic Telecom AI
### Last Updated: 2026-04-09

---

## Why Policy Matters

Consilium has working agents, tools, and guardrails. But as it moves from L1-L2 (assisted) toward L3 (conditional autonomy) with closed-loop operations, the missing piece is a **formal policy framework** that controls, constrains, audits, and escalates agent decisions.

The industry is converging on this: **capability without governance is a demo, not a product.**

---

## What "Policy" Means in Agentic Telecom AI

Policy is not one thing — it's 7 distinct layers, each serving a different governance function:

### 1. Intent Policies (What the Operator WANTS)

High-level declarations of desired outcomes without specifying implementation.

**Examples:**
- "Maintain DL throughput above 50 Mbps on Metro sites during business hours"
- "Prioritize URLLC traffic over eMBB when congestion detected"
- "Keep ERAB setup success rate above 99% on all Metro sites"

**How it works:** An Intent Management Function (IMF) translates human-readable intent into machine-actionable policies. The operator defines WHAT (goals, constraints); the system determines HOW.

**Standards:** TM Forum TR290 (Intent Common Model), IG1253 (Intent in AN), 3GPP SA5 Intent-Driven Management, ETSI ENI GR ENI 008.

**Consilium status:** Not built. Users ask questions and get answers. No persistent intent monitoring.

### 2. Constraint Policies (What the Agent CANNOT Do)

Hard boundaries on agent behavior — actions forbidden regardless of context.

**Examples:**
- "Never modify core network routing tables without human approval"
- "Never apply configuration changes to more than 5 cells simultaneously"
- "Never reduce QoS below SLA minimum during optimization"
- "Agent Factory cannot create agents for security-domain operations"

**Industry practice:** AWS Bedrock AgentCore uses Cedar policy language for deterministic constraint enforcement OUTSIDE the agent's reasoning loop. The policy intercepts tool calls at the gateway before execution.

**Consilium status:** Only data-aware routing guardrail exists. No formal constraint policies.

### 3. Escalation Policies (When to Hand Off to Human)

Rules governing when autonomous operation must yield to human decision-making.

**Examples:**
- "If confidence below 70%, present recommendation but require human approval"
- "If action affects revenue-generating service, escalate to NOC manager"
- "If multiple agents disagree on root cause, present both analyses to human"
- "If alarm severity is Critical and affects >100 users, notify duty engineer"

**Industry practice:**
- Ericsson: Optional human-in-the-loop for early technology adopters
- Nokia: Essential human intervention with approval points until models achieve maturity
- TM Forum L3: Human in oversight role, not decision loop for routine operations

**Consilium status:** Not built. Every query gets a response regardless of confidence or severity.

### 4. Scope Boundary Policies (Which Domains/Cells/Slices an Agent Can Act On)

Geographic, functional, or organizational boundaries limiting an agent's operational domain.

**Examples:**
- "Investigator Agent can only query sites in Region-South"
- "Config Agent can generate configs for RAN only, not Core"
- "Agent Factory agents cannot be created for network-slice-specific operations"
- "Optimization scope limited to non-revenue cells during off-peak hours"

**Industry practice:**
- Ericsson: Agents reside within domains and layers with clear interfaces and authorizations
- O-RAN: A1 policies scoped to specific cells, slices, or UE groups
- Nokia: Clear RACI defines which actions agents may take autonomously vs. requiring approval

**Consilium status:** Not built. Any agent can be asked about any site, any domain, any cell.

### 5. Confidence Threshold Policies (Minimum Confidence Before Autonomous Action)

Quantitative thresholds that gate autonomous execution.

**Examples:**
- Confidence > 90% → execute autonomously
- Confidence 70-90% → execute but log for review
- Confidence < 70% → recommend only, human must approve
- Confidence < 40% → refuse to answer, escalate

**Industry practice:**
- Nokia: Sophisticated mechanisms to monitor accuracy and confidence against calibrated thresholds
- Pipeline checkpoints: Each agent attaches confidence score to output; below threshold, pipeline pauses
- Telecom BPO case study: 94% reduction in hallucination-related escalations through graduated fallback mechanisms

**Calibration methods:** Statistical (variance/bootstrapping), reinforcement learning, LLM self-evaluation, historical accuracy correlation.

**Consilium status:** Not built. 4-level guardrail checks data presence (FULL/PARTIAL/NO_DATA) but does not score confidence of the analysis itself.

### 6. Rollback Policies (How to Undo Agent Actions)

Mechanisms to reverse actions when outcomes are undesirable.

**Examples:**
- "If KPI degrades by >5% within 30 minutes of config change, auto-rollback"
- "Maintain previous-3-versions of every configuration for instant rollback"
- "Saga pattern: multi-step actions have compensating transactions for each step"

**Industry practice:**
- Nokia: Digital twins simulate predicted outcomes before deployment
- Microsoft AGT: Saga orchestration for multi-step transactions + kill switch
- AWS AgentCore: Config-driven deployment, canary rollouts, rollback one command away

**Consilium status:** Not built. Currently read-only (generates recommendations, doesn't execute). Rollback becomes critical at L3.

### 7. Audit/Explainability Policies

Requirements for logging, tracing, and explaining every agent decision.

**Industry audit properties** (articulated by Nokia Bell Labs as "Glass Box", but aligned with broader ETSI ENI and EU AI Act requirements):
1. **Observability** — What decision was made, where, and when
2. **Provenance** — Which model or policy version was active
3. **Traceability** — The signals and context that drove the action
4. **Attributability** — Which agent or component is responsible
5. **Reproducibility** — Can the decision be replicated given the same inputs

**Note:** These 5 properties are Nokia's vendor articulation, not an industry standard. However, they map directly to EU AI Act Articles 13-14 (transparency, human oversight) and ETSI ENI GS 005 (context-aware policy management). Use TM Forum/ETSI/EU AI Act as the standard references; cite Nokia as one well-articulated vendor approach.

**EU AI Act (mandatory by Aug 2026):** Comprehensive, centralized logging of all agentic activities. Agentic asset inventory with unique identification, capabilities, and granted permissions. Rapid revocation within seconds.

**Consilium status:** Basic SQLite logs (`consilium.db`) track agent runs. No detailed decision trace, no model version tracking, no input/output logging for individual skills, no explanation of routing decisions.

---

## Industry Standards & Frameworks

### TM Forum Autonomous Networks (AN)

The most relevant governance framework. 70+ telcos signed the AN Manifesto.

**Key specifications:**
- **IG1230** — AN Technical Architecture (v1.1.1): Three layers, four closed loops
- **IG1252** — AN Levels Evaluation Methodology (v1.2.0): KEIs and KCIs for level assessment
- **IG1253** — Intent in Autonomous Networks (v1.3.0): Intent lifecycle management
- **TR290** — Intent Common Model (v3.6.0): Mandatory vocabulary for intent specification
- **IG1392** — AN Levels Assessment and Certification (v2.0.0)

**L3 requirements (Consilium's target):**
- System senses real-time environmental changes
- Closed-loop optimization in certain network domains
- Intent-based policy definition (operator says WHAT, not HOW)
- AI model evaluation before execution
- Human in oversight role, not decision loop for routine operations

### ETSI ENI (Experiential Networked Intelligence)

Most detailed policy architecture specification for AI-driven network management.

**Key specification:** GS ENI 005 (v3.1.1) — System Architecture with Context-Aware Policy Management.

**Core model:** Policy-driven closed control loops as the fundamental operational model. Policies dynamically adjust network configuration using big data analysis, analytics, and AI/ML mechanisms. Context-aware: policies adapt based on business goals, environmental conditions, and user needs.

### O-RAN Alliance

Most concrete policy enforcement mechanism through the A1 interface.

- Non-RT RIC provides **policy-based guidance**, ML model management, enrichment
- A1 Policies steer RAN operation without prescribing exact actions
- Near-RT RIC decides HOW to implement policies
- Policy data types are extensible

### 3GPP SA5

- AI/ML Management Framework: ML model lifecycle with OpenAPIs
- Intent-Driven Management: Intent = "expectations including requirements, goals and constraints given to a system, without specifying how to achieve them"
- Closed Control Loop: Operators leverage AI/ML, intent, NDT, and closed loops

### GSMA Responsible AI Maturity Roadmap

**Seven principles:** Fairness, Human Agency & Oversight, Privacy & Security, Safety & Robustness, Transparency, Accountability, Environmental Impact.

**Five maturity dimensions:** Vision, Operating Model, Technical Controls, Ecosystem Collaboration, Change Management.

**Adoption:** 19 MNOs including BT, Deutsche Telekom, Orange, Telefonica, Vodafone.

### EU AI Act

Full applicability from **August 2, 2026**.

**Key requirements for agentic telecom AI:**
- Risk classification: Critical infrastructure = "high-risk"
- Human oversight (Article 14): Ability to reject any proposed action
- Transparency (Article 13): AI systems must be interpretable
- Agentic asset inventory: Centralized list with unique identification and permissions
- Rapid revocation: Quick removal of agent privileges within seconds
- Audit trail: See exactly where, when, and how agents are acting

### NIST AI Risk Management Framework

- AI RMF 1.0 (NIST.AI.100-1): Core operational framework
- GenAI Profile (NIST.AI.600-1, July 2024): Specific to LLMs and agents
- AI Agent Standards Initiative (Feb 2026): Multi-year effort, first deliverables late 2026
- Five use cases: Generative AI, Predictive AI, Single-agent, Multi-agent, Developer guidance

### OWASP Top 10 for Agentic Applications (2026)

First formal taxonomy of risks specific to autonomous AI agents:
- Goal hijacking, tool misuse, identity abuse, memory poisoning, cascading failures, rogue agents
- Key principle: "Treat agents as privileged applications with clear identities, scoped permissions, continuous oversight, and lifecycle governance"

---

## What the Industry Leaders Are Doing

### Nokia — Glass Box Autonomy (vendor thought leadership, not industry standard)

**Note:** "Glass Box" is Nokia Bell Labs' articulation of governance principles. The concepts (observability, provenance, traceability, attributability, reproducibility) align with EU AI Act and ETSI ENI requirements but are Nokia's framing. Use as a reference model, not as a standard to cite.

**Core principle:** "An operating fabric connects four things: what the operator wants, what the system knows, what the system is allowed to do, and how it proves it did the right thing."

**Agent taxonomy (Nokia-specific):**
- **Observer agents** — Detect and summarize
- **Advisor agents** — Recommend
- **Actuator agents** — Execute bounded changes
- **Coordinator agents** — Cross-domain arbitration
- **Lifecycle agents** — Validation gates, rollout, rollback, audit

**Governance:** Guardrails + policy-based conflict management + digital twin simulation + confidence threshold calibration + bounded actuation (explicit limits on scope, rate of change, and blast radius).

### Ericsson — Supervisor Agent Architecture

**Agent types:** Restricted agents (bound by human-defined constraints), Copilots (LLM-based human interface).

**Governance:** Intent Management Function translates operator intent. Supervisor evaluates before execution. Optional human-in-the-loop. EIAP provides centralized governance over data access and policy compliance. Safety via tool constraints, code sandboxes, chain-of-thought supervision, output filtering.

### Amdocs — aOS

**Governance layers:** Azure Native Governance (Azure Policy, Purview) + Domain-Specific Guardrails (telecom regulations) + Human-in-the-Loop (critical decisions require approval) + Audit Trails + Integrated Compliance (continuous, not final checkpoint).

### ONAP CLAMP

**Architecture:** Dedicated closed-loop policy engine.

**Policy types:** Monitoring policies (what to watch), Analytics policies (how to analyze), Action policies (what to do), Guard policies (what NOT to do).

**Model:** Some actions automatic, others raise alarm and require human intervention. Full lifecycle management.

### AWS Bedrock AgentCore

**Approach:** Deterministic policy enforcement OUTSIDE the LLM reasoning loop.

- Cedar policy language: Fine-grained authorization based on identity and tool parameters
- Policies intercept ALL agent traffic before tool access
- Enforcement is deterministic, not probabilistic
- All decisions logged via CloudWatch

### Microsoft Agent Governance Toolkit (AGT)

**Released April 2, 2026.** Open-source, MIT license.

**Seven packages:**
1. **Agent OS** — Stateless policy engine, <0.1ms p99
2. **Agent Mesh** — Cryptographic identity (DIDs), trust scoring (0-1000)
3. **Agent Runtime** — Execution rings, saga orchestration, kill switch
4. **Agent Compliance** — Automated governance verification, regulatory mapping

---

## Gap Analysis — Consilium vs Industry

| Gap | Severity | Industry Benchmark | Consilium Status |
|-----|----------|-------------------|-----------------|
| No formal policy engine | CRITICAL | Nokia, ONAP, AWS all have dedicated enforcement | Routing hardcoded in Supervisor |
| No intent-based policy | HIGH | TM Forum TR290, 3GPP IDM, ETSI ENI require for L3 | Users ask questions; no persistent monitoring |
| No confidence scoring | HIGH | Nokia thresholds, 94% hallucination reduction | Guardrails check data presence, not analysis confidence |
| No rollback capability | HIGH for L3 | Nokia digital twin, MS AGT saga orchestration | Read-only today, no rollback design |
| No audit trail beyond SQLite | MEDIUM-HIGH | EU AI Act mandates comprehensive logging | Basic agent runs only |
| No scope boundaries | HIGH | Ericsson domain isolation, O-RAN A1 scoping | Any agent, any scope |
| No escalation policy | HIGH | Ericsson HITL, Nokia approval points, TM Forum L3 | Every query gets a response |
| Agent Factory: no governance gate | HIGH | Nokia lifecycle agents, MS AGT compliance grading | Auto-promotion after 2 uses |
| No constraint policies | HIGH | AWS Cedar, MS AGT, ONAP guard policies | Only data-aware routing |
| No routing explainability | MEDIUM | EU AI Act Article 13, ETSI ENI context-aware policy | Supervisor classifies but doesn't explain WHY |
| No policy-as-code | MEDIUM | OPA Rego, Cedar widely adopted | Guardrails are hardcoded Python |

---

## Proposed Policy Framework for Consilium

### Architecture — Where Policies Are Enforced

```
                    +------------------------+
                    |     INTENT LAYER       |  <-- NEW: Operator goals/constraints
                    |  (Policy Definitions)  |
                    +-----------+------------+
                                |
                    +-----------v------------+
                    |     POLICY ENGINE      |  <-- NEW: OPA/Cedar or custom
                    |  (Enforcement Point)   |
                    +-----------+------------+
                                |
         +----------------------+----------------------+
         |                      |                      |
+--------v--------+  +---------v--------+  +----------v---------+
|  PRE-ROUTING    |  |  PRE-EXECUTION   |  |  POST-EXECUTION    |
|  POLICIES       |  |  POLICIES        |  |  POLICIES          |
|                 |  |                  |  |                    |
| - Scope check   |  | - Constraint     |  | - Confidence       |
| - Auth check    |  |   validation     |  |   scoring          |
| - Intent match  |  | - Tool call      |  | - Audit logging    |
| - Escalation    |  |   interception   |  | - Rollback check   |
|   threshold     |  | - Parameter      |  | - Escalation       |
|                 |  |   bounds check   |  |   trigger          |
+-----------------+  +------------------+  +--------------------+
         |                      |                      |
         +----------------------+----------------------+
                                |
                    +-----------v------------+
                    |  EXISTING CONSILIUM    |
                    | (Supervisor -> Agents  |
                    |  -> Tools -> SLM)      |
                    +------------------------+
```

**Key design principle:** Policy engine sits OUTSIDE the agent loop — deterministic enforcement, not relying on SLM to self-police. Same principle as Consilium's existing 4-level guardrails, extended to governance.

### Implementation Phases

**Phase 1 — L1-L2 Hardening (P0, 3-5 weeks):**

| Item | What to Build | Effort |
|------|--------------|--------|
| Confidence scoring | SLM scores own confidence (0.0-1.0) as part of output format; calibrate against benchmark | 1-2 weeks |
| Escalation policy | Confidence-gated: >0.8 auto-respond, 0.6-0.8 caveat, 0.4-0.6 escalate, <0.4 refuse | 1 week |
| Audit logging | Structured JSONL: timestamp, agent, query, routing decision, tools called, SLM response, guardrail scores, model version | 1-2 weeks |

**Phase 2 — L2 Hardening (P1, 3 weeks):**

| Item | What to Build | Effort |
|------|--------------|--------|
| Scope boundaries | YAML config per agent: allowed domains, allowed sites, max cells per query | 1 week |
| Constraint policies | YAML hard limits: prohibited config types, prohibited domains for Factory | 1 week |
| Factory governance gate | Human review required before candidate → active promotion | 1 week |

**Phase 3 — L3 Preparation (P2-P3, 6-8 weeks):**

| Item | What to Build | Effort |
|------|--------------|--------|
| Policy engine | OPA (Open Policy Agent) with Rego rules, REST API | 2-3 weeks |
| Routing explainability | Supervisor logs WHY it chose each agent (confidence per category) | 1 week |
| Intent policy layer | Persistent goal monitoring with triggers and escalation | 3-4 weeks |
| Rollback framework | Version configs, auto-rollback on KPI degradation | 2-3 weeks |

**Phase 4 — L3/L4 (P4, 8+ weeks):**

| Item | What to Build | Effort |
|------|--------------|--------|
| Digital twin validation | Simulate predicted outcomes before execution | 4-6 weeks |
| Agent identity + trust scoring | UUID per agent, version tracking, trust decay | 3-4 weeks |

### Policy Configuration Examples

**Agent Scope Policies:**
```yaml
agent_policies:
  investigator:
    allowed_domains: [RAN, Transport, Core]
    allowed_sites: ["SITE-METRO-*", "SITE-URBAN-*"]
    max_cells_per_query: 10
  config_agent:
    allowed_config_types: [ran, qos, handover]
    prohibited_config_types: [core_routing, security, lawful_intercept]
  agent_factory:
    prohibited_domains: [security, billing, subscriber_data]
    max_candidate_agents: 20
    require_human_review: true
```

**Escalation Policies:**
```yaml
escalation_policies:
  confidence_thresholds:
    auto_respond: 0.8
    respond_with_caveat: 0.6
    escalate_to_human: 0.4
    refuse_to_answer: 0.2
  severity_overrides:
    critical_alarm: always_escalate
    revenue_impacting: require_approval
    multi_domain: require_approval
```

**Constraint Policies:**
```yaml
constraints:
  global:
    - "Never generate configs for production Core NFs without human review"
    - "Never claim certainty about real network state from SLM memory"
    - "Always disclose when data is synthetic vs real"
  investigator:
    - "Must call at least 2 tools before diagnosis"
    - "Must report NO_DATA explicitly, never fabricate"
  factory:
    - "Cannot create agents that call operational tools"
    - "Must include disclaimer: generated from model knowledge"
```

**Audit Policies:**
```yaml
audit:
  log_level: full
  required_fields:
    - timestamp, agent_id, query_hash
    - routing_decision, routing_confidence, routing_reason
    - tools_called, tool_inputs, tool_outputs
    - slm_prompt_hash, slm_response, slm_temperature
    - guardrail_scores, escalation_triggered
    - model_version, policy_version
  retention: 90_days
  export_format: jsonl
```

### Confidence Scoring — Implementation Sketch

Highest-impact, lowest-effort addition:

```python
# Add to every agent's response template:
"""
CONFIDENCE: [0.0-1.0]
CONFIDENCE_FACTORS:
  - data_completeness: [FULL|PARTIAL|NONE]
  - domain_match: [EXACT|RELATED|GENERAL]
  - evidence_strength: [STRONG|MODERATE|WEAK|NONE]
  - historical_accuracy: [from calibration table]
ESCALATION: [AUTO_RESPOND|CAVEAT|ESCALATE|REFUSE]
"""

# Post-processing:
def apply_escalation_policy(response, confidence, severity):
    if severity == "critical":
        return escalate(response)
    if confidence >= 0.8:
        return auto_respond(response)
    elif confidence >= 0.6:
        return respond_with_caveat(response)
    elif confidence >= 0.4:
        return escalate(response)
    else:
        return refuse_with_explanation(response)
```

### Mapping to TM Forum L3

| TM Forum L3 Requirement | Consilium Current | Policy Framework Addition |
|---|---|---|
| Closed-loop O&M for certain units | Detect + analyze, no act/verify | Intent policies + actuation + rollback |
| AI model evaluation before execution | Guardrails check data presence | Confidence scoring + threshold policies |
| System senses real-time changes | Synthetic data, polled on query | Event-driven triggers, continuous monitoring |
| Intent-based closed-loop | No intent layer | Intent policy definitions + IMF |
| Human in oversight role | No escalation mechanism | Escalation policies with confidence gates |
| Self-adjustment to environment | Agent Factory creates agents | Scope boundaries + governance gates |

### Recommended Technology Choices

| Component | Recommendation | Rationale |
|---|---|---|
| Policy engine | OPA (Open Policy Agent) with Rego | Proven in telecom (CNCF), REST API, decouples policy from code |
| Policy storage | YAML files (Phase 1) then OPA Bundle Server | Start simple, graduate to centralized |
| Confidence scoring | LLM self-evaluation + historical calibration | Ask SLM to score confidence; calibrate against benchmark |
| Audit logging | Structured JSONL with rotation | Simple, parseable; upgrade to ELK later |
| Agent identity | UUID per agent + version tracking | Lightweight; upgrade to DIDs if multi-org |
| Policy UI | YAML editor (Phase 1) then Streamlit dashboard | Match existing tech stack |

---

## Audit & Explainability Properties — Mapping to Consilium

The following 5 properties are needed for governed autonomous operations. They are articulated by Nokia Bell Labs as "Glass Box" but map directly to EU AI Act (Articles 13-14), ETSI ENI (GS 005), and TM Forum L3 requirements. We reference the properties, not the vendor branding:

| Property | What It Means | Consilium Gap |
|---|---|---|
| **Observability** | What decision was made, where, when | Partial (SQLite logs) |
| **Provenance** | Which model/policy version was active | Not tracked |
| **Traceability** | What signals drove the decision | Not logged |
| **Attributability** | Which agent is responsible | Basic (agent name in logs) |
| **Reproducibility** | Can you replay the same decision | Not possible (no input logging) |

---

## Agent Taxonomy — Mapping to Consilium

Agent role taxonomy (as defined by Nokia, but reflecting common multi-agent design patterns across the industry):

| Agent Role | Consilium Equivalent | Notes | Source |
|---|---|---|---|
| Observer agents | Knowledge Agent, Incident Agent | Detect and summarize | Common pattern |
| Advisor agents | Investigator Agent, Config Agent | Recommend actions | Common pattern |
| Actuator agents | Not built | Execute bounded changes — needed for L3 | Nokia, ETSI ENI |
| Coordinator agents | Supervisor Agent | Routes and arbitrates | Common pattern |
| Lifecycle agents | Not built | Validation gates, rollback, audit — needed for governance | Nokia specific |

**Note:** Nokia's agent taxonomy is a useful reference but is vendor-specific. The broader industry uses varied terminology. TM Forum and ETSI ENI define agent roles through functional descriptions rather than a fixed taxonomy.

---

## Key Takeaways

1. **Consilium's architecture is sound** — multi-agent, tool-augmented, domain-specialized. This aligns with GSMA, Ericsson, Nokia, and TM Forum directions.

2. **What separates Consilium from L3 is governance, not capability.** The agents work; what's missing is the policy layer that controls, constrains, audits, and escalates.

3. **The industry is converging on a common pattern:** Intent → Constraints → Policy Engine (outside LLM) → Confidence scoring → Audit trail.

4. **Policy-as-code (OPA, Cedar, YAML) is the 2026 trend.** Replacing hardcoded guardrails with declarative, versioned policies.

5. **The minimum viable policy framework (P0) can be built in 3-5 weeks:** confidence scoring + escalation + audit logging. This transforms Consilium from "a smart assistant" to "a governed autonomous system."

6. **EU AI Act compliance by August 2026** requires: agent inventory, comprehensive logging, human oversight, rapid revocation, transparency.

7. **The gap is addressable.** Ericsson and Nokia build the same patterns at carrier-grade scale. Consilium can implement the same principles at prototype scale.

---

## References

**TM Forum:**
- IG1230 — AN Technical Architecture (v1.1.1)
- IG1252 — AN Levels Evaluation Methodology (v1.2.0)
- IG1253 — Intent in Autonomous Networks (v1.3.0)
- TR290 — Intent Common Model (v3.6.0)
- IG1392 — AN Assessment and Certification (v2.0.0)

**ETSI:**
- GS ENI 005 (v3.1.1) — System Architecture with Context-Aware Policy Management
- GR ENI 008 — Intent-Aware Autonomicity
- GR ENI 017 — Control Loop Architectures

**3GPP:**
- SA5 AI/ML Management Framework (Rel-18/19)
- SA5 Intent-Driven Management

**O-RAN Alliance:**
- O-RAN.WG2.AIML — AI/ML Workflow Technical Report
- A1 Policy Management Service

**Governance Frameworks:**
- GSMA Responsible AI Maturity Roadmap (2024)
- EU AI Act (full applicability August 2, 2026)
- NIST AI RMF 1.0 + GenAI Profile (NIST.AI.600-1)
- OWASP Top 10 for Agentic Applications (2026)
- CSA CSAI Foundation — Securing the Agentic Control Plane (March 2026)

**Vendor Approaches:**
- Nokia: Glass Box Imperative, AgenticOps
- Ericsson: AI Agents in Telecom Network Architecture (Whitepaper)
- Amdocs: aOS (Agentic Operating System)
- ONAP: CLAMP Closed-Loop Automation Management Platform
- AWS: Bedrock AgentCore Policy (Cedar language)
- Microsoft: Agent Governance Toolkit (April 2026, MIT license)
- NVIDIA: NeMo Guardrails + NemoClaw
