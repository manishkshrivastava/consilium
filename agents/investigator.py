"""
Consilium — Investigator Agent (Truly Agentic)
This agent doesn't just answer — it INVESTIGATES using tools + RAG.

Flow:
1. Receives a complex question (e.g., "why was data poor at 3pm in cluster X?")
2. Plans investigation steps (ALWAYS uses all 3 tools + RAG)
3. Calls tools (KPI lookup, alarm query, config audit)
4. Retrieves relevant 3GPP procedures via RAG
5. Analyzes tool results + 3GPP context
6. Synthesizes findings into a diagnosis with standards references

Phase 3B-ii: RAG integration — retrieves 3GPP procedures during investigation
Phase 3B-iii: 3-tool planning — ensures all tools are always used
"""

import json
import textwrap
import time
import logging
from typing import Optional

from agents.tools import TOOL_REGISTRY, get_tool_descriptions, execute_tool

logger = logging.getLogger("investigator")

INVESTIGATION_PLAN_PROMPT = textwrap.dedent("""\
    You are Consilium, an intelligent telecom network investigator.

    The user has asked a question that requires investigation. You have these tools:
    {tool_descriptions}

    Based on the user's question, create an investigation plan as a JSON array.
    Each step should have: "tool" (tool name), "params" (dict of parameters), "reason" (why this step).

    IMPORTANT RULES:
    - You MUST use ALL THREE tools: kpi_lookup, alarm_query, AND config_audit
    - Always start with kpi_lookup to get baseline data
    - Then alarm_query to check for related alarms
    - Then config_audit to check for recent changes that may have caused the issue
    - You may add up to 6 steps total if needed (e.g., for comparing two sites)
    - For COMPARISON queries (e.g., "compare site A and site B"): call kpi_lookup TWICE (once per site), then alarm_query and config_audit for each
    - Extract any cell IDs, cluster names, or time references from the user's question

    User question: {query}

    IMPORTANT parameter rules:
    - Use "cell_id" for a specific cell (e.g., "SITE-METRO-002-S2")
    - Use "site_id" for a whole site (e.g., "SITE-METRO-002") — this returns all 3 sectors
    - Use "region" for a region (e.g., "North", "South", "East", "West")
    - Extract the EXACT cell/site ID from the user's question — do NOT use generic placeholders like "affected"
    - If the user mentions a site name like "SITE-SUBR-001", use that as site_id
    - If the user mentions a cell like "SITE-RURAL-001-S3", use that as cell_id

    Reply with ONLY a JSON array.

    Example (single site):
    [
        {{"tool": "kpi_lookup", "params": {{"site_id": "SITE-METRO-002"}}, "reason": "Check cell KPIs for all sectors at this site"}},
        {{"tool": "alarm_query", "params": {{"site_id": "SITE-METRO-002"}}, "reason": "Check for active and recent alarms at this site"}},
        {{"tool": "config_audit", "params": {{"site_id": "SITE-METRO-002"}}, "reason": "Check for recent config changes at this site"}}
    ]

    Example (comparison):
    [
        {{"tool": "kpi_lookup", "params": {{"site_id": "SITE-METRO-001"}}, "reason": "Get KPIs for first site"}},
        {{"tool": "kpi_lookup", "params": {{"site_id": "SITE-METRO-002"}}, "reason": "Get KPIs for second site"}},
        {{"tool": "alarm_query", "params": {{"site_id": "SITE-METRO-001"}}, "reason": "Check alarms on first site"}},
        {{"tool": "alarm_query", "params": {{"site_id": "SITE-METRO-002"}}, "reason": "Check alarms on second site"}},
        {{"tool": "config_audit", "params": {{"site_id": "SITE-METRO-001"}}, "reason": "Config changes on first site"}},
        {{"tool": "config_audit", "params": {{"site_id": "SITE-METRO-002"}}, "reason": "Config changes on second site"}}
    ]

    JSON plan:""")


ANALYSIS_PROMPT = textwrap.dedent("""\
    You are Consilium, an expert telecom network investigator.

    The user asked: {query}

    You investigated using network tools and found:

    {findings}

    {rag_context}

    Now analyze these findings and provide:
    1. **Root Cause Assessment** — what is the most likely cause based on the data?
    2. **Evidence** — which specific data points support your conclusion?
    3. **Affected Scope** — how many cells/users are impacted?
    4. **3GPP Reference** — ONLY reference documents listed in the "Relevant 3GPP procedures" section above. Do NOT invent or guess spec numbers. If no relevant 3GPP docs were found, say "No specific 3GPP reference available"
    5. **Recommended Actions** — specific, actionable next steps with priority order
    6. **Priority** — Critical / Major / Minor
    7. **What to Monitor** — which KPIs to watch after implementing the fix

    Be specific — reference actual values from the tool results. Don't be generic.
    If config changes were found around the time of the issue, correlate them with the KPI degradation.
    If the data shows conflicting signals, say so and explain what additional investigation is needed.""")


class InvestigatorAgent:
    """
    Truly agentic — plans investigation using skills, calls tools, analyzes results.
    Uses Consilium v4.1 (via Ollama) for planning and analysis.

    Evolution:
    - Phase 3B: Single-step investigation (plan → tools → analyze)
    - Phase 4: Skill-based investigation (triage → diagnose → impact → recommend)

    Skills are defined in investigation_skills.py. Each skill knows which tools
    it needs and has its own analysis prompt. The SLM selects which skills to
    chain based on the query type.
    """

    def __init__(self, ollama_client, rag_retriever=None):
        self.ollama = ollama_client
        self.rag = rag_retriever
        self.tool_descriptions = get_tool_descriptions()

        # Initialize skill framework
        try:
            from agents.investigation_skills import SkillExecutor, SkillPlanner
            self.skill_executor = SkillExecutor(ollama_client)
            self.skill_planner = SkillPlanner(ollama_client)
            self._skills_available = True
            logger.info("Investigation skills framework loaded (5 skills)")
        except Exception as exc:
            logger.warning("Skills framework not available: %s. Using legacy mode.", exc)
            self._skills_available = False

    def investigate(self, query: str) -> dict:
        """
        Investigation flow — uses skill-based approach if available.
        1. Plan skills → 2. Execute skills (each calls its tools) → 3. Synthesize → 4. Report
        Falls back to legacy single-step investigation if skills unavailable.
        """
        if self._skills_available:
            return self._investigate_with_skills(query)
        return self._investigate_legacy(query)

    def _investigate_with_skills(self, query: str) -> dict:
        """Skill-based investigation: chain multiple skills, each with its own tools."""
        t0 = time.time()
        steps_log = []

        # Step 1: Extract entity params from query
        params = self._extract_params(query)
        logger.info("Investigation params: %s", params)

        # Step 2: Plan which skills to chain
        skill_chain = self.skill_planner.plan(query)
        logger.info("Skill chain: %s", " → ".join(skill_chain))
        steps_log.append({"phase": "planning", "skill_chain": skill_chain, "params": params})

        # Step 3: Execute skills in order, passing results forward
        # For comparison queries (multiple entities), run skills per entity then combine
        is_comparison = "site_ids" in params or "cell_ids" in params
        skill_results = {}
        tools_used = set()

        if is_comparison:
            # Comparison mode: run skills for each entity separately
            entities = params.get("site_ids") or params.get("cell_ids", [])
            id_key = "site_id" if "site_ids" in params else "cell_id"
            logger.info("Comparison mode: %d entities (%s)", len(entities), entities)

            for skill_name in skill_chain:
                logger.info("Executing skill: %s (comparison across %d entities)", skill_name, len(entities))
                combined_analysis = []

                for entity_id in entities:
                    entity_params = {id_key: entity_id}
                    result = self.skill_executor.execute(
                        skill_name, entity_params, prior_results=skill_results
                    )

                    for tool_name in result.get("tool_results", {}).keys():
                        tools_used.add(tool_name)

                    combined_analysis.append(f"**{entity_id}:**\n{result.get('analysis', 'No data')}")

                # Combine per-entity results into one skill result
                skill_results[skill_name] = {
                    "skill": skill_name,
                    "status": "completed",
                    "tool_results": {},
                    "analysis": "\n\n".join(combined_analysis),
                }

                steps_log.append({
                    "phase": "skill_execution",
                    "skill": skill_name,
                    "status": "completed",
                    "mode": "comparison",
                    "entities": entities,
                })
        else:
            # Normal mode: run skills with single entity params
            for skill_name in skill_chain:
                logger.info("Executing skill: %s", skill_name)
                result = self.skill_executor.execute(
                    skill_name, params, prior_results=skill_results
                )
                skill_results[skill_name] = result

                # Track tools used
                for tool_name in result.get("tool_results", {}).keys():
                    tools_used.add(tool_name)

                steps_log.append({
                    "phase": "skill_execution",
                    "skill": skill_name,
                    "status": result.get("status"),
                    "analysis_preview": result.get("analysis", "")[:200],
                })

        # Step 4: RAG lookup if available
        rag_context = ""
        rag_sources = []
        if self.rag:
            rag_query = f"3GPP procedure for {query}"
            chunks = self.rag.retrieve(rag_query)
            if chunks:
                rag_parts = []
                for chunk in chunks[:3]:
                    text = chunk.get("text", "")[:400]
                    source = chunk.get("metadata", {}).get("source", "unknown")
                    rag_parts.append(f"[{source}]: {text}")
                    rag_sources.append(source)
                rag_context = "\n\nRelevant 3GPP procedures:\n" + "\n\n".join(rag_parts)

        # Step 4.5: GUARDRAIL — Check if any skill got real data
        skills_with_data = [name for name, r in skill_results.items() if r.get("status") == "completed"]
        skills_no_data = [name for name, r in skill_results.items() if r.get("status") == "no_data"]

        if not skills_with_data or (len(skills_no_data) >= len(skill_results) - 1 and "recommend" in skill_results):
            # All data-gathering skills returned no data — don't synthesize, return guardrail response
            logger.warning("Guardrail: all data skills returned no_data. Skipping synthesis.")
            entity = params.get("cell_id") or params.get("site_id") or "unknown"
            synthesis = (
                f"**Investigation could not complete — insufficient data.**\n\n"
                f"**Entity queried:** {entity}\n"
                f"**Skills attempted:** {', '.join(skill_chain)}\n"
                f"**Skills with data:** {', '.join(skills_with_data) if skills_with_data else 'none'}\n"
                f"**Skills with no data:** {', '.join(skills_no_data)}\n\n"
                f"**Reason:** The cell/site ID '{entity}' was not found in the network inventory. "
                f"All tool queries returned 'Unknown cell_id'.\n\n"
                f"**Recommended next steps:**\n"
                f"1. Verify the cell/site ID exists in the network\n"
                f"2. Check the correct ID format (e.g., SITE-METRO-001-S1)\n"
                f"3. If the ID is correct, check if the data service has this entity loaded\n\n"
                f"**Note:** This response is from the guardrail system, not the SLM, "
                f"to prevent fabricated analysis."
            )
        else:
            # Step 5: Final synthesis — at least some skills got real data
            logger.info("Synthesizing skill results...")
            synthesis = self._synthesize_skills(query, skill_results, rag_context)

        elapsed = time.time() - t0

        return {
            "answer": synthesis,
            "investigation_steps": steps_log,
            "tools_used": list(tools_used) + (["rag_search"] if rag_sources else []),
            "skills_used": skill_chain,
            "findings_count": len(skill_results),
            "rag_sources": rag_sources,
            "elapsed_seconds": round(elapsed, 2),
        }

    def _extract_params(self, query: str) -> dict:
        """Extract cell_id(s), site_id(s) from the query. Handles multiple entities for comparison."""
        import re
        params = {}

        # Find ALL cell IDs (e.g., SITE-METRO-002-S2)
        all_cells = re.findall(r'(SITE-[\w-]+-S\d)', query, re.IGNORECASE)
        # Find ALL site IDs (e.g., SITE-METRO-001)
        all_sites = re.findall(r'(SITE-[\w-]+?)(?:-S\d|\s|$|,|\.)', query, re.IGNORECASE)
        # Deduplicate sites (a cell match also matches as site)
        all_sites = list(dict.fromkeys(all_sites))

        # Also catch plain numeric/text IDs not in SITE- format:
        # "site 31203", "cell id 33456", "cellid 33456", "ENB-33456", "node 33456", "cell 23"
        if not all_cells and not all_sites:
            # With explicit keyword prefix — accept any length number (even 1-2 digits)
            numeric_ids = re.findall(
                r'(?:site|cell|cell_id|cell\s*id|cellid|node|enb|gnb|device|element)\s*[-:]?\s*(\d+)',
                query, re.IGNORECASE
            )
            # Without keyword — only catch 5+ digit numbers (avoid false match on "5G", "3GPP")
            if not numeric_ids:
                numeric_ids = re.findall(r'(?:for|on|at|of|with)\s+(\d{5,})', query, re.IGNORECASE)
            if numeric_ids:
                # Pass as cell_id — data service will validate and return "unknown"
                all_sites = [num_id for num_id in numeric_ids]

        if all_cells:
            if len(all_cells) == 1:
                params["cell_id"] = all_cells[0]
            else:
                params["cell_ids"] = all_cells
                params["cell_id"] = all_cells[0]
        elif all_sites:
            if len(all_sites) == 1:
                params["cell_id"] = all_sites[0]  # Use cell_id — triggers validation
            else:
                params["site_ids"] = all_sites
                params["site_id"] = all_sites[0]

        return params

    def _synthesize_skills(self, query: str, skill_results: dict, rag_context: str) -> str:
        """Combine all skill outputs into a final investigation report."""
        parts = []
        for skill_name, result in skill_results.items():
            status = result.get("status", "unknown")
            analysis = result.get("analysis", "No analysis")
            parts.append(f"### {skill_name.upper()}\n{analysis}")

        findings_text = "\n\n".join(parts)

        synthesis_prompt = (
            f"You are Consilium, synthesizing an investigation report.\n\n"
            f"The user asked: {query}\n\n"
            f"Investigation findings from {len(skill_results)} skills:\n\n"
            f"{findings_text}\n"
            f"{rag_context}\n\n"
            f"Synthesize into a final report with:\n"
            f"1. **Root Cause** — one sentence, decisive\n"
            f"2. **Evidence** — specific data points from the skills\n"
            f"3. **Impact** — cells, users, services affected\n"
            f"4. **Priority** — Critical / Major / Minor\n"
            f"5. **Immediate Action** — what to do right now\n"
            f"6. **Verification** — how to confirm the fix worked\n"
            f"7. **What to Monitor** — KPIs and thresholds\n\n"
            f"Be specific. Reference actual values from the findings. Do NOT fabricate."
        )

        return self.ollama.generate(synthesis_prompt)

    def _investigate_legacy(self, query: str) -> dict:
        """Legacy single-step investigation (fallback if skills unavailable)."""
        t0 = time.time()
        steps_log = []

        # ── Step 1: Plan the investigation ──
        logger.info("Planning investigation...")
        plan_prompt = INVESTIGATION_PLAN_PROMPT.format(
            tool_descriptions=self.tool_descriptions,
            query=query,
        )
        plan_raw = self.ollama.generate(
            plan_prompt,
            system="You are a telecom investigation planner. Reply only with a JSON array. You MUST include all 3 tools.",
        )

        # Parse plan
        plan = self._parse_plan(plan_raw)
        if not plan:
            plan = self._default_plan(query)

        # ── Phase 3B-iii: Ensure all 3 tools are in the plan ──
        plan = self._ensure_all_tools(plan, query)

        logger.info("Investigation plan: %d steps", len(plan))
        steps_log.append({"phase": "planning", "plan": plan})

        # ── Step 2: Execute tools ──
        findings = []
        for i, step in enumerate(plan):
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            reason = step.get("reason", "")

            logger.info("Step %d/%d: %s — %s", i + 1, len(plan), tool_name, reason)

            result = execute_tool(tool_name, **params)
            findings.append({
                "step": i + 1,
                "tool": tool_name,
                "reason": reason,
                "result": result,
            })

            steps_log.append({
                "phase": "execution",
                "step": i + 1,
                "tool": tool_name,
                "params": params,
                "result_summary": result.get("summary", ""),
            })

        # ── Step 3: RAG lookup for relevant 3GPP procedures (Phase 3B-ii) ──
        rag_context = ""
        rag_sources = []
        if self.rag:
            logger.info("Retrieving relevant 3GPP procedures via RAG...")
            rag_query = self._build_rag_query(query, findings)
            chunks = self.rag.retrieve(rag_query)

            if chunks:
                rag_parts = []
                for chunk in chunks[:3]:  # Top 3 chunks
                    text = chunk.get("text", "")[:400]
                    source = chunk.get("metadata", {}).get("source", "unknown")
                    rag_parts.append(f"[{source}]: {text}")
                    rag_sources.append(source)

                rag_context = (
                    "Relevant 3GPP procedures found:\n\n"
                    + "\n\n".join(rag_parts)
                )
                logger.info("RAG retrieved %d relevant 3GPP chunks", len(chunks))

                steps_log.append({
                    "phase": "rag_retrieval",
                    "chunks_retrieved": len(chunks),
                    "sources": rag_sources,
                })
            else:
                logger.info("No relevant 3GPP procedures found via RAG")
                rag_context = "No specific 3GPP procedures found for this issue."
        else:
            rag_context = "RAG not available — analysis based on tool findings only."

        # ── Step 3.5: GUARDRAIL — Validate data before SLM analysis ──
        data_quality = self._assess_data_quality(findings)
        logger.info("Data quality assessment: %s", data_quality["verdict"])

        if data_quality["verdict"] == "NO_DATA":
            # Don't send empty data to SLM — it will hallucinate
            analysis = self._no_data_response(query, data_quality)
            steps_log.append({"phase": "guardrail", "verdict": "NO_DATA", "reason": data_quality["reason"]})
            logger.warning("Guardrail triggered: no meaningful data from tools. Skipping SLM analysis.")

        elif data_quality["verdict"] == "PARTIAL_DATA":
            # Warn the SLM that data is incomplete
            logger.info("Partial data — adding caveat to SLM prompt")
            findings_text = self._format_findings(findings)
            caveat = (
                "\n\n**DATA QUALITY WARNING:** Some tools returned empty or incomplete results. "
                "Only analyze data you actually received. Do NOT invent or fabricate data points. "
                "If a tool returned no results, say 'no data available from [tool name]' — do not guess.\n"
            )
            analysis_prompt = ANALYSIS_PROMPT.format(
                query=query,
                findings=findings_text + caveat,
                rag_context=rag_context,
            )
            analysis = self.ollama.generate(analysis_prompt)
            steps_log.append({"phase": "analysis", "data_quality": "partial", "conclusion": analysis[:200]})

        else:
            # Full data available — normal analysis
            logger.info("Analyzing findings...")
            findings_text = self._format_findings(findings)
            analysis_prompt = ANALYSIS_PROMPT.format(
                query=query,
                findings=findings_text,
                rag_context=rag_context,
            )
            analysis = self.ollama.generate(analysis_prompt)
            steps_log.append({"phase": "analysis", "data_quality": "full", "conclusion": analysis[:200]})

        elapsed = time.time() - t0

        return {
            "answer": analysis,
            "investigation_steps": steps_log,
            "tools_used": [s["tool"] for s in plan] + (["rag_search"] if rag_sources else []),
            "findings_count": len(findings),
            "rag_sources": rag_sources,
            "elapsed_seconds": round(elapsed, 2),
        }

    def _ensure_all_tools(self, plan: list, query: str) -> list:
        """
        Phase 3B-iii: Guarantee all 3 tools are in the plan.
        If the SLM planner missed a tool, add it with sensible defaults.
        """
        required_tools = {"kpi_lookup", "alarm_query", "config_audit"}
        tools_in_plan = {step.get("tool") for step in plan}
        missing_tools = required_tools - tools_in_plan

        if not missing_tools:
            return plan  # All tools already present

        logger.info("Adding missing tools to plan: %s", missing_tools)

        # Extract identifiers from existing plan steps
        default_params = {}
        for step in plan:
            params = step.get("params", {})
            if params.get("cell_id"):
                default_params["cell_id"] = params["cell_id"]
            if params.get("site_id"):
                default_params["site_id"] = params["site_id"]
            if params.get("region"):
                default_params["region"] = params["region"]

        # Add missing tools using the same identifiers
        tool_defaults = {
            "kpi_lookup": {
                "params": dict(default_params),
                "reason": "Check cell KPIs during the affected time period",
            },
            "alarm_query": {
                "params": dict(default_params),
                "reason": "Check for alarms raised around the time of the issue",
            },
            "config_audit": {
                "params": dict(default_params),
                "reason": "Check for configuration changes that could have caused the issue",
            },
        }

        for tool_name in missing_tools:
            defaults = tool_defaults[tool_name]
            plan.append({
                "tool": tool_name,
                "params": defaults["params"],
                "reason": defaults["reason"] + " (auto-added — planner missed this tool)",
            })

        # Sort: kpi_lookup first, alarm_query second, config_audit third
        tool_order = {"kpi_lookup": 0, "alarm_query": 1, "config_audit": 2}
        plan.sort(key=lambda s: tool_order.get(s.get("tool", ""), 99))

        return plan

    def _build_rag_query(self, query: str, findings: list) -> str:
        """
        Phase 3B-ii: Build a RAG search query based on investigation findings.
        Searches for relevant 3GPP procedures based on what the tools found.
        """
        # Extract key issues from findings
        issues = []

        for f in findings:
            result = f.get("result", {})

            if f["tool"] == "kpi_lookup":
                for cell in result.get("results", []):
                    if cell.get("status") == "DEGRADED":
                        metrics = cell.get("metrics", {})
                        if metrics.get("prb_utilization_dl_pct", 0) > 80:
                            issues.append("PRB congestion capacity management")
                        if metrics.get("sinr_avg_db", 99) < 5:
                            issues.append("interference management SINR degradation")
                        if metrics.get("erab_drop_rate_pct", 0) > 1:
                            issues.append("ERAB drop bearer release procedure")
                        if metrics.get("rrc_setup_success_pct", 100) < 95:
                            issues.append("RRC connection setup failure")
                        if metrics.get("ul_interference_dbm", -120) > -100:
                            issues.append("uplink interference detection mitigation")

            elif f["tool"] == "alarm_query":
                for alarm in result.get("alarms", []):
                    alarm_type = alarm.get("type", "")
                    if "INTERFERENCE" in alarm_type:
                        issues.append("3GPP interference management procedure")
                    elif "S1" in alarm_type or "LINK" in alarm_type:
                        issues.append("S1 interface failure recovery procedure")
                    elif "VSWR" in alarm_type:
                        issues.append("antenna fault detection VSWR")
                    elif "CPU" in alarm_type:
                        issues.append("eNodeB overload control")

        if not issues:
            # Generic RAG query based on user's original question
            return f"3GPP procedure for {query}"

        # Combine top issues into a RAG query
        return " ".join(issues[:3])

    def _parse_plan(self, raw: str) -> list:
        """Parse the SLM's investigation plan from JSON."""
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                plan = json.loads(raw[start:end])
                valid = []
                for step in plan:
                    if isinstance(step, dict) and "tool" in step:
                        if step["tool"] in TOOL_REGISTRY:
                            valid.append(step)
                return valid[:6]
        except (json.JSONDecodeError, ValueError):
            pass
        return []

    def _default_plan(self, query: str) -> list:
        """Fallback plan if SLM doesn't produce valid JSON. Tries to extract IDs from query."""
        import re
        # Try to extract cell or site ID from the query
        params = {}
        cell_match = re.search(r'(SITE-[\w-]+-S\d)', query, re.IGNORECASE)
        site_match = re.search(r'(SITE-[\w-]+?)(?:-S\d|$|\s)', query, re.IGNORECASE)
        if cell_match:
            params["cell_id"] = cell_match.group(1)
        elif site_match:
            params["site_id"] = site_match.group(1)

        return [
            {
                "tool": "kpi_lookup",
                "params": dict(params),
                "reason": "Check cell KPIs during the affected time period",
            },
            {
                "tool": "alarm_query",
                "params": dict(params),
                "reason": "Check for alarms raised around the time of the issue",
            },
            {
                "tool": "config_audit",
                "params": dict(params),
                "reason": "Check for any configuration changes before the issue",
            },
        ]

    def _format_findings(self, findings: list) -> str:
        """Format tool results into readable text for the SLM analysis step."""
        parts = []
        for f in findings:
            parts.append(f"### Step {f['step']}: {f['tool']} — {f['reason']}")

            result = f["result"]
            if "error" in result:
                parts.append(f"ERROR: {result['error']}")
                continue

            parts.append(f"Summary: {result.get('summary', 'No summary')}")

            if f["tool"] == "kpi_lookup":
                for cell_data in result.get("results", []):
                    status = cell_data.get("status", "UNKNOWN")
                    cell_id = cell_data.get("cell_id", "?")
                    parts.append(f"\n**{cell_id}** [{status}]:")
                    for metric, value in cell_data.get("metrics", {}).items():
                        parts.append(f"  - {metric}: {value}")

            elif f["tool"] == "alarm_query":
                for alarm in result.get("alarms", []):
                    parts.append(
                        f"  - [{alarm['severity']}] {alarm['type']} on {alarm['affected_element']} "
                        f"at {alarm['raised_time']} — {alarm['description']} "
                        f"({alarm['status']})"
                    )
                if not result.get("alarms"):
                    parts.append("  No alarms found in this time window.")

            elif f["tool"] == "config_audit":
                for change in result.get("changes", []):
                    param = change.get("parameter") or change.get("param", "?")
                    old_val = change.get("old_value") or change.get("old", "?")
                    new_val = change.get("new_value") or change.get("new", "?")
                    changed_by = change.get("changed_by", "?")
                    change_time = change.get("change_time") or change.get("time", "?")
                    reason = change.get("reason", "")
                    parts.append(
                        f"  - {param}: {old_val} → {new_val} "
                        f"by {changed_by} at {change_time} "
                        f"(reason: {reason})"
                    )
                if not result.get("changes"):
                    parts.append("  No configuration changes found in this time window.")

            parts.append("")

        return "\n".join(parts)

    def _assess_data_quality(self, findings: list) -> dict:
        """
        GUARDRAIL: Check if tools returned meaningful data before sending to SLM.
        Prevents hallucination when tools return empty results.
        """
        kpi_cells = 0
        kpi_degraded = 0
        alarm_count = 0
        config_changes = 0
        tool_errors = 0
        tools_with_data = 0

        for f in findings:
            result = f.get("result", {})

            if "error" in result:
                tool_errors += 1
                continue

            if f["tool"] == "kpi_lookup":
                cells = result.get("results", [])
                kpi_cells += len(cells)
                kpi_degraded += sum(1 for c in cells if c.get("status") in ("DEGRADED", "CRITICAL"))
                if cells:
                    tools_with_data += 1

            elif f["tool"] == "alarm_query":
                alarms = result.get("alarms", [])
                alarm_count += len(alarms)
                if alarms:
                    tools_with_data += 1

            elif f["tool"] == "config_audit":
                changes = result.get("changes", [])
                config_changes += len(changes)
                # Only count baseline as data if it has overrides (actual changes)
                baseline = result.get("baseline")
                if changes:
                    tools_with_data += 1
                elif baseline and baseline.get("overrides"):
                    tools_with_data += 1

        # Determine verdict
        if kpi_cells == 0 and alarm_count == 0 and config_changes == 0 and tool_errors == 0:
            return {
                "verdict": "NO_DATA",
                "reason": "All tools returned empty results. The cell/site ID may not exist or the data service may be unreachable.",
                "kpi_cells": 0, "alarms": 0, "config_changes": 0, "errors": 0,
            }

        if tool_errors > 0 and tools_with_data == 0:
            return {
                "verdict": "NO_DATA",
                "reason": f"{tool_errors} tool(s) returned errors and no tool returned usable data.",
                "kpi_cells": kpi_cells, "alarms": alarm_count, "config_changes": config_changes, "errors": tool_errors,
            }

        if tools_with_data < 2:
            return {
                "verdict": "PARTIAL_DATA",
                "reason": f"Only {tools_with_data}/3 tools returned data. Analysis may be incomplete.",
                "kpi_cells": kpi_cells, "alarms": alarm_count, "config_changes": config_changes, "errors": tool_errors,
            }

        return {
            "verdict": "FULL_DATA",
            "reason": "All tools returned data.",
            "kpi_cells": kpi_cells, "kpi_degraded": kpi_degraded,
            "alarms": alarm_count, "config_changes": config_changes, "errors": tool_errors,
        }

    def _no_data_response(self, query: str, data_quality: dict) -> str:
        """
        GUARDRAIL: Return a structured response WITHOUT calling the SLM.
        Used when tools returned no meaningful data.
        """
        return (
            f"**Investigation could not complete — insufficient data.**\n\n"
            f"**Reason:** {data_quality['reason']}\n\n"
            f"**Data retrieved:**\n"
            f"- KPI results: {data_quality.get('kpi_cells', 0)} cells\n"
            f"- Alarms found: {data_quality.get('alarms', 0)}\n"
            f"- Config changes: {data_quality.get('config_changes', 0)}\n"
            f"- Tool errors: {data_quality.get('errors', 0)}\n\n"
            f"**Recommended next steps:**\n"
            f"1. Verify the cell/site ID exists in the network inventory\n"
            f"2. Check if the Telecom Data Service is running (port 3003)\n"
            f"3. Try querying a specific cell ID (e.g., SITE-METRO-001-S1) instead of a broad query\n"
            f"4. If the ID is correct, escalate to the NOC for manual investigation\n\n"
            f"**Note:** This response is generated by the guardrail system, not the SLM, "
            f"to prevent fabricated analysis when no real data is available."
        )
