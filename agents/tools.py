"""
Consilium — Agent Tools
Connect to the Telecom Data Service for KPI, alarm, and config data.
Falls back to direct generation if the data service is unavailable.
"""

import json
import random
import time
from datetime import datetime
from typing import Optional

# Data service URL
DATA_SERVICE_URL = "http://localhost:3003"


def _call_service(endpoint: str, params: dict = None) -> Optional[dict]:
    """Call the telecom data service. Returns None if unavailable."""
    try:
        import httpx
        url = f"{DATA_SERVICE_URL}{endpoint}"
        resp = httpx.get(url, params={k: v for k, v in (params or {}).items() if v is not None}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


# =============================================================================
# Tool: KPI Lookup
# =============================================================================
class KPILookupTool:
    """
    Queries cell-level KPIs from the Telecom Data Service.
    Falls back to basic generation if service is down.
    """

    name = "kpi_lookup"
    description = "Look up network performance KPIs for a specific cell, site, or region. Returns metrics like throughput, PRB utilization, SINR, ERAB drop rate, handover success rate."

    def run(self, cell_id: str = None, cluster: str = None,
            site_id: str = None, region: str = None,
            time_from: str = None, time_to: str = None,
            metrics: list[str] = None) -> dict:
        # Try data service first — accept both old "cluster" and new "site_id"/"region" params
        effective_site_id = site_id or cluster
        params = {"cell_id": cell_id, "site_id": effective_site_id, "region": region}
        if time_from:
            try:
                hour = int(time_from.split(" ")[1].split(":")[0])
                params["hour"] = hour
            except (IndexError, ValueError):
                pass

        result = _call_service("/kpi", params)
        if result:
            return result

        # Fallback: basic generation
        return {
            "tool": "kpi_lookup",
            "query": {"cell_id": cell_id, "cluster": cluster},
            "results": [{"cell_id": cell_id or "UNKNOWN", "status": "SERVICE_UNAVAILABLE", "metrics": {}}],
            "summary": "Data service unavailable — no KPI data returned.",
        }


# =============================================================================
# Tool: Alarm Query
# =============================================================================
class AlarmQueryTool:
    """
    Queries alarms from the Telecom Data Service.
    Falls back to empty result if service is down.
    """

    name = "alarm_query"
    description = "Search for active or historical alarms for specific cells, sites, or regions. Returns alarm type, severity, time, affected element, and probable cause."

    def run(self, cell_id: str = None, cluster: str = None,
            site_id: str = None, region: str = None,
            time_from: str = None, time_to: str = None,
            severity: str = None, status: str = None) -> dict:
        # Normalize: accept both old "cluster" and new "site_id"/"region" params
        effective_site_id = site_id or cluster
        params = {
            "cell_id": cell_id,
            "site_id": effective_site_id,
            "region": region,
            "severity": severity,
            "status": status,
        }

        result = _call_service("/alarms", params)
        if result:
            return result

        return {
            "tool": "alarm_query",
            "query": {"cell_id": cell_id, "site_id": effective_site_id, "region": region},
            "alarms": [],
            "summary": "Data service unavailable — no alarm data returned.",
        }


# =============================================================================
# Tool: Config Audit
# =============================================================================
class ConfigAuditTool:
    """
    Queries configuration baselines and recent changes from the Telecom Data Service.
    Falls back to empty result if service is down.
    """

    name = "config_audit"
    description = "Check configuration baselines and recent changes for a cell or site. Returns parameter values, deviations from standard, and change history."

    def run(self, cell_id: str = None, element: str = None,
            site_id: str = None,
            time_from: str = None, time_to: str = None) -> dict:
        params = {
            "cell_id": cell_id or element,
            "site_id": site_id,
        }

        result = _call_service("/config", params)
        if result:
            return result

        return {
            "tool": "config_audit",
            "query": {"cell_id": cell_id, "site_id": site_id},
            "baseline": None,
            "changes": [],
            "summary": "Data service unavailable — no config data returned.",
        }


# =============================================================================
# Tool Registry
# =============================================================================
TOOL_REGISTRY = {
    "kpi_lookup": KPILookupTool(),
    "alarm_query": AlarmQueryTool(),
    "config_audit": ConfigAuditTool(),
}


def get_tool_descriptions() -> str:
    """Return formatted tool descriptions for the LLM prompt."""
    descriptions = []
    for name, tool in TOOL_REGISTRY.items():
        descriptions.append(f"- **{name}**: {tool.description}")
    return "\n".join(descriptions)


def execute_tool(tool_name: str, **kwargs) -> dict:
    """Execute a tool by name and return results."""
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return tool.run(**kwargs)
    except Exception as e:
        return {"error": f"Tool execution failed: {e}"}
