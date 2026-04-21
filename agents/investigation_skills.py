"""
Consilium — Investigation Skills
Each skill is a specific capability the Investigator can perform.
Skills define which tools to call and how to prompt the SLM for that task.

Skills are data-driven (not hardcoded methods) so new skills can be added
without code changes — either by domain experts or by the Skill Factory.

Architecture:
    Agent → selects skills → each skill calls its tools → SLM analyzes per skill → synthesize all
"""

import json
import logging
from typing import Optional

from agents.tools import execute_tool

logger = logging.getLogger("investigation_skills")

# ─── Skill Definitions ────────────────────────────────────────────────
# Each skill defines:
#   - name: identifier
#   - description: what this skill does (for SLM to decide when to use it)
#   - tools: which tools this skill needs, in order
#   - prompt: skill-specific analysis prompt (SLM sees tool results + this prompt)
#   - output_keys: what this skill produces (fed to next skill or final synthesis)

INVESTIGATION_SKILLS = {
    "triage": {
        "name": "triage",
        "description": "Classify alarm severity and determine escalation path. Use this first when an alarm or incident is reported.",
        "tools": ["alarm_query"],
        "prompt": (
            "Based on the alarm data below, classify:\n"
            "1. Severity: Critical / Major / Minor\n"
            "2. Domain: RAN / Core / Transport / IMS / Power / Security\n"
            "3. Escalation: Who should be notified?\n"
            "4. Urgency: Immediate / Within 1 hour / Within 4 hours\n\n"
            "Alarm data:\n{tool_results}\n\n"
            "Be decisive. Name the severity and domain in the first sentence."
        ),
        "output_keys": ["severity", "domain", "escalation", "urgency"],
    },

    "diagnose": {
        "name": "diagnose",
        "description": "Identify root cause by correlating alarms, KPIs, and network state. Use this after triage when root cause is needed.",
        "tools": ["alarm_query", "kpi_lookup"],
        "prompt": (
            "Based on the alarm and KPI data below, identify the root cause.\n\n"
            "Alarm data:\n{alarm_query_result}\n\n"
            "KPI data:\n{kpi_lookup_result}\n\n"
            "Rules:\n"
            "- Name the specific root cause in the first sentence\n"
            "- Cite specific KPI values as evidence\n"
            "- If alarms and KPIs point to different causes, explain the discrepancy\n"
            "- Do NOT fabricate data you didn't receive"
        ),
        "output_keys": ["root_cause", "evidence", "confidence"],
    },

    "impact_assess": {
        "name": "impact_assess",
        "description": "Determine how many cells, users, and services are affected. Use this when scope of impact needs to be understood.",
        "tools": ["kpi_lookup"],
        "prompt": (
            "Based on the KPI data below, assess the impact:\n\n"
            "KPI data:\n{tool_results}\n\n"
            "Determine:\n"
            "1. How many cells are degraded or down?\n"
            "2. Estimated users affected (from connected_ues counts)\n"
            "3. Which KPIs are below acceptable thresholds?\n"
            "4. Is the degradation spreading or contained?\n"
            "5. SLA risk: any enterprise/priority services affected?"
        ),
        "output_keys": ["cells_affected", "users_affected", "sla_risk", "spreading"],
    },

    "config_check": {
        "name": "config_check",
        "description": "Check if recent configuration changes could have caused the issue. Use this to rule out or confirm change-related faults.",
        "tools": ["config_audit"],
        "prompt": (
            "Based on the configuration audit data below, determine:\n\n"
            "Config data:\n{tool_results}\n\n"
            "1. Were there any recent changes on affected entities?\n"
            "2. Do any changes correlate with the time of incident onset?\n"
            "3. Could any change have caused or contributed to the issue?\n"
            "4. If yes: recommend rollback. If no: rule out config as cause."
        ),
        "output_keys": ["change_found", "correlates_with_incident", "rollback_recommended"],
    },

    "recommend": {
        "name": "recommend",
        "description": "Provide specific, prioritized recovery actions. Use this as the final step after diagnosis and impact are known.",
        "tools": [],  # No tools — synthesizes from prior skill outputs
        "prompt": (
            "Based on the investigation findings below, provide recovery recommendations.\n\n"
            "Findings:\n{prior_results}\n\n"
            "Provide:\n"
            "1. Immediate action (do within 15 minutes)\n"
            "2. Short-term action (do within 1 hour)\n"
            "3. Verification step (how to confirm the fix worked)\n"
            "4. What KPIs to monitor post-fix and target values\n\n"
            "Be specific — give actual commands, parameter values, counter names."
        ),
        "output_keys": ["immediate_action", "short_term_action", "verification", "monitoring"],
    },
}


class SkillExecutor:
    """Executes a single investigation skill — calls its tools and prompts the SLM."""

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    def execute(self, skill_name: str, params: dict, prior_results: dict = None) -> dict:
        """
        Execute a skill.

        Args:
            skill_name: which skill to run
            params: tool parameters (cell_id, site_id, etc.)
            prior_results: output from previously executed skills (for chaining)

        Returns:
            dict with skill output
        """
        skill = INVESTIGATION_SKILLS.get(skill_name)
        if not skill:
            return {"error": f"Unknown skill: {skill_name}"}

        logger.info("Executing skill: %s (tools: %s)", skill_name, skill["tools"])

        # Step 1: Call tools
        tool_results = {}
        for tool_name in skill["tools"]:
            result = execute_tool(tool_name, **params)
            tool_results[tool_name] = result
            logger.info("  Tool %s: %s", tool_name, result.get("summary", "no summary"))

        # Step 2: Build prompt with tool results
        prompt = self._build_prompt(skill, tool_results, prior_results)

        # Step 3: Check if we have any data (guardrail)
        has_data = self._has_meaningful_data(tool_results)

        if not has_data and skill["tools"]:
            # Tools returned nothing — don't ask SLM to analyze empty data
            logger.warning("Skill %s: no data from tools. Skipping SLM analysis.", skill_name)
            return {
                "skill": skill_name,
                "status": "no_data",
                "tool_results": tool_results,
                "analysis": f"No data available for {skill_name}. Tools returned empty results.",
            }

        # Step 4: SLM analysis
        system = "You are Consilium, a telecom network investigation specialist. Be precise and decisive."
        analysis = self.ollama.generate(prompt, system=system)

        return {
            "skill": skill_name,
            "status": "completed",
            "tool_results": tool_results,
            "analysis": analysis,
        }

    def _build_prompt(self, skill: dict, tool_results: dict, prior_results: dict) -> str:
        """Build the skill-specific prompt with tool results injected."""
        prompt = skill["prompt"]

        # Inject individual tool results
        for tool_name, result in tool_results.items():
            key = f"{tool_name}_result"
            prompt = prompt.replace(f"{{{key}}}", json.dumps(result, indent=2)[:1500])

        # Inject combined tool results
        combined = "\n\n".join(
            f"### {name}\n{json.dumps(result, indent=2)[:800]}"
            for name, result in tool_results.items()
        )
        prompt = prompt.replace("{tool_results}", combined)

        # Inject prior skill results
        if prior_results:
            prior_text = "\n\n".join(
                f"### {name}\n{r.get('analysis', 'No analysis')[:500]}"
                for name, r in prior_results.items()
            )
            prompt = prompt.replace("{prior_results}", prior_text)
        else:
            prompt = prompt.replace("{prior_results}", "No prior investigation steps.")

        return prompt

    def _has_meaningful_data(self, tool_results: dict) -> bool:
        """Check if tools returned any meaningful data."""
        for tool_name, result in tool_results.items():
            if "error" in result:
                continue
            if result.get("results") and len(result["results"]) > 0:
                return True
            if result.get("alarms") and len(result["alarms"]) > 0:
                return True
            if result.get("changes") and len(result["changes"]) > 0:
                return True
        return False


class SkillPlanner:
    """Decides which skills to chain for a given investigation query."""

    # Default skill chains for common patterns
    SKILL_CHAINS = {
        "alarm": ["triage", "diagnose", "impact_assess", "config_check", "recommend"],
        "degradation": ["diagnose", "impact_assess", "config_check", "recommend"],
        "compare": ["diagnose", "impact_assess", "config_check", "recommend"],
        "config_change": ["config_check", "diagnose", "recommend"],
        "general": ["triage", "diagnose", "recommend"],
    }

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    def plan(self, query: str) -> list[str]:
        """
        Decide which skills to chain for this query.
        Uses keyword matching first, falls back to SLM if ambiguous.
        """
        query_lower = query.lower()

        # Keyword-based matching (fast, no SLM call)
        if any(w in query_lower for w in ["alarm", "fault", "failure", "down", "outage"]):
            chain = self.SKILL_CHAINS["alarm"]
        elif any(w in query_lower for w in ["degradation", "drop", "slow", "poor", "low throughput"]):
            chain = self.SKILL_CHAINS["degradation"]
        elif any(w in query_lower for w in ["compare", "difference", "vs", "versus"]):
            chain = self.SKILL_CHAINS["compare"]
        elif any(w in query_lower for w in ["config change", "parameter change", "recently changed"]):
            chain = self.SKILL_CHAINS["config_change"]
        else:
            chain = self.SKILL_CHAINS["general"]

        logger.info("Skill plan for query: %s → %s", query[:60], chain)
        return chain
