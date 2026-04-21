"""
Consilium Strategy Presentation — Slide Reference Script
=========================================================

This script documents the ACTUAL structure of Consilium_Strategy_Presentation.pptx
as of 2026-04-10. 29 slides in 8-act narrative.

WARNING: Do NOT run this script to regenerate the presentation.
The production deck was built through iterative patching of the visual _9th version.
Regenerating from this script will produce text-only slides and LOSE all visual work
(215+ custom shapes across 29 slides).

To make changes:
  1. Start from current Consilium_Strategy_Presentation.pptx (or _9th backup)
  2. Write a targeted Python patch script that modifies only affected slides
  3. Save result — never regenerate the full deck from this script

This file serves as:
  - Content reference for all 29 slides
  - Speaker notes reference
  - Slide ordering documentation
  - Shape inventory per slide

See also: feedback_pptx_workflow.md in memory
"""

# ═══════════════════════════════════════════════════════════════
# PRESENTATION STRUCTURE — 29 slides, 8 acts
# ═══════════════════════════════════════════════════════════════
#
# ACT 1 — THE PROBLEM (Slides 3-4)
# ACT 2 — THE MARKET (Slides 5-6)
# ACT 3 — OUR ANSWER (Slides 7-8)
# ACT 4 — HOW WE BUILT IT (Slides 9-13)
# ACT 5 — WHAT IT CAN DO (Slides 14-18)
# ACT 6 — PROOF (Slides 19-21)
# ACT 7 — POSITIONING (Slides 22-24)
# ACT 8 — PATH FORWARD (Slides 25-29)
#
# ═══════════════════════════════════════════════════════════════

SLIDES = {
    # ----------------------------------------------------------
    # SLIDE 1: Title
    # Layout: 0 (title slide)
    # Shapes: 0 custom | Visual: template background
    # ----------------------------------------------------------
    1: {
        "title": "CONSILIUM",
        "subtitle": "Domain-trained. Agent-driven. Self-evolving.",
        "subhead": "Domain-Specialized SLM Prototype — Strategy Overview",
        "shapes": 0,
        "notes": (
            "Welcome. Consilium is a domain-specialized SLM prototype for telecom "
            "network operations. Built on Llama 3.1 8B, fine-tuned with 49K+ telecom "
            "examples. Runs locally, costs nothing to operate."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 2: What We Will Cover (Agenda)
    # Layout: 17 (content)
    # Shapes: 17 (8 act headers + 8 description cards + 1 bottom bar)
    # NOTE: Agenda was rebuilt via code. Acts have colored cards.
    # ----------------------------------------------------------
    2: {
        "title": "What We Will Cover",
        "subhead": "29-slide strategy overview in 8 acts",
        "shapes": 17,
        "acts": [
            ("THE PROBLEM",      "3-4",   "Why telecom needs domain-specific AI, Pain points → solutions"),
            ("THE MARKET",       "5-6",   "Industry deployment results, Competitive landscape"),
            ("OUR ANSWER",       "7-8",   "3 pillars of network intelligence, Key objectives achieved"),
            ("HOW WE BUILT IT",  "9-13",  "Architecture, routing, training, data sources, open-source vs craft"),
            ("WHAT IT CAN DO",   "14-18", "Capabilities, Factory+Skills, self-evolution, guardrails, trust model"),
            ("PROOF",            "19-21", "Benchmarks 84.1%, 25-step journey, tech stack"),
            ("POSITIONING",      "22-24", "TM Forum levels, new approaches, engineering insights"),
            ("PATH FORWARD",     "25-29", "Current state, external tools, roadmap, policy framework, ask"),
        ],
        "notes": (
            "29 slides in 8 acts. We start with the problem and market context, "
            "then give the punchline early (objectives achieved at slide 8). "
            "Then how we built it, what it can do, proof it works, positioning, "
            "and the path forward including the policy governance roadmap."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 3: The Challenge
    # Layout: 11 (transition slide)
    # Shapes: 0 | Visual: template transition layout
    # ----------------------------------------------------------
    3: {
        "title": "The Challenge",
        "subhead": "Why network operations needs domain-specific AI",
        "shapes": 0,
        "act": "THE PROBLEM",
        "notes": (
            "The core challenge: network operations is drowning in data and losing "
            "institutional knowledge. General-purpose AI doesn't have the telecom depth."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 4: Pain Points → How Consilium Solves Them
    # Layout: 17 | Shapes: 24 (7 pain cards + 7 arrows + 7 answer cards + 2 headers + 1 bar)
    # Built via code: 2-column layout, red pain points → green solutions
    # ----------------------------------------------------------
    4: {
        "title": "Pain Points → How Consilium Solves Them",
        "subhead": "Every pain point maps to a capability we've built",
        "shapes": 24,
        "content": {
            "rows": [
                ("Thousands of signals per hour",        "Multi-agent routing"),
                ("60-70% time on manual triage",         "Incident diagnosis in 3-12 seconds"),
                ("Siloed vendor tools",                  "Single platform, 6 domains"),
                ("Institutional knowledge loss",         "49K training examples + Agent Factory"),
                ("Generic AI hallucinates",              "84.1% accuracy + 4-level guardrails"),
                ("No tool access",                       "Investigator + 3 live tools"),
                ("Cannot learn new domains",             "Self-evolving Agent Factory"),
            ],
            "bottom_bar": "Every pain point has a working answer | Not aspirational — built, tested, and documented",
        },
        "notes": (
            "This slide maps each NOC pain point directly to a Consilium capability. "
            "Key message: these aren't aspirational — every answer on the right is built, "
            "tested, and documented. The rest of the presentation proves each claim."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 5: Industry Deployment Results
    # Layout: 17 | Shapes: 16
    # Visual: 5 deployment cards (Far EasTone, Vodafone, etc.)
    # Originally from _9th version
    # ----------------------------------------------------------
    5: {
        "title": "Industry Deployment Results",
        "subhead": "",
        "shapes": 16,
        "act": "THE MARKET",
        "notes": (
            "The industry is already moving — real deployments with real results. "
            "Far EasTone 60% ops AI-assisted, Vodafone FCR 15%→60%. "
            "This validates the approach. Domain-trained models + multi-agent systems."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 6: Competitive Landscape
    # Layout: 17 | Shapes: 0 (table in body placeholder)
    # Content: 10-player feature matrix
    # Originally from _9th version
    # ----------------------------------------------------------
    6: {
        "title": "Competitive Landscape",
        "subhead": "Feature matrix — 10 players compared (2025-2026 data)",
        "shapes": 0,
        "notes": (
            "Competitive landscape showing 7+ major players. Tech Mahindra uses same "
            "base model (Llama 3.1 8B). NVIDIA is the gorilla with 30B params but cloud-only."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 7: Consilium — The Solution
    # Layout: 17 | Shapes: 4 (3 pillar boxes + bottom bar)
    # Visual: 3 colored pillar cards (Domain-Trained, Agent-Driven, Self-Evolving)
    # Originally from _9th version
    # ----------------------------------------------------------
    7: {
        "title": "Consilium — The Solution",
        "subhead": "Three pillars of network intelligence",
        "shapes": 4,
        "act": "OUR ANSWER",
        "notes": (
            "Three pillars: domain-trained (not a generic LLM with a prompt), "
            "agent-driven (specialist routing), self-evolving (Agent Factory). "
            "All running locally for $0."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 8: Key Objectives Achieved
    # Layout: 17 | Shapes: 21 (10 number badges + 10 content cards + 1 summary bar)
    # Built via code: 2x5 grid of colored objective cards
    # ----------------------------------------------------------
    8: {
        "title": "Key Objectives Achieved",
        "subhead": "What the 25-step journey delivered",
        "shapes": 21,
        "content": {
            "objectives": [
                ("1",  "Domain-Specialized SLM",     "84.1% on 203Q benchmark, 49K+ examples, 6 domains"),
                ("2",  "Novel Training Method",       "Regression-driven patch-tuning, +2.2% from 1,293 rows"),
                ("3",  "Multi-Agent Architecture",    "Supervisor + 5 specialists, 100% routing accuracy"),
                ("4",  "Tool-Based Investigation",    "3 live tools, 5-skill framework, 14/14 tests pass"),
                ("5",  "Anti-Hallucination",          "4-level guardrails, validates BEFORE SLM"),
                ("6",  "Self-Evolving System",        "Agent Factory, no competitor has this publicly"),
                ("7",  "$0 Operational Cost",         "Fully local via Ollama, total training ~$10"),
                ("8",  "RAG Pipeline",                "3.5M vectors from 15K 3GPP docs"),
                ("9",  "Production-Ready App",        "Streamlit + FastAPI + CLI, Docker documented"),
                ("10", "Full Documentation",          "4 docs (3,600+ lines), 29-slide deck"),
            ],
            "bottom_bar": "Built in 3 weeks | ~$10 total cost | 84.1% accuracy | $0 operational | fully documented",
        },
        "notes": (
            "10 key objectives achieved. The punchline early — R&D sees what was "
            "delivered before diving into how. The rest of the deck backs each one up."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 9: System Architecture
    # Layout: 17 | Shapes: 13
    # Visual: 3-layer architecture diagram (User → Orchestration → Tools)
    # Originally from _9th version (25+ shapes originally, some manually adjusted)
    # ----------------------------------------------------------
    9: {
        "title": "System Architecture",
        "subhead": "3-layer architecture: User → Orchestration → Tools & Data",
        "shapes": 13,
        "act": "HOW WE BUILT IT",
        "notes": (
            "The architecture: Supervisor classifies and routes to 5 specialist agents. "
            "Only Investigator has external tool access. All powered by single fine-tuned model."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 10: Query Routing Flow
    # Layout: 17 | Shapes: 13
    # Visual: 5-step routing flow + post-routing + insight boxes
    # Originally from _9th version
    # ----------------------------------------------------------
    10: {
        "title": "Query Routing Flow — 5-Step Decision Path",
        "subhead": "",
        "shapes": 13,
        "notes": (
            "5-step routing flow. Critical: Step 3 (data-aware guardrail) prevents "
            "Agent Factory from fabricating network data. Without this, entity queries "
            "go to Factory instead of Investigator."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 11: Model Training — Regression-Driven Approach
    # Layout: 17 | Shapes: 19
    # Visual: Version progression chart + QLoRA details + data composition
    # Originally from _9th version
    # ----------------------------------------------------------
    11: {
        "title": "Model Training — Regression-Driven Approach",
        "subhead": "From 78% to 84% through surgical patching",
        "shapes": 19,
        "notes": (
            "Regression-driven training: don't retrain, patch. Question-level diff "
            "identifies failures, targeted data generation fixes them. +2.2% from 1,293 rows."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 12: Training Data & RAG
    # Layout: 17 | Shapes: 17
    # Built via code: Left=5 data source cards + composition bar, Right=RAG details + 6 QC checkmarks
    # ----------------------------------------------------------
    12: {
        "title": "Training Data & RAG — What Powers Consilium",
        "subhead": "Data provenance, curation methodology, and quality controls",
        "shapes": 17,
        "content": {
            "training_sources": [
                ("3GPP TSpec-LLM",            "15,422 files, Release 8-19, 535M words"),
                ("Synthetic Q&A Generation",   "38K examples, 47 NOC scenarios, 25 configs, 6 domains"),
                ("Expert Responses",           "Curated from Claude / ChatGPT / Gemini"),
                ("Claude API Corrective",      "v4: 3,674 rows, v4.1: 395 rows"),
                ("Quality-Filtered Replay",    "v4: 3,700, v4.1: 900 rows"),
            ],
            "rag": "3.5M vectors, 15,422 3GPP docs, Release 8-19, ChromaDB, all-MiniLM-L6-v2",
            "quality_controls": [
                "MCQ contamination removed (92 rows)",
                "Probability-pattern filtering (146 phrases rewritten)",
                "Anti-hallucination style rules enforced",
                "Gold eval: 203 questions, zero training overlap",
                "Per-question scoring with rubric review",
                "Coverage grids prevent category imbalance",
            ],
        },
        "notes": (
            "Data provenance — critical for R&D credibility. Training: 49K+ examples from "
            "3GPP specs, synthetic Q&A, expert responses, Claude API corrective. "
            "RAG: 3.5M vectors from 15K 3GPP docs. SLM and RAG are independent systems. "
            "6 quality controls including gold eval with zero training overlap."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 13: Open-Source Foundation, Unique Craft
    # Layout: 17 | Shapes: 23
    # Built via code: Left=6 open-source component cards, Right=6 differentiation cards with stripes
    # ----------------------------------------------------------
    13: {
        "title": "Open-Source Foundation, Unique Craft",
        "subhead": "The tools are open. The craft is ours.",
        "shapes": 23,
        "content": {
            "open_source": ["Llama 3.1 8B", "all-MiniLM-L6-v2", "3GPP TSpec-LLM",
                            "ChromaDB", "LangGraph", "Ollama/FastAPI/Streamlit"],
            "differentiation": [
                "49K Curated Training Examples",
                "Regression-Driven Methodology",
                "6 Iterations of Trial & Error",
                "Multi-Agent Architecture",
                "Quality Control Discipline",
                "Domain Expertise",
            ],
        },
        "notes": (
            "Addresses: if everything is open-source, can anyone replicate? "
            "The tools are commodity but the craft is unique — 49K curated examples, "
            "regression-driven methodology, 6 iterations, the architecture born from failures."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 14: What Consilium Can Do Today
    # Layout: 17 | Shapes: 6 (capability cards)
    # Visual: 6 colored cards (Incident, Investigation, Config, Self-Evolving, Knowledge, Guardrail)
    # Originally from _9th version
    # ----------------------------------------------------------
    14: {
        "title": "What Consilium Can Do Today",
        "subhead": "14 validated test scenarios across 4 rounds",
        "shapes": 6,
        "act": "WHAT IT CAN DO",
        "notes": (
            "Live demo scenarios validated. Incident 3-12s, Investigation 15-60s, "
            "Config 3-5s, Self-evolving agents 15-20s, Knowledge Q&A 3-8s. "
            "Guardrail validation: fake cell IDs blocked."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 15: Agent Factory + Skills
    # Layout: 17 | Shapes: 6
    # Visual: 3 tier cards + lifecycle + skill chains + guardrails
    # Originally from _9th version
    # ----------------------------------------------------------
    15: {
        "title": "Agent Factory + Skills — Self-Evolving Intelligence",
        "subhead": "The system grows agents AND capabilities from real usage",
        "shapes": 6,
        "notes": (
            "Agent Factory + Investigation Skills. Three tiers of self-evolution. "
            "Factory creates agents, skills define capabilities, strategies learn from outcomes."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 16: Self-Evolution — 3-Tier Model
    # Layout: 17 | Shapes: 6
    # Visual: 3 tier boxes + fixed vs evolves + human role
    # Originally from _9th version
    # ----------------------------------------------------------
    16: {
        "title": "Self-Evolution — 3-Tier Model",
        "subhead": "Hardcoded → Templated → Learned — all evolving from usage",
        "shapes": 6,
        "notes": (
            "Three tiers: Agents (built, self-evolving), Skills (built, data-driven), "
            "Strategies (future, emergent from logged outcomes). "
            "Human role: register tools, review candidates. System discovers everything else."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 17: Anti-Hallucination Guardrails
    # Layout: 17 | Shapes: 7 (problem + principle + 4 level cards + lesson)
    # Visual: 4 stacked level cards
    # Originally from _9th version
    # ----------------------------------------------------------
    17: {
        "title": "Anti-Hallucination Guardrails",
        "subhead": "The #1 risk with AI in telecom operations: fabricated data",
        "shapes": 7,
        "notes": (
            "Found SLM hallucinating 3 times during testing. Solution: 4-level guardrails "
            "that validate BEFORE SLM sees data. Design principle: don't trust SLM to self-police."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 18: Agent Data Trust Model
    # Layout: 17 | Shapes: 2 (+ body table)
    # Visual: Table + tool expansion plan
    # Originally from _9th version
    # ----------------------------------------------------------
    18: {
        "title": "Agent Data Trust Model",
        "subhead": "",
        "shapes": 2,
        "notes": (
            "Where each agent gets its data and what to trust. Only Investigator has "
            "external data access. Next: extend tools to Incident and Config agents. "
            "Enable RAG for Knowledge."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 19: Benchmark Results — 84.1%
    # Layout: 17 | Shapes: 6 (domain cards + notes)
    # Visual: Results table + 4 domain cards
    # Originally from _9th version
    # ----------------------------------------------------------
    19: {
        "title": "Benchmark Results — 84.1% Overall",
        "subhead": "100-question operational benchmark across 4 telecom domains",
        "shapes": 6,
        "act": "PROOF",
        "notes": (
            "84.1% overall on 203-question evaluation. Knowledge 92.3%, Config 94.3%, "
            "KPI 72.0%, Incident 77.9%. Covers RAN, Core, Transport, IMS, cross-domain."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 20: The Journey — 25 Steps to Production
    # Layout: 17 | Shapes: 9 (4 phase headers + 4 step bodies + 1 accuracy bar)
    # Built via code: 4 colored phase columns + bottom accuracy arc
    # Patched from _9th (was 21 steps, now 25)
    # ----------------------------------------------------------
    20: {
        "title": "The Journey — 25 Steps to Production",
        "subhead": "From 3GPP data to self-evolving network intelligence | 3 weeks | ~$10 total",
        "shapes": 9,
        "content": {
            "phases": [
                ("Phase 1: Foundation",     "Steps 1-8",   "Mar 18-19"),
                ("Phase 2: 7B Training",    "Steps 9-12",  "Mar 20 - Apr 2"),
                ("Phase 3: v4 Regression",  "Steps 13-21", "Apr 2-8"),
                ("Phase 4: Integration",    "Steps 22-25", "Apr 8-9"),
            ],
            "accuracy_arc": "61.4% → 76.1% → 78.1% → 81.9% → 79.3% → 82.8% → 84.1%",
        },
        "notes": (
            "25 steps across 4 phases. Key moments: 1.5B proved too small (Step 4), "
            "v3 pruning failed (Step 11), v4.1 shipped at 84.1% (Step 21)."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 21: Technology Stack
    # Layout: 17 | Shapes: 11 (3x3 grid + cost model cards)
    # Visual: 3x3 component grid + cost breakdown
    # Originally from _9th version
    # ----------------------------------------------------------
    21: {
        "title": "Technology Stack — Minimal Operational Cost",
        "subhead": "Fully local, fully private, no cloud dependency",
        "shapes": 11,
        "notes": (
            "Technology stack: entirely open-source, fully local. Ollama inference, "
            "LangGraph agents, ChromaDB RAG, FastAPI+Streamlit UI. $0 operational."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 22: TM Forum Autonomy Levels
    # Layout: 17 | Shapes: 15
    # Visual: L0-L5 level cards + Consilium position + L3 requirements
    # Originally from _9th, patched via code (21→25 steps, L2/L3/L4 descriptions corrected)
    # Then manually corrected by user based on TMF ANL expert feedback
    # ----------------------------------------------------------
    22: {
        "title": "TM Forum Autonomy Levels — Where We Stand",
        "subhead": "Industry standard framework for network automation maturity (L0-L5)",
        "shapes": 15,
        "act": "POSITIONING",
        "content": {
            "levels": {
                "L0": "Manual — No automation",
                "L1": "Assisted — System provides recommendations",
                "L2": "Partial — Machine decides within bounded tasks, human validates",
                "L3": "Conditional — Operates under intent + policy in defined domains. Human has oversight & intervention capability",
                "L4": "Highly Autonomous — Fully closed-loop with adaptive learning, self-optimization, cross-domain coordination",
                "L5": "Full Autonomy — Self-driving network",
            },
            "consilium_position": "L1-L2 (open-loop): recommend, not act",
            "l3_requirements": [
                "Intent interpretation (operator says WHAT)",
                "Policy constraints (blast radius, SLA protection)",
                "Context-aware decision making",
                "Closed-loop actuation + verification + state awareness",
            ],
            "our_implementation_plan": [
                "Actuation: config push, ticket creation, rollback",
                "Confidence scoring (our engineering choice, not TMF requirement)",
                "Escalation rules + feedback loop",
            ],
            "industry_target": "70+ telcos signed AN Manifesto. <5% achieved L4. Majority targeting L4 by 2026-2028",
        },
        "notes": (
            "TM Forum Autonomous Network Levels. Consilium is L1-L2 (open-loop). "
            "L2→L3 shift is open-loop to closed-loop. L3 = Intent → Decision → Action → Verify → Learn. "
            "TMF L3 requires intent interpretation, policy constraints, context-aware decisions, "
            "closed-loop actuation. Confidence scoring is our engineering choice, not TMF concept. "
            "Human role at L3 is oversight with intervention capability — not passive monitoring."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 23: New Approaches in Telecom AI
    # Layout: 17 | Shapes: 13 (6 approach cards + market learnings)
    # Visual: Colored cards for each approach
    # Originally "What Makes Consilium Unique", renamed to avoid boasting
    # ----------------------------------------------------------
    23: {
        "title": "New Approaches in Telecom AI",
        "subhead": "How we approached the problem differently — and what we learned from the market",
        "shapes": 13,
        "content": [
            "Self-evolving agents (no vendor has this publicly)",
            "4-level guardrails (designed from real failures)",
            "$0 operational cost (fully local)",
            "Full transparency (4 comprehensive docs)",
            "Config 94.3% (industry benchmark gap)",
            "Regression-driven training (novel methodology)",
        ],
        "notes": (
            "New approaches — not to boast, but to show different thinking. "
            "Self-evolving agents, 4-level guardrails, regression-driven training. "
            "Market learnings section shows we're incorporating industry leaders' lessons."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 24: Key Engineering Insights
    # Layout: 17 | Shapes: 10 (2x5 insight cards)
    # Visual: 10 numbered lesson cards
    # Originally from _9th version
    # ----------------------------------------------------------
    24: {
        "title": "Key Engineering Insights",
        "subhead": "10 lessons from building Consilium end-to-end",
        "shapes": 10,
        "notes": (
            "10 engineering lessons. Top 3: don't prune training data (v3 failure), "
            "guardrails at every SLM invocation point, patch-tune beats full retraining."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 25: Current State
    # Layout: 17 | Shapes: 10 (8 status cards + limitations + docs)
    # Visual: Status cards with green checkmarks
    # Originally from _9th, patched (21→25 steps)
    # ----------------------------------------------------------
    25: {
        "title": "Current State — Ready for Demonstration",
        "subhead": "All 25 steps complete — ready for live demonstration",
        "shapes": 10,
        "act": "PATH FORWARD",
        "notes": (
            "All 25 steps complete. Model shipped, agents working, tools integrated, "
            "guardrails validated. Limitations listed transparently."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 26: External Tools
    # Layout: 17 | Shapes: 9 (4-tier progression columns)
    # Visual: 4 tier columns (Done, Next, Future, Production)
    # Originally from _9th version
    # ----------------------------------------------------------
    26: {
        "title": "External Tools — Path to Production NMS/OSS",
        "subhead": "From synthetic data to real network integration",
        "shapes": 9,
        "notes": (
            "External tools progression. Tier 1 (done): synthetic data service, 14/14 tests. "
            "Tier 2 (next): O-RAN/ONAP Docker simulators. Tier 3 (future): OAI/srsRAN. "
            "Production: requires vendor access."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 27: Recommended Roadmap
    # Layout: 17 | Shapes: 13 (5 phase cards with timelines)
    # Visual: 5 colored phase columns
    # Originally from _9th version
    # ----------------------------------------------------------
    27: {
        "title": "Recommended Roadmap",
        "subhead": "Path from prototype to production deployment",
        "shapes": 13,
        "notes": (
            "5 phases: Now (demo), 1-2 months (Tier 2 simulators), 2-3 months (real NMS), "
            "3-6 months (production hardening), 6+ months (vendor-specific training)."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 28: Policy Framework & Governance Roadmap
    # Layout: 17 | Shapes: 11
    # Visual: Left=7 policy layer cards with status badges, Right=4 phase roadmap
    # Added manually by user from Policy_Framework_Slide.pptx
    # See POLICY_FRAMEWORK.md for full research
    # ----------------------------------------------------------
    28: {
        "title": "Policy Framework & Governance Roadmap",
        "subhead": "What's needed to move from L1-L2 to L3 | Vendor thought leadership - Glass Box, Nokia Bell Labs",
        "shapes": 11,
        "content": {
            "policy_layers": [
                ("Intent Policies",        "NOT BUILT"),
                ("Constraint Policies",    "PARTIAL"),
                ("Escalation Policies",    "NOT BUILT"),
                ("Scope Boundaries",       "NOT BUILT"),
                ("Confidence Thresholds",  "NOT BUILT"),
                ("Rollback Policies",      "NOT BUILT"),
                ("Audit / Explainability", "BASIC"),
            ],
            "roadmap_phases": [
                ("P0: L1-L2 Hardening",   "Confidence scoring + escalation + audit logging"),
                ("P1: L2 Hardening",       "Scope boundaries + constraints + Factory governance"),
                ("P2: L3 Preparation",     "Policy engine (OPA) + intent layer + rollback"),
                ("P3: L3/L4 Future",       "Digital twin + agent identity + full closed-loop"),
            ],
            "standards_aligned": [
                "TM Forum AN (IG1253/TR290)", "ETSI ENI (GS 005)", "O-RAN A1 Policy",
                "Nokia Glass Box", "ONAP CLAMP", "EU AI Act (Aug 2026)",
                "NIST AI RMF", "OWASP Agentic Top 10",
            ],
        },
        "notes": (
            "Governance gap and path to close it. 7 policy layers needed — currently only "
            "partial on constraints and basic on audit. P0 (confidence + escalation + audit) "
            "is 3-5 weeks and transforms from assistant to governed system. "
            "Capability is built; what separates from L3 is governance. "
            "Nokia Glass Box is vendor thought leadership, not industry standard — "
            "we reference underlying standards (EU AI Act, ETSI ENI)."
        ),
    },

    # ----------------------------------------------------------
    # SLIDE 29: What We Need
    # Layout: 17 | Shapes: 3 (asking + not asking + tagline)
    # Visual: 2 columns (asking vs not asking)
    # Originally from _9th version, "single-person" references removed
    # ----------------------------------------------------------
    29: {
        "title": "What We Need",
        "subhead": "To move from prototype to pilot deployment",
        "shapes": 3,
        "content": {
            "asking_for": [
                "Stakeholder alignment on framework and next steps",
                "Access to vendor NMS APIs for Tier 3 real data",
                "Vendor documentation for RAG indexing",
                "Pilot deployment target — one NOC team",
                "GPU budget ~$20/year for periodic retraining",
            ],
            "not_asking_for": [
                "No cloud API subscription ($0 operational)",
                "No new hardware (runs on existing laptop)",
                "No vendor licensing (open-source stack)",
            ],
        },
        "notes": (
            "What we need: stakeholder alignment, NMS API access, vendor docs, "
            "pilot target, small GPU budget. What we're NOT asking for: no cloud, "
            "no new hardware, no vendor licensing."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════
# ADDITIONAL SLIDES (manually added by user, not in original script)
# ═══════════════════════════════════════════════════════════════
#
# The user also created (may or may not be in the main deck):
#
# "Agent Execution Across TMF Autonomy Levels"
#   - 4 execution patterns mapped to TMF levels
#   - L1 Copilot, L2 Queue Attendant, L3 Closed Loop, Composition
#   - "Autonomy = Decision + Action + Verification (not just automation)"
#   - Bottom bar: "L2 Partial" (fix from "L2 Conditional")
#
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# CHANGE LOG
# ═══════════════════════════════════════════════════════════════
#
# 2026-04-09 Session 1 (original _9th version):
#   - 25 slides, fully visual (215+ shapes), 7-act narrative
#   - All slides redesigned from text-heavy to visual
#   - Saved as Consilium_Strategy_Presentation_9th.pptx (BACKUP)
#
# 2026-04-09 Session 2 (this session):
#   - PLAN.md: Renumbered 21 steps → 25 steps across 4 phases
#   - Patched slide 16: "21 Steps" → "25 Steps" with 4-phase visual boxes
#   - Patched slide 23: "21 steps" → "25 steps" in subhead + shapes
#   - Added slide: "Key Objectives Achieved" (10 cards, 2x5 grid)
#   - Added slide: "What We Will Cover" (agenda, 8 act cards)
#   - Updated slide 1: subhead → "Domain-Specialized SLM Prototype"
#   - Removed old slide 22: "Consilium vs Industry — Key Differentiators" (overlap)
#   - Renamed slide 23: "What Makes Unique" → "New Approaches in Telecom AI"
#   - Removed all "single-person" / "1 person" references
#   - Replaced "SINGLE-PERSON BUILD" card → "FULL TRANSPARENCY"
#   - Added speaker notes to all slides
#   - Added slide: "Training Data & RAG" (data provenance, 2-column)
#   - Added slide: "Open-Source Foundation, Unique Craft" (2-column)
#   - Rebuilt slide 4: "Pain Points → How Consilium Solves Them" (7-row mapping)
#   - Reordered all slides into 8-act narrative (28 slides)
#   - Updated agenda ranges for 28 slides
#
# 2026-04-09/10 Session 2 continued:
#   - Fixed TM Forum slide (22): L2, L3, L4 descriptions corrected
#   - L2: "System executes with human approval" → "Machine decides within bounded tasks"
#   - L3: Added intent + policy + "NOT yet built" for closed-loop
#   - L4: Added self-optimization, cross-domain, adaptive learning
#   - Consilium box: Added "open-loop" framing, "read-only" emphasis
#   - L3 requirements: Separated TMF requirements from "our implementation plan"
#   - Confidence scoring reframed as "our engineering choice" not TMF requirement
#   - Industry target: Added "70+ telcos, <5% achieved L4, 23% targeting by 2026-2028"
#   - Created POLICY_FRAMEWORK.md (full research document)
#   - User manually added Policy Framework slide (slide 28)
#   - User manually added "Agent Execution Across TMF Autonomy Levels" slide
#   - Updated Nokia Glass Box references: vendor thought leadership, not industry standard
#   - Final deck: 29 slides, all with speaker notes
#   - User took backup before TMF corrections
#
# KEY LESSON: Never regenerate from this script.
#   The visual deck was built through iterative patching.
#   Always patch the existing .pptx file.
#   See memory/feedback_pptx_workflow.md
#
# ═══════════════════════════════════════════════════════════════
