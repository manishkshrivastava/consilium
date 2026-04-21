# Consilium — Industry Research & Competitive Landscape
## (Previously: Telco SLM + Agentic Ecosystem Research)
### Last Updated: 2026-04-09

## Executive Summary

After researching NVIDIA, Nokia, Tech Mahindra, Ericsson, Amazon AWS, Amdocs, Microsoft, and the broader telco AI landscape (2025-2026), key findings:

1. **Nobody is training a telco LLM from scratch** — everyone fine-tunes existing foundation models (Llama, Mistral, Gemma, Qwen, Nemotron)
2. **Agentic AI has overtaken GenAI** as the dominant paradigm in telco (2025-2026 shift)
3. **RAG + 3GPP documents** is the most practical starting approach
4. **Fine-tuning yields measurable gains**: Llama 3.1 8B goes from 72.6% → 84.58% on telco MCQs with domain fine-tuning
5. **The configuration/automation gap is real**: even the best models score <30% on intent-to-YAML tasks — huge opportunity
6. **Open-source telco models and datasets already exist** on HuggingFace

---

## What the Big Players Are Doing

### NVIDIA
- **Nemotron Large Telco Model (LTM)**: 30B param, open-source, fine-tuned by AdaptKey AI on 3GPP specs + synthetic logs
- **Telco Reasoning Model**: Based on Qwen3-32B, trained via NeMo with synthetic NOC incident data
- **NVIDIA NeMo Agent Toolkit (NAT)**: For building telco-specific agentic workflows
- **AI Blueprints**: Reference architectures for network config optimization and RAN energy efficiency
- **NIM Microservices**: Containerized model serving for telco (used by Infosys, Accenture, TCS, Amdocs)
- **Key result**: Incident summary accuracy improved from ~20% → 60% with fine-tuned telco model

### Nokia
- **Nokia Language Model (NLM)**: RAG-based (not fine-tuned), trained on 330M+ words of Nokia product docs
- **Chose RAG over fine-tuning** — argues it's less costly, more accurate, fewer hallucinations
- **Autonomous Network Fabric**: Suite of telco-trained LLMs + Learning Agent Models (LAMs) + classical ML
- **aApps**: Localized agentic autonomous applications for network operations
- **Network as Code**: API platform integrated with Google Cloud's agentic AI (MCP, A2A protocol, Gemini)
- **Partnership**: $1B NVIDIA investment, joint AI-RAN development

### Tech Mahindra
- **Large Telco Model (LTM)**: Based on Llama 3.1 8B, fine-tuned with NVIDIA NeMo, deployed via NIM
- **TENO Framework**: Their custom fine-tuning framework on top of NeMo
- **TechM Orion**: 200+ pre-built AI agents across industries, C2A (Chat-to-Agent) interface
- **First customer**: O2 Telefonica Germany — automated root-cause analysis, field dispatch
- **Key result**: 2-3x accuracy improvement vs non-fine-tuned models in live NOC
- **Microsoft partnership**: Ontology-driven agentic AI with knowledge graphs for telco

### Amazon AWS
- **No pre-built domain-trained telecom LLM** — relies on partners and customer fine-tuning
- **Amazon Bedrock**: Supports fine-tuning Claude 3 Haiku, Llama 3.2 for telecom. SK Telecom fine-tuned Claude Haiku → 73% better feedback, 68% fewer bad responses
- **Bedrock AgentCore**: Fully managed platform for building/deploying AI agents with enterprise security
- **AWS + Orange**: Built GenAI assistant for NOC — analyzes PM data, FM metrics, historical trouble tickets
- **AWS + Nokia (MWC 2026)**: Agentic AI-powered 5G-Advanced network slicing — industry first in live 5G. Testing at du (UAE) and Orange (France)
- **AWS + Ericsson (Feb 2026)**: Agentic rApp as a Service (rApp aaS) — SaaS on AWS Marketplace. Connects to Non-RT RIC via R1 interface (O-RAN). First field test: Vivo Brazil. 100M+ AI inferences/day across 11M cells
- **NetoAI TSLAM**: Partner-built telecom-specific LLM on SageMaker + AWS Trainium (not AWS first-party)
- **Samsung CognitiV NOS Copilot**: Demonstrated at MWC 2025 using Amazon Bedrock for RAN management
- **Re:Invent 2025**: Session on "Bedrock AgentCore + MCP for Automated Telecom Service Assurance"
- **Key gap**: No first-party telecom model. Strong in infrastructure (Bedrock, AgentCore) but depends on partners for domain expertise

### Amdocs
- **amAIz Suite**: Domain-specific GenAI platform for telecom. Modular: Cognitive Core + amAIz Agents + aOS
- **aOS (Agentic Operating System)**: Launched 2026, claims "world's first agentic OS for telecom". Coordinates teams of agents across multi-step workflows with shared context
- **LLM-agnostic**: Tested Llama 2 7B/13B, Mixtral 8x7B (Mixtral won). Currently using Llama Nemotron. Supports OpenAI/GPT, Claude, Llama, Bloom, Mistral
- **Fine-tuning**: LoRA on "a few hundred annotated Q&A pairs" — 20-30% accuracy gains
- **NVIDIA partnership (deep)**: DGX Cloud (8x A100 80GB), NIM for inference (~80% latency reduction), NeMo data flywheel pipeline
- **Microsoft partnership**: Azure + Foundry modernization. amAIz on Microsoft AppSource
- **AWS partnership (MWC 2026)**: Multi-year strategic collaboration for AI-driven telecom modernization
- **Google Cloud**: amAIz available on Google Cloud Marketplace (since MWC 2025)
- **Deployed at**: e& (Etisalat), Telefonica Germany, AT&T (long-standing)
- **Key result**: 60% token reduction from data preprocessing, 40% additional savings from domain customization
- **Key gap vs Consilium**: No self-evolving agents (has NeMo data flywheel but not autonomous). aOS is proprietary. Cloud-dependent. "Few hundred" training pairs vs Consilium's 49K+

### Ericsson
- **Will NOT build its own LLM** — partners with Mistral AI for telco AI agents
- **Supervisor Agent Architecture**: Hierarchical multi-agent with Intent Management Function
- **Agentic rApp as a Service (rApp aaS)**: Launched Feb 2026 on AWS Marketplace. SaaS solution combining agentic AI + GenAI. Connects to Non-RT RIC via R1 interface (O-RAN standard)
- **Scale**: 100M+ AI inferences daily across 11M cells serving 2B+ subscribers
- **First field test**: Vivo Brazil
- **Natural language interface**: "Talk with the network" — operator can query network state in plain English

### SK Telecom
- **Fine-tuned Claude 3 Haiku on Amazon Bedrock** for Korean telecom Q&A
- **Results**: 73% increase in positive feedback, 37% KPI improvement, 68% reduction in low-quality responses
- **Method**: Synthetic data from larger LLMs for knowledge distillation + RAG + fine-tuning
- **Performance**: Internal scale 3.3 → 4.3 (out of 5). Fine-tuning up to 32K token context

### Deutsche Telekom
- **SOOFI**: 100B param sovereign European LLM, training on 130 NVIDIA DGX B200 systems (March 2026)
- **Multi-agentic RAN Guardian**: Using Google Cloud for RAN optimization

### SK Telecom
- **A.X K1**: 519B param Korean AI model, used as "Teacher Model" for distillation to smaller models

---

## Available Open-Source Telco Models & Datasets

### Models (HuggingFace)
| Model | Base | Size | Source |
|-------|------|------|--------|
| LLama-3-8B-Tele-it | Llama 3 8B | 8B | Yale (AliMaatouk/Tele-LLMs) |
| Tele-LLMs family | Various | 1B-8B | Yale University |
| NVIDIA Nemotron LTM | Nemotron 3 | 30B | NVIDIA/AdaptKey AI via GSMA |
| AT&T fine-tuned Gemma | Gemma | ~2B | AT&T (scored highest on TeleLogs benchmark) |

### Datasets
| Dataset | Content | Size |
|---------|---------|------|
| **TSpec-LLM** | All 3GPP docs (Release 8-19) | 13.5 GB, 535M words, 30K docs |
| **TeleQnA** | 10K telco MCQ questions | Benchmark dataset |
| **Tele-Data** | arXiv papers + 3GPP + telecom Wikipedia + Common Crawl | Multi-source |
| **GSMA Benchmark Suite** | TeleQnA, TeleYAML, TeleLogs, TeleMATH, 3GPP-TSG | 5 benchmarks |

### Key Papers
| Paper | Key Finding |
|-------|-------------|
| MM-Telco (2025) | LoRA fine-tuned Llama 3.1 8B: 72.6% → 84.58% on telco MCQs |
| TelcoAI (2025) | Agentic multi-modal RAG for 3GPP: 87% recall, 92% faithfulness |
| DeepSpecs (2025) | RAG with structural/temporal reasoning for expert-level 5G Q&A |
| Tele-LLMs (2024) | Continual pretraining on telco data outperforms general models |

---

## Real-World Agentic Deployments

| Company | What | Results |
|---------|------|---------|
| Far EasTone (Taiwan) | NOC automation | 60% ops AI-assisted, 10.5K tasks/month |
| Vodafone | Customer + network | 70% queries handled by AI, FCR 15%→60% |
| Rakuten Mobile | RAN optimization | 350K sites managed by ~250 engineers, 25-30% OPEX reduction |
| Microsoft Azure (internal) | Fiber-break dispatch | 65% autonomous dispatches, 80% faster RCA |
| Deutsche Telekom | RAN Guardian | 25% faster network repairs |

---

## Frameworks & Protocols in Use

### Production Frameworks (Telco-Specific)
| Framework | By | Notes |
|-----------|----|-------|
| Microsoft NOA Framework | Microsoft | Multi-agent NOC; used by Far EasTone, Vodafone |
| NVIDIA NeMo Agent Toolkit (NAT) | NVIDIA | Telco reasoning agents; used by NTT DATA, Telenor |
| Nokia Autonomous Network Fabric | Nokia | Telco-native agentic platform with Google Cloud |
| Cisco Crosswork Multi-Agentic | Cisco | Knowledge-graph-based NOC agents |
| TechM Orion | Tech Mahindra | 200+ pre-built agents |
| Ericsson IAP | Ericsson | Agentic rApps via AWS |

### General Frameworks (Used in PoCs/Custom Builds)
- LangGraph, CrewAI, AutoGen — used in internal PoCs but NOT dominant in production telco deployments
- Microsoft Semantic Kernel — part of Microsoft Foundry-based telco deployments

### Key Protocols
- **A2A (Agent-to-Agent)**: Google-originated, tested by Telefonica/Nokia
- **MCP (Model Context Protocol)**: Anthropic-originated, adopted by Microsoft NOA, Nokia
- **TM Forum Open APIs**: TMF621 (Trouble Ticket) etc. — standard interfaces for telco agents

---

## TM Forum Autonomy Levels

| Level | Name | Description |
|-------|------|-------------|
| L0 | Manual | No automation |
| L1 | Assisted | System provides recommendations |
| L2 | Partial | System executes with human approval |
| L3 | Conditional | System executes, human monitors |
| L4 | Highly Autonomous | System operates independently, human for exceptions |
| L5 | Full Autonomy | Fully self-driving network |

**Industry target**: L4 by 2026-2028 (Nokia, Tech Mahindra, NVIDIA all targeting this)

---

---

## Competitive Landscape — Full Comparison (Updated 2026-04-09)

### Feature Matrix

| Player | Product | Domain-Trained SLM | Multi-Agent | Tool Investigation | Self-Evolving | Local/Edge | Cost |
|---|---|---|---|---|---|---|---|
| **NVIDIA** | Nemotron LTM 30B + NeMo NAT | YES (30B) | Toolkit | Unknown | No | No (NIM cloud) | $$$ |
| **Amazon AWS** | Bedrock AgentCore + partner models | No (partners fine-tune) | YES (AgentCore) | YES (MCP) | No | No (cloud) | $$$ |
| **Amdocs** | amAIz + aOS | Partial (LoRA, few hundred pairs) | YES (aOS) | Implied | Partial (NeMo flywheel) | No (Azure/GCP) | $$$ |
| **Nokia** | NLM + Autonomous Network Fabric | No (RAG only) | YES (aApps) | Unknown | No | No | $$$ |
| **Ericsson** | Mistral + Supervisor Agent + rApp aaS | No (Mistral) | YES (hierarchical) | YES (R1 to RIC) | No | No (AWS) | $$$ |
| **Tech Mahindra** | LTM (Llama 8B) + Orion 200+ agents | YES (8B) | YES (Orion) | Unknown | No | No (NIM) | $$$ |
| **Microsoft** | NOA Framework | No (GPT-4) | YES (multi-agent NOC) | Unknown | No | No (Azure) | $$$ |
| **SK Telecom** | Claude Haiku fine-tuned on Bedrock | YES (Haiku) | Unknown | Unknown | No | No (AWS) | $$ |
| **Deutsche Telekom** | SOOFI 100B sovereign LLM | Building (100B) | Unknown | Unknown | No | No | $$$$ |
| **Consilium** | v4.1 (Llama 8B + QLoRA) + full stack | **YES (8B, 84.1%)** | **YES (built + factory)** | **YES (skill-based, 4-level guardrails)** | **YES (3-tier: agents + skills + strategies)** | **YES ($0)** | **$0** |

### What's Unique to Consilium

| Capability | Status in Industry | Consilium |
|---|---|---|
| Self-evolving (3-tier: agents + skills + strategies) | **Nobody has this publicly** | Tier 1: Agent Factory creates domain agents. Tier 2: Skills define capabilities (data-driven definitions, hardcoded chains). Tier 3: Investigation strategies learn from outcomes (future) |
| Skill-based investigation with chaining | Not publicly described at this granularity | 5 skills (triage→diagnose→impact→config→recommend), each with own tools, comparison mode for multi-site |
| 4-level anti-hallucination guardrails | Not publicly described by any vendor | Data service → Skill → Synthesis → Agent. Found and fixed 3 separate hallucination paths |
| Anti-hallucination guardrails on tool data | Not publicly described by any vendor | Pre-analysis validation, 3-tier verdict system, 16 test cases validated |
| $0 operational cost | Everyone else requires cloud APIs | Fully local via Ollama on commodity hardware |
| Single-person build | Vendors have teams of 10-100+ | Complete platform with 4 comprehensive docs |
| Full decision transparency | Vendor products are black boxes | Every decision, failure, and lesson documented |
| Regression-driven training methodology | Not publicly described | Question-level diff → failure mode classification → targeted patch |

### What Consilium Should Learn from Industry

| From | Lesson | Action |
|---|---|---|
| **Amdocs** | LoRA fine-tuning + NeMo data flywheel for continuous improvement | Consider NeMo pipeline for automated retraining cycle |
| **Ericsson** | R1 interface to O-RAN Non-RT RIC for real network data | Align Tier 2/3 tool integration with R1/O1 standards |
| **SK Telecom** | Claude Haiku fine-tuning on Bedrock with synthetic data distillation | Alternative path if Llama hits accuracy ceiling |
| **Nokia** | RAG over 330M+ words of vendor docs works better than fine-tuning for factual accuracy | Enable RAG (already built). Index vendor docs alongside 3GPP |
| **AWS** | Bedrock AgentCore + MCP is becoming the enterprise standard for agent deployment | Consider MCP protocol adoption for tool interoperability |
| **NVIDIA** | NIM containerization is the standard deployment path for serving SLMs at scale | If scaling beyond laptop, package Consilium as NIM container |

---

## What Consilium Actually Achieved vs Original Plan

### Original Plan (from this document)

| Phase | Planned | Timeline |
|---|---|---|
| Phase 1: Foundation | Download TSpec-LLM, prepare training data | Weeks 1-3 |
| Phase 2: Fine-tune SLM | Llama 3.1 8B, QLoRA, GSMA benchmark | Weeks 3-5 |
| Phase 3: RAG Pipeline | ChromaDB, LlamaIndex, 3GPP docs | Weeks 5-7 |
| Phase 4: Agentic Ecosystem | Multi-agent with LangGraph | Weeks 7-12 |
| Phase 5: Deployment | Ollama local, Baseten production | Weeks 12+ |

### What Was Actually Built (21 steps)

| Phase | What Happened | Result |
|---|---|---|
| Foundation | 38K training examples, 15K 3GPP docs, TSpec-LLM | Done |
| SLM Training | 1.5B→7B pivot, v1(78%)→v2(82%)→v3(failed)→v4(83%)→v4.1(84.1%) | 84.1% accuracy |
| RAG Pipeline | 3.5M vectors, 64 GB ChromaDB, all-MiniLM-L6-v2 | Built, disabled by default |
| Agent System | 5 built-in agents + Investigator + Agent Factory + guardrails | Working end-to-end |
| External Tools | Tier 1 synthetic data service, 14/14 tests, anti-hallucination | Validated |
| Deployment | Ollama local, $0 cost, full deployment playbook documented | Ready |

### Key Deltas from Plan

1. **Started with 1.5B, had to pivot to 8B** — 1.5B hit fundamental ceiling at 61%
2. **v3 failed** — pruning training data destroys knowledge. Critical lesson for the industry
3. **Regression-driven training** emerged as the methodology — not in any vendor's public approach
4. **Agent Factory** was not in the original plan — emerged from the need to handle unseen domains
5. **Anti-hallucination guardrails** were not planned — discovered during testing (cell 331145 incident)
6. **Context loss across agent switches** was a bug found during live testing — now fixed
7. **TeleYAML gap** (industry scores <30%) — Consilium's ConfigAgent scores 94.3% on config generation

---

## GSMA Benchmark Key Finding

**Critical gap**: All models score **under 30% on TeleYAML** (intent-to-network-configuration). This means:
- There's a massive opportunity in building agents that can translate natural language intents into actual network configs
- This is where a specialized telco SLM + agentic system could differentiate

---

## Original Approach (Executed — see PLAN.md for full 21-step journey)

Based on what the industry leaders were doing, here was the strategy that was executed:

### Phase 1: Foundation (Weeks 1-3)
**Data Collection & Preparation**
- Download TSpec-LLM dataset (all 3GPP docs, 13.5GB)
- Collect TeleQnA benchmark for evaluation
- Gather synthetic NOC data (alarm logs, incident tickets, troubleshooting steps)
- Format as instruction-response pairs for fine-tuning

### Phase 2: Fine-Tune the Telco SLM (Weeks 3-5)
**Base Model**: Llama 3.1 8B (same as Tech Mahindra's choice — proven in production at O2 Telefonica)
**Alternative**: Qwen 2.5 7B (NVIDIA uses Qwen3-32B for reasoning, but 7B is more practical)
**Method**: QLoRA via Unsloth + HuggingFace PEFT
**Training Focus**:
- 3GPP knowledge (specs, terminology, procedures)
- NOC operations (alarm analysis, root-cause, remediation)
- Network configuration (the <30% gap — huge opportunity)
**Evaluation**: GSMA benchmark suite (TeleQnA, TeleLogs, TeleYAML)

### Phase 3: RAG Pipeline (Weeks 5-7)
**Why RAG first**: Nokia explicitly chose RAG over fine-tuning for accuracy + less hallucination
**Our approach**: Fine-tuning + RAG (best of both worlds, like TelcoAI paper: 87% recall, 92% faithfulness)
- Vector DB: ChromaDB or Qdrant
- Embed 3GPP docs, MOPs/SOPs, troubleshooting guides
- LlamaIndex or LangChain for orchestration

### Phase 4: Agentic Ecosystem (Weeks 7-12)
**Architecture**: Multi-agent system inspired by TM Forum Agent Fabric + Microsoft NOA
**Framework**: LangGraph (most flexible for custom builds) + MCP protocol support
**Agents**:

1. **Incident Agent** — Diagnoses network issues using alarms + telemetry
2. **Healing Agent** — Manages tickets and executes corrective actions
3. **Configuration Agent** — Translates intents to network configs (targeting the TeleYAML gap)
4. **Knowledge Agent** — RAG-powered Q&A on 3GPP specs and procedures
5. **Optimization Agent** — RAN parameter tuning suggestions
6. **Supervisor Agent** — Orchestrates other agents (Ericsson's pattern)

### Phase 5: Deployment (Weeks 12+)
- **Local/Dev**: Ollama
- **Production**: Baseten or vLLM
- **Interface**: API + optional OpenClaw for chat integration

---

## Technology Stack (As Built)

| Layer | Planned | Actually Used | Result |
|-------|---------|---------------|--------|
| Base Model | Llama 3.1 8B | Llama 3.1 8B Instruct | Confirmed — same as Tech Mahindra's choice |
| Fine-tuning | Unsloth + QLoRA | Unsloth + QLoRA (r=16, alpha=32) | v2→v4→v4.1 regression-driven chain. 84.1% |
| Training Data | TSpec-LLM + synthetic | 49K rows + 8.7K corrective patches | More data than planned, quality-focused |
| RAG | LlamaIndex + ChromaDB | LlamaIndex + ChromaDB (3.5M vectors, 64 GB) | Built. Currently disabled. Ready to enable |
| Agents | LangGraph + MCP | LangGraph + custom orchestrator | 5 built-in + Investigator + Agent Factory |
| Tools | Not in original plan | FastAPI data service (KPI, Alarm, Config) | Tier 1 synthetic, Tier 2/3 planned |
| Guardrails | Not in original plan | Anti-hallucination (3-tier verdict) | Emerged from testing. Critical for production |
| Agent Factory | Not in original plan | SQLite registry + hybrid prompt + lifecycle | Self-evolving agents. Unique in industry |
| Evaluation | GSMA Benchmark Suite | Custom 100Q + 203Q gold eval | Domain-specific, more actionable |
| Local Inference | Ollama | Ollama (GGUF Q4_K_M, 4.6 GB) | $0 operational cost |
| Production | Baseten or vLLM | DEPLOYMENT_PLAYBOOK.md (Docker Compose) | Documented, ready for deployment |
| Protocols | MCP + TM Forum Open APIs | TMF628/642/639 adapter pattern designed | Tier 2 implementation planned |
