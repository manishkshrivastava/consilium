"""
Consilium — Agent Factory
Creates candidate agent configurations for unseen domains.

Uses hybrid approach:
- Fixed template skeleton (structure, tool policy, output style)
- SLM fills domain-specific sections (description, keywords, intents, examples)

Lifecycle: generate → validate → store as candidate → promote if useful
"""

import json
import textwrap
import logging
from typing import Optional

from agents.agent_registry import AgentRegistry

logger = logging.getLogger("agent_factory")

# ─── Template Skeleton (fixed — SLM does NOT generate this) ──────────

AGENT_TEMPLATE = textwrap.dedent("""\
    You are Consilium, a telecom network intelligence assistant specializing in {domain_description}.

    Your expertise covers:
    {domain_expertise}

    When answering questions in this domain:
    - Be specific and use exact technical terminology
    - Reference relevant 3GPP specifications where applicable
    - Provide actionable recommendations, not just explanations
    - If you need network data, request it through the available tools
    - If you don't know something, say so — do not fabricate

    Available tools: {tools_description}
""")

# ─── SLM Prompt for Domain Inference ─────────────────────────────────

DOMAIN_INFERENCE_PROMPT = textwrap.dedent("""\
    You are Consilium, analyzing a user query to determine its telecom domain.

    The query does not match any existing specialist agent. Analyze it and extract:

    1. "domain": a short canonical domain label (2-3 words, lowercase, underscore-separated)
       Examples: "spectrum_planning", "energy_optimization", "billing_mediation", "ran_planning"
    2. "name": a human-readable agent name (e.g., "SpectrumPlanningAgent")
    3. "description": one sentence describing what this agent specializes in
    4. "expertise": 3-5 bullet points of specific expertise areas
    5. "keywords": 8-15 routing keywords that would identify queries for this domain
    6. "tools": which tools are relevant — choose from: ["kpi_lookup", "alarm_query", "config_audit"]
       Use empty list [] if no tools are needed (pure knowledge domain)
    7. "example_queries": 3 example queries this agent should handle

    User query: {query}

    Reply with ONLY valid JSON. No other text.
    {{
        "domain": "...",
        "name": "...",
        "description": "...",
        "expertise": ["...", "...", "..."],
        "keywords": ["...", "...", "..."],
        "tools": ["..."],
        "example_queries": ["...", "...", "..."]
    }}
""")


class AgentFactory:
    """
    Creates candidate agent configurations for unseen domains.
    Uses the SLM to infer domain-specific details, then fills a fixed template.
    """

    def __init__(self, ollama_client, registry: AgentRegistry):
        self.ollama = ollama_client
        self.registry = registry
        logger.info("AgentFactory initialized")

    def create_agent_for_query(self, query: str) -> Optional[dict]:
        """
        Analyze a query, infer domain, generate candidate agent config.
        Returns the agent dict if created, None if validation fails or duplicate.
        """
        # Step 1: Ask SLM to infer domain
        logger.info("Inferring domain for: %s", query[:80])
        domain_info = self._infer_domain(query)

        if not domain_info:
            logger.warning("Failed to infer domain from query")
            return None

        # Step 2: Check for duplicate domain
        existing = self.registry.find_similar_domain(
            domain_info["domain"],
            domain_info["keywords"]
        )
        if existing:
            logger.info(
                "Similar agent already exists: %s (domain: %s). Reusing.",
                existing["name"], existing["domain"]
            )
            return existing

        # Step 3: Generate system prompt from template
        system_prompt = self._build_system_prompt(domain_info)

        # Step 4: Save as candidate
        agent = self.registry.create_agent(
            name=domain_info["name"],
            domain=domain_info["domain"],
            description=domain_info["description"],
            system_prompt=system_prompt,
            keywords=domain_info["keywords"],
            tools=domain_info.get("tools", []),
        )

        if agent:
            logger.info(
                "Created candidate agent: %s (id=%d, domain=%s, keywords=%d)",
                agent["name"], agent["id"], agent["domain"], len(agent["keywords"])
            )

        return agent

    def _infer_domain(self, query: str) -> Optional[dict]:
        """Ask the SLM to analyze the query and extract domain info."""
        prompt = DOMAIN_INFERENCE_PROMPT.format(query=query)
        raw = self.ollama.generate(
            prompt,
            system="You are a telecom domain classifier. Reply with ONLY valid JSON."
        )

        try:
            # Extract JSON from response
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                info = json.loads(raw[start:end])

                # Validate required fields
                required = ["domain", "name", "description", "keywords"]
                if all(k in info for k in required):
                    # Normalize domain label
                    info["domain"] = info["domain"].lower().replace(" ", "_").replace("-", "_")
                    # Ensure keywords is a list
                    if isinstance(info["keywords"], str):
                        info["keywords"] = [k.strip() for k in info["keywords"].split(",")]
                    # Ensure tools is a list
                    if "tools" not in info:
                        info["tools"] = []
                    # Ensure expertise is a list
                    if "expertise" not in info:
                        info["expertise"] = [info["description"]]

                    # Expand keywords: break compound terms into individual words too
                    expanded = set()
                    for kw in info["keywords"]:
                        expanded.add(kw.lower())
                        # Break compound terms (underscores, hyphens)
                        for part in kw.replace("_", " ").replace("-", " ").split():
                            if len(part) >= 3:
                                expanded.add(part.lower())
                    # Also add words from domain and description
                    for word in info["domain"].replace("_", " ").split():
                        if len(word) >= 3:
                            expanded.add(word.lower())
                    for word in info["description"].lower().split():
                        if len(word) >= 4 and word not in ("with", "from", "that", "this", "also", "into", "about"):
                            expanded.add(word)
                    info["keywords"] = list(expanded)

                    return info

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to parse domain inference: %s", e)

        return None

    def _build_system_prompt(self, domain_info: dict) -> str:
        """
        Build system prompt using fixed template + SLM-inferred domain details.
        The SLM fills the specialization, not the whole architecture.
        """
        expertise_bullets = "\n    ".join(
            f"- {item}" for item in domain_info.get("expertise", [])
        )

        tools = domain_info.get("tools", [])
        if tools:
            tools_desc = ", ".join(tools)
        else:
            tools_desc = "None — this is a pure knowledge domain"

        prompt = AGENT_TEMPLATE.format(
            domain_description=domain_info["description"],
            domain_expertise=expertise_bullets,
            tools_description=tools_desc,
        )

        return prompt

    def execute_with_agent(self, agent: dict, query: str) -> str:
        """Execute a query using a dynamic agent's system prompt."""
        response = self.ollama.generate(query, system=agent["system_prompt"])
        return response
