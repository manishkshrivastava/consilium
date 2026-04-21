# Independent Investigation: Agentic AI Supervisor/Reasoning Layer
# Alignment of Consilium's Thesis with Published Industry Research

Date: 2026-04-11

---

## The Thesis Under Investigation

1. The supervisor/reasoning layer is the most critical component of an agentic framework
2. Three approaches exist to build it: rule-based, ML-based, and domain-specific LLM-based
3. The production answer is hybrid (layering all three)
4. For telecom/vertical domains, domain fine-tuning of the LLM supervisor is essential

## Methodology

Exhaustive research across published materials from five organizations: Google/Google DeepMind, AWS/Amazon, Anthropic, OpenAI, and Oracle. Only findings that could be traced to actual published documents, documentation pages, research papers, or blog posts are included. Where a finding could not be verified, it is noted as unconfirmed.

---

## Consolidated Alignment Matrix

| Thesis Point | Google/DeepMind | AWS | Anthropic | OpenAI | Oracle |
|---|---|---|---|---|---|
| 1. Supervisor is critical | STRONGLY ALIGNS | STRONGLY ALIGNS | STRONGLY ALIGNS | STRONGLY ALIGNS | PARTIALLY ALIGNS |
| 2. Three approaches exist | STRONGLY ALIGNS | PARTIALLY ALIGNS | PARTIALLY ALIGNS | ALIGNS | UNCONFIRMED |
| 3. Hybrid is production answer | VERY STRONGLY ALIGNS | ALIGNS | STRONGLY ALIGNS | STRONGLY ALIGNS | IMPLICITLY ALIGNS |
| 4. Domain fine-tuning essential | ALIGNS (with nuance) | PARTIALLY ALIGNS | DOES NOT ALIGN | ALIGNS (strong evidence) | PARTIALLY MISALIGNS |

---

## Thesis Point 1: "The supervisor/reasoning layer is the most critical component"

**VERDICT: Universally validated across all five organizations.**

### Google/DeepMind

Google's "Agents" white paper (2024) defines the orchestration layer as governing "the agent's cognitive processes, managing how it takes in information, performs reasoning, and determines its next actions." Their "Introduction to Agents" white paper (Nov 2025) calls it "The Nervous System." The Architecture Center states: "At the core of any complex agentic system is what's called a 'primary orchestrator,' whose purpose is not to perform the low-level tasks itself, but to manage the workflow, delegate to specialized sub-agents, and interact with the user."

The DeepMind scaling paper ("Towards a Science of Scaling Agent Systems", Dec 2025, arXiv:2512.08296) provides the strongest quantitative evidence: across 180 configurations tested, coordination topology determined performance more than model choice or agent count. Centralized coordination with a supervisor achieved 4.4-fold error containment vs 17.2-fold error amplification in independent agent systems.

- Sources: Google Agents White Paper (2024), Introduction to Agents (Nov 2025), Google Cloud Architecture Center, arXiv:2512.08296

### AWS

Every major AWS publication positions the orchestration/reasoning layer as the central architectural concern. The Multi-Agent Orchestrator framework (awslabs/multi-agent-orchestrator) architectures everything around the Classifier — the supervisor that analyzes user input and routes to the appropriate agent. Bedrock Agents documentation describes the FM as the "brain" of the agent system. At re:Invent 2024, AWS positioned the orchestration strategy as "what separates prototype agents from production agents."

- Sources: AWS Prescriptive Guidance on Agentic AI, Amazon Bedrock Agents documentation, AWS Multi-Agent Orchestrator (GitHub), AWS re:Invent 2024 sessions

### Anthropic

Anthropic's internal managed agent architecture explicitly separates the "brain" (LLM reasoning) from the "hands" (tools/execution): "no hand is coupled to any brain, brains can pass hands to one another." Their multi-agent research system uses an orchestrator-worker pattern where "a lead agent coordinates the process while delegating to specialized subagents." This system outperformed single-agent Claude Opus 4 by 90.2% on internal evaluations — validating that the orchestrator architecture is the performance differentiator.

- Sources: "Scaling Managed Agents: Decoupling the Brain from the Hands" (2025), "How We Built Our Multi-Agent Research System" (2025), "Building Effective Agents" (Dec 2024)

### OpenAI

OpenAI's "A Practical Guide to Building Agents" (2025) defines the Model as the core of the agent, "powering the agent's reasoning and decision-making." Their Manager pattern "empowers a central LLM — the 'manager' — to orchestrate a network of specialized agents." Their Reasoning Best Practices describe the Planner-Doer pattern where a reasoning model serves as "the planner, producing a detailed, multistep solution and then selecting and assigning the right GPT model for each step." The o3/o4-mini models were "trained to use tools through reinforcement learning — teaching them not just how to use tools, but to reason about when to use them."

- Sources: "A Practical Guide to Building Agents" (2025), Agents SDK Documentation, Reasoning Best Practices, "Introducing o3 and o4-mini" (Apr 2025)

### Oracle

Oracle treats orchestration as important but frames it as one component alongside data grounding, tool use, and enterprise integration. Their OCI Generative AI Agents service uses an orchestration layer for routing and tool management, but Oracle emphasizes the full enterprise stack rather than elevating the supervisor as the single critical component.

- Sources: OCI Generative AI Agents documentation, Oracle CloudWorld 2024

### Assessment

All five organizations place the reasoning/orchestration layer at the center of their agent architectures. The terminology varies — "orchestration layer" (Google, AWS), "brain" (Anthropic), "manager/planner" (OpenAI), "orchestration" (Oracle) — but the concept is identical. Google DeepMind's scaling paper provides the only quantitative proof: the supervisor's design determines agent system performance more than model choice or agent count.

---

## Thesis Point 2: "Three approaches exist: rule-based, ML-based, and domain-specific LLM-based"

**VERDICT: Validated by Google and OpenAI explicitly; acknowledged by AWS and Anthropic implicitly. Not confirmed by Oracle.**

### Google/DeepMind — STRONGEST VALIDATION

Google's Agent Development Kit (ADK) literally implements three agent types:

1. **Workflow Agents** (SequentialAgent, ParallelAgent, LoopAgent) — "determine the execution sequence according to their type without consulting an LLM for the orchestration itself, resulting in deterministic and predictable execution patterns"
2. **LlmAgent** — LLM-driven reasoning and dynamic routing
3. **Custom Agents** — user-defined logic including ML classifiers

Google's Architecture Center explicitly distinguishes deterministic patterns from LLM-driven patterns: "The coordinator pattern uses an AI model to orchestrate and dynamically route tasks, while the parallel pattern relies on a hardcoded workflow to dispatch tasks for simultaneous execution without the need for AI model orchestration."

- Sources: ADK Documentation, Google Cloud Architecture Center — "Choose Design Pattern for Agentic AI System"

### OpenAI

OpenAI explicitly describes three types of guardrails: "LLM-based guardrails, rules-based guardrails such as regex, and the OpenAI moderation API" (ML-based classification). While this taxonomy applies to guardrails rather than the full supervisor layer, the architectural principle of three distinct mechanisms is identical. The Agents SDK supports deterministic workflows (rule-based), model-based triage (ML classification), and reasoning model supervision (LLM planning).

- Sources: "A Practical Guide to Building Agents", Agents SDK Guardrails documentation

### AWS

AWS does not explicitly enumerate the three approaches as a taxonomy. However, Bedrock Agents offers: (a) ReAct/LLM-based default orchestration, (b) Return of Control for application-level rules, and (c) Custom Lambda orchestration enabling any logic (ML, rules, or LLM). The Multi-Agent Orchestrator provides BedrockClassifier (LLM-based) with extensibility for custom classifiers (rule-based, ML-based).

- Sources: Bedrock Agents documentation, Multi-Agent Orchestrator (awslabs/multi-agent-orchestrator)

### Anthropic

Anthropic draws a binary distinction between "workflows" (predefined code paths = rule-based) and "agents" (LLM-driven). They acknowledge routing can use "an LLM or a more traditional classification model/algorithm." Constitutional Classifiers demonstrate ML-based enforcement of rule-based principles. Anthropic does not frame these as three competing approaches to the supervisor — rather, they are different patterns applied at different levels.

- Sources: "Building Effective Agents" (Dec 2024), Constitutional Classifiers research

### Oracle — NOT CONFIRMED

Oracle has not, based on available materials, published a taxonomy of supervisor approaches.

### Assessment

Google provides the strongest validation — ADK is a production framework that literally implements all three types. OpenAI validates the three-mechanism concept through guardrails. The thesis's taxonomy is architecturally sound but is not universally adopted as a standard framework by all vendors. No vendor explicitly contradicts it.

---

## Thesis Point 3: "The production answer is hybrid (layering all three)"

**VERDICT: Strongly validated across all five organizations. This is the most consistently supported thesis point.**

### Google/DeepMind — STRONGEST VALIDATION

ADK's design philosophy is explicitly built on combining approaches: "ADK offers flexible orchestration by defining workflows using workflow agents (Sequential, Parallel, Loop) for predictable pipelines, or leveraging LLM-driven dynamic routing (LlmAgent transfer) for adaptive behavior." The Composite design pattern "allows for combining any of the other patterns."

The Architecture Center states: "guardrails block risky actions, critics review outputs for errors, and routers direct different parts of complex tasks to specialized models, **shifting the reliability burden from the probabilistic LLM to deterministic system design.**"

Google's own telecom deployment (Autonomous Network Operations Framework) combines GNNs (ML-based), rule-based network policies, and LLM-powered agents. AlphaEvolve combines evolutionary algorithms (rule-based) + LLMs (reasoning) + automated evaluators (deterministic).

- Sources: ADK Documentation, Google Cloud Architecture Center, Autonomous Network Operations Framework, AlphaEvolve (arXiv:2506.13131)

### OpenAI

OpenAI's Reasoning Best Practices explicitly state: "Most AI workflows will use a combination of both models — o-series for agentic planning and decision-making, GPT series for task execution." The guardrails documentation advocates layered defense: "While a single guardrail is unlikely to provide sufficient protection, using multiple, specialized guardrails together creates more resilient agents." The concrete example: GPT-4o for triage + o3-mini for final decisions.

- Sources: Reasoning Best Practices, "A Practical Guide to Building Agents"

### Anthropic

Anthropic's own harness design combines "deterministic safeguards like retry logic and regular checkpoints" with LLM-based agent reasoning. Constitutional AI layers rule-based principles (the constitution) with ML classifiers and LLM self-evaluation. Their "Building Effective Agents" guide presents five composable patterns designed to be mixed. Caveat: Anthropic strongly advises "consider adding complexity only when it demonstrably improves outcomes."

- Sources: "Effective Harnesses for Long-Running Agents" (2025), Constitutional AI research, "Building Effective Agents"

### AWS

AWS provides multiple orchestration strategies in Bedrock Agents: default ReAct (LLM-based), Return of Control (rule-based), Custom Lambda (any logic). The Well-Architected Generative AI Lens recommends cost optimization through tiered approaches — cheaper/faster methods for simple routing, full LLM reasoning for complex cases. This implicitly supports hybrid layering.

- Sources: Bedrock Agents documentation, AWS Well-Architected Generative AI Lens

### Oracle

Oracle's architecture IS hybrid in practice — deterministic business logic (ERP workflows) combined with LLM reasoning (natural language understanding). They frame this as "enterprise AI" rather than using "hybrid supervisor" terminology.

- Sources: OCI Generative AI Agents documentation, Oracle CloudWorld 2024

### Assessment

This is the thesis's strongest claim. Every vendor either explicitly advocates or implicitly demonstrates hybrid architectures. Google's quote about "shifting the reliability burden from the probabilistic LLM to deterministic system design" is the clearest articulation of the principle.

---

## Thesis Point 4: "For telecom/vertical domains, domain fine-tuning of the LLM supervisor is essential"

**VERDICT: This is where the thesis diverges most from published guidance. Supported by OpenAI and Google with evidence; not supported by Anthropic; partially supported by AWS and Oracle who favor RAG-first approaches.**

### OpenAI — STRONGEST SUPPORT

OpenAI published a case study with **SK Telecom** (30M+ subscribers) showing domain fine-tuning achieved:
- 35% increase in conversation summarization quality
- 33% increase in intent recognition accuracy
- Satisfaction scores from 3.6 to 4.5 (out of 5)

OpenAI's Reinforcement Fine-Tuning (RFT) documentation shows fine-tuning reasoning models for domain-specific tool calling and decision-making. The SafetyKit case demonstrates replacing complex workflow nodes with a single domain-fine-tuned reasoning agent. Their function calling fine-tuning documentation states: "As the number of functions increases and the complexity of the task increases, function calling becomes less accurate with more hallucinated and incorrect invocations" — fine-tuning addresses this.

- Sources: "Improvements to Fine-Tuning API" (SK Telecom case), RFT documentation, Fine-Tuning for Function Calling cookbook

### Google/DeepMind — SUPPORTS

Google Vertex AI documentation states: "Supervised fine-tuning is particularly effective for domain-specific applications where the language or content significantly differs from the data the large model was originally trained on." Gemini 2.0 Flash fine-tuning supports function calling — meaning the supervisor's tool-selection reasoning can be domain-tuned. Google's telecom work partners with domain-specific model providers (NetAI for GraphML), validating that generic models are insufficient for telecom.

The GSMA 6G Community Whitepaper (Feb 2026) states: "Telecom deployments often require localized adaptation to vendor-specific behaviours, regulatory constraints, and customer policies. Parameter-efficient fine-tuning strategies and retrieval-augmented approaches provide practical alternatives to full retraining."

- Sources: Vertex AI Supervised Tuning documentation, Google Autonomous Network Operations Framework, GSMA 6G Whitepaper

### Anthropic — DOES NOT SUPPORT

This is the most significant misalignment. Anthropic's primary domain specialization mechanisms are, in order of preference:
1. **Prompt engineering** and system prompts
2. **Agent Skills** — structured instruction files loaded dynamically at runtime
3. **MCP tool integration** — standardized connections to domain data/tools
4. **Fine-tuning** — available only for Claude 3 Haiku (smallest model) through Amazon Bedrock; not available through Anthropic's own API

Anthropic built Agent Skills specifically to solve domain specialization WITHOUT fine-tuning. Their subagent architecture achieves domain specialization via focused system prompts, not by fine-tuning the orchestrator. Anthropic does acknowledge fine-tuning can "encode company and domain knowledge" — they do not say it is wrong, but they do not recommend it as the primary approach.

- Sources: "Equipping Agents for the Real World with Agent Skills" (2025), "Building agents with the Claude Agent SDK", Fine-tune Claude 3 Haiku documentation

### AWS — PARTIALLY SUPPORTS

AWS provides the mechanisms (Bedrock Custom Models, fine-tuning, Custom Model Import) but has NOT published guidance explicitly saying "fine-tune your agent's supervisor/reasoning model for your domain." Their default assumption is that a general-purpose frontier model serves as the supervisor, with domain knowledge injected via RAG/knowledge bases. The Multi-Agent Orchestrator supports custom/fine-tuned models as classifiers but does not explicitly advocate this approach.

- Sources: Bedrock Agents documentation, Multi-Agent Orchestrator, AWS Prescriptive Guidance

### Oracle — PARTIALLY MISALIGNS

Oracle's published guidance favors RAG-first, grounding-first approaches over fine-tuning. Oracle provides fine-tuning capability on OCI but their materials lean toward RAG + enterprise data grounding + tool use as the primary customization mechanism for agents.

- Sources: OCI Generative AI Agents documentation, Oracle AI blog

### Assessment

This thesis point reveals a genuine **industry divide**:

**Pro fine-tuning camp:**
- OpenAI (SK Telecom case, RFT for reasoning, function calling fine-tuning)
- Google (Vertex AI fine-tuning docs, Gemini function calling tuning, domain-specific partner models)
- GSMA 6G Whitepaper (parameter-efficient fine-tuning for telecom adaptation)

**Pro RAG/prompting camp:**
- Anthropic (Agent Skills, MCP, prompt engineering first)
- AWS (RAG/knowledge bases as primary domain adaptation)
- Oracle (RAG-first, grounding-first)

**The divide maps to a business model difference:** Anthropic, AWS, and Oracle sell frontier model API access — their incentive is to keep customers on general-purpose models with RAG. OpenAI and Google sell both API access AND fine-tuning/training infrastructure — they benefit from customers investing in domain-specific model training.

**However, the technical argument for fine-tuning is supported by evidence:**
- OpenAI's SK Telecom: +33% intent recognition from fine-tuning
- Consilium's own benchmark: +11.4 pts overall, +19 pts on knowledge and KPI from fine-tuning vs base model
- OpenAI's function calling docs: accuracy degrades as tool complexity increases; fine-tuning addresses this
- The GSMA whitepaper: telecom needs "bounded reasoning, predictable execution, and fast response guarantees" — properties more achievable with a smaller fine-tuned model than a large general-purpose one

---

## What No Vendor Says (Important Gaps)

1. **No vendor explicitly publishes a document titled "how to fine-tune your agent supervisor for a specific domain."** Fine-tuning documentation is agent-role-agnostic — it applies to any model in the system, not specifically to the supervisor.

2. **No vendor provides a head-to-head benchmark comparing rule-based vs ML-based vs LLM-based supervisor performance on the same task set.** Google's scaling paper comes closest by comparing coordination topologies, but not the underlying mechanism type.

3. **No vendor publishes a telecom-specific agentic AI reference architecture with a fine-tuned supervisor.** Google comes closest with the Autonomous Network Operations Framework, but it uses partner models (NetAI) rather than explicitly fine-tuned LLM supervisors.

4. **No vendor explicitly addresses the RAG-vs-fine-tuning tradeoff for the supervisor layer specifically.** Consilium's benchmark data (fine-tuned 84.1% vs fine-tuned+RAG 74.5%) is a novel finding not replicated in any published vendor material.

---

## Key Quotes — Grounded Citations

### On the supervisor/orchestration layer being critical:

> "At the core of any complex agentic system is what's called a 'primary orchestrator,' whose purpose is not to perform the low-level tasks itself, but to manage the workflow, delegate to specialized sub-agents, and interact with the user."
> — Google Cloud Architecture Center

> "Most AI workflows will use a combination of both models — o-series for agentic planning and decision-making, GPT series for task execution."
> — OpenAI, Reasoning Best Practices

> "Each hand is a tool, with an execute(name, input) -> string interface... no hand is coupled to any brain, brains can pass hands to one another."
> — Anthropic, "Scaling Managed Agents" (2025)

### On hybrid architectures:

> "Shifting the reliability burden from the probabilistic LLM to deterministic system design."
> — Google Cloud Architecture Center

> "While a single guardrail is unlikely to provide sufficient protection, using multiple, specialized guardrails together creates more resilient agents."
> — OpenAI, "A Practical Guide to Building Agents"

> "ADK offers flexible orchestration by defining workflows using workflow agents for predictable pipelines, or leveraging LLM-driven dynamic routing for adaptive behavior."
> — Google ADK Documentation

> "Constrained, well-managed agents frequently outperform theoretically superior but poorly governed systems."
> — GSMA 6G Community Whitepaper (Feb 2026)

### On domain fine-tuning:

> "Supervised fine-tuning is particularly effective for domain-specific applications where the language or content significantly differs from the data the large model was originally trained on."
> — Google Cloud, Vertex AI Documentation

> SK Telecom fine-tuning achieved "35% increase in conversation summarization quality" and "33% increase in intent recognition accuracy."
> — OpenAI, Fine-Tuning API Improvements

> "Telecom deployments often require localized adaptation to vendor-specific behaviours, regulatory constraints, and customer policies."
> — GSMA 6G Community Whitepaper (Feb 2026)

### On the alternative view (against fine-tuning as primary approach):

> Routing classification can be handled "either by an LLM or a more traditional classification model/algorithm."
> — Anthropic, "Building Effective Agents"

> Agent Skills provide "composable, scalable, and portable ways to equip agents with domain-specific expertise" — without fine-tuning.
> — Anthropic, "Equipping Agents for the Real World with Agent Skills"

---

## Where Consilium's Thesis Goes Beyond Published Guidance

Three areas where Consilium has generated findings not yet published by any vendor:

### 1. Fine-tuned supervisor outperforms base model for routing/reasoning

Consilium's benchmark shows the fine-tuned v4.1 model (84.1%) outperforms the base Llama 3.1 8B (72.7%) by +11.4 points on operational telecom tasks, with +19 point gains on knowledge and KPI reasoning. No vendor has published an equivalent comparison for the supervisor/routing function specifically.

### 2. RAG can degrade supervisor performance

Consilium's benchmark shows the fine-tuned model WITH RAG (74.5%) scores lower than WITHOUT RAG (84.1%). This counterintuitive finding — that retrieval augmentation can hurt a domain-trained supervisor — has not been published by any of the five vendors researched. It challenges the RAG-first assumptions of Anthropic, AWS, and Oracle.

### 3. Regression-driven micro-patching as training methodology

The iterative approach of benchmarking, identifying specific category gaps, generating targeted corrective data, and micro-patching (v2 -> v4 -> v4.1) is not described in any vendor's fine-tuning documentation. OpenAI's self-evolving agents cookbook comes closest but does not describe the regression-driven data generation methodology.

---

## Honest Assessment: Where the Thesis is Strong and Where It Needs Qualification

### STRONG (universally supported):
- The supervisor/reasoning layer is the most critical component
- Production systems should use hybrid architectures layering deterministic, ML, and LLM approaches
- Domain specificity matters for telecom — generic models are insufficient

### NEEDS QUALIFICATION:
- "Domain fine-tuning of the LLM supervisor is **essential**" is too strong a claim given Anthropic's and AWS's published positions. A more defensible framing:

> "Domain fine-tuning of the LLM supervisor is the **most effective** approach for telecom when latency, cost, deployment constraints, or reasoning accuracy requirements exceed what prompting and RAG can deliver — as demonstrated by Consilium's benchmarks and OpenAI's SK Telecom case study. For organizations with access to frontier model APIs and no edge/cost constraints, prompt engineering + Agent Skills + RAG may be sufficient."

### THE DEFENSIBLE POSITION:
Fine-tuning is not the only path, but it is the highest-leverage intervention when:
- The domain vocabulary differs significantly from general training data (telecom: yes)
- Routing accuracy degrades with tool complexity (OpenAI's own finding)
- Latency/cost requires a smaller model rather than a frontier API (SLM use case)
- RAG retrieval introduces noise rather than helping (Consilium's benchmark finding)
- Edge or air-gapped deployment is needed (no API dependency)

---

## Source Index

### Google / Google DeepMind
- Google "Agents" White Paper (2024) — ppc.land/content/files/2025/01/Newwhitepaper_Agents2.pdf
- Google "Introduction to Agents" White Paper (Nov 2025)
- Google Cloud Architecture Center — "Choose Agentic AI Architecture Components"
- Google Cloud Architecture Center — "Choose Design Pattern for Agentic AI System"
- Google ADK Documentation — google.github.io/adk-docs/
- Google ADK Multi-Agent Systems — google.github.io/adk-docs/agents/multi-agents/
- Google ADK Workflow Agents — google.github.io/adk-docs/agents/workflow-agents/
- "Towards a Science of Scaling Agent Systems" — arXiv:2512.08296
- Google Vertex AI Supervised Tuning — docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning
- Google Cloud "Rise of the Agentic Telco" — MWC 2025
- Google Autonomous Network Operations Framework
- Agent2Agent Protocol — a2a-protocol.org
- AlphaEvolve — arXiv:2506.13131
- Gemini 2.5 Technical Report — arXiv:2507.06261
- GSMA 6G Community Whitepaper (Feb 2026)

### AWS / Amazon
- AWS Prescriptive Guidance — "Agentic AI on AWS"
- Amazon Bedrock Agents Documentation — docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- AWS Multi-Agent Orchestrator — github.com/awslabs/multi-agent-orchestrator
- Amazon Science Research Papers
- AWS re:Invent 2024 Sessions
- AWS Well-Architected Generative AI Lens

### Anthropic
- "Building Effective Agents" (Dec 2024) — anthropic.com/research/building-effective-agents
- "How We Built Our Multi-Agent Research System" (2025) — anthropic.com/engineering/multi-agent-research-system
- "Building Agents with the Claude Agent SDK" (2025)
- "Equipping Agents for the Real World with Agent Skills" (2025)
- "Effective Context Engineering for AI Agents" (2025)
- "Scaling Managed Agents: Decoupling the Brain from the Hands" (2025)
- "Effective Harnesses for Long-Running Agents" (2025)
- Constitutional AI Research
- "Our Framework for Developing Safe and Trustworthy Agents" (2025)
- Model Context Protocol — modelcontextprotocol.io
- Claude Extended Thinking Documentation

### OpenAI
- "A Practical Guide to Building Agents" (2025) — openai.com/business/guides-and-resources/
- OpenAI Agents SDK Documentation — developers.openai.com/api/docs/guides/agents
- OpenAI Swarm (deprecated) — github.com/openai/swarm
- Reasoning Best Practices — developers.openai.com/api/docs/guides/reasoning-best-practices
- Reinforcement Fine-Tuning Guide — platform.openai.com/docs/guides/reinforcement-fine-tuning
- Fine-Tuning for Function Calling — cookbook.openai.com
- SK Telecom Case Study — openai.com/index/introducing-improvements-to-the-fine-tuning-api/
- "Learning to Reason with LLMs" (2024)
- "Introducing o3 and o4-mini" (Apr 2025)
- Self-Evolving Agents Cookbook
- Building Governed AI Agents Cookbook
- Safety in Building Agents Documentation

### Oracle
- OCI Generative AI Agents Documentation — docs.oracle.com/en-us/iaas/Content/generative-ai-agents/
- Oracle CloudWorld 2024 Sessions
- Oracle Communications AI Documentation
- Oracle-Cohere Partnership Materials

---

*Research conducted 2026-04-11. Findings based on published materials available as of that date. All citations are to publicly accessible documents.*
