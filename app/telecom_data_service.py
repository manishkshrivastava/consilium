"""
Consilium — Telecom Data Service (Tier 1)
Serves realistic synthetic KPI, alarm, and config data via REST API.
Follows TM Forum API patterns (TMF628, TMF642, TMF639).

Usage:
    uvicorn app.telecom_data_service:app --port 3003
"""

import math
import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Query

app = FastAPI(
    title="Consilium Telecom Data Service",
    description="Synthetic telecom network data: KPIs, alarms, configurations. TM Forum-aligned.",
    version="1.0.0",
)

# =============================================================================
# NETWORK TOPOLOGY — persistent cell/site definitions
# =============================================================================

SITES = [
    {"site_id": "SITE-METRO-001", "name": "Metro Tower Alpha", "region": "North", "type": "macro", "lat": 40.7128, "lon": -74.0060},
    {"site_id": "SITE-METRO-002", "name": "Metro Tower Beta", "region": "North", "type": "macro", "lat": 40.7580, "lon": -73.9855},
    {"site_id": "SITE-METRO-003", "name": "Metro Tower Gamma", "region": "North", "type": "macro", "lat": 40.7484, "lon": -73.9857},
    {"site_id": "SITE-SUBR-001", "name": "Suburban Hub East", "region": "East", "type": "macro", "lat": 40.6892, "lon": -74.0445},
    {"site_id": "SITE-SUBR-002", "name": "Suburban Hub West", "region": "West", "type": "macro", "lat": 40.7282, "lon": -74.0776},
    {"site_id": "SITE-SUBR-003", "name": "Suburban Hub South", "region": "South", "type": "macro", "lat": 40.6501, "lon": -73.9496},
    {"site_id": "SITE-RURAL-001", "name": "Rural Site Delta", "region": "South", "type": "rural", "lat": 40.5795, "lon": -74.1502},
    {"site_id": "SITE-RURAL-002", "name": "Rural Site Echo", "region": "East", "type": "rural", "lat": 40.6340, "lon": -74.2107},
    {"site_id": "SITE-INDOOR-001", "name": "Mall Indoor DAS", "region": "North", "type": "indoor", "lat": 40.7505, "lon": -73.9934},
    {"site_id": "SITE-INDOOR-002", "name": "Stadium Indoor DAS", "region": "North", "type": "indoor", "lat": 40.7614, "lon": -73.9776},
]

# Generate 3 cells per site (sectors)
CELLS = []
for site in SITES:
    for sector in range(1, 4):
        cell_id = f"{site['site_id']}-S{sector}"
        CELLS.append({
            "cell_id": cell_id,
            "site_id": site["site_id"],
            "site_name": site["name"],
            "region": site["region"],
            "sector": sector,
            "band": random.choice(["B1-2100", "B3-1800", "B7-2600", "n78-3500", "n1-2100"]),
            "technology": "5G NR" if "n" in random.choice(["B1", "n78"]) else "LTE",
            "bandwidth_mhz": random.choice([10, 20, 40, 100]),
            "azimuth": (sector - 1) * 120,
            "site_type": site["type"],
        })

CELL_IDS = [c["cell_id"] for c in CELLS]
CELL_LOOKUP = {c["cell_id"]: c for c in CELLS}


# =============================================================================
# KPI GENERATOR — deterministic, time-based, with anomalies
# =============================================================================

def _seed_for(cell_id: str, hour: int, day: int) -> int:
    """Deterministic seed so same query returns same data."""
    h = hashlib.md5(f"{cell_id}-{hour}-{day}".encode()).hexdigest()
    return int(h[:8], 16)


def _diurnal_factor(hour: int) -> float:
    """Traffic pattern: low at night, peak at 9-11 and 17-20."""
    return 0.2 + 0.8 * (
        0.3 * math.exp(-((hour - 10) ** 2) / 8) +
        0.4 * math.exp(-((hour - 18) ** 2) / 10) +
        0.3 * math.exp(-((hour - 14) ** 2) / 20)
    )


# Active anomalies — simulates ongoing issues
ACTIVE_ANOMALIES = {
    "SITE-METRO-002-S2": {"type": "interference", "start_hour": 8, "end_hour": 22, "severity": "major"},
    "SITE-SUBR-001-S1": {"type": "backhaul_degradation", "start_hour": 0, "end_hour": 23, "severity": "major"},
    "SITE-RURAL-001-S3": {"type": "hw_fault", "start_hour": 0, "end_hour": 23, "severity": "critical"},
    "SITE-INDOOR-002-S1": {"type": "congestion", "start_hour": 10, "end_hour": 21, "severity": "major"},
}


def generate_kpi(cell_id: str, hour: int, day: int = 0) -> dict:
    """Generate realistic KPIs for a cell at a specific hour."""
    rng = random.Random(_seed_for(cell_id, hour, day))
    cell = CELL_LOOKUP.get(cell_id, {})
    traffic = _diurnal_factor(hour)
    anomaly = ACTIVE_ANOMALIES.get(cell_id)
    is_anomalous = anomaly and anomaly["start_hour"] <= hour <= anomaly["end_hour"]

    # Base values by site type
    base_sinr = {"macro": 15, "rural": 10, "indoor": 18}.get(cell.get("site_type", "macro"), 15)
    base_rsrp = {"macro": -78, "rural": -92, "indoor": -70}.get(cell.get("site_type", "macro"), -78)
    bw = cell.get("bandwidth_mhz", 20)

    # Normal KPIs
    sinr = base_sinr + rng.uniform(-3, 3)
    rsrp = base_rsrp + rng.uniform(-5, 5)
    prb_dl = min(95, 15 + 60 * traffic + rng.uniform(-5, 5))
    prb_ul = min(85, 10 + 40 * traffic + rng.uniform(-3, 3))
    connected = int(30 + 300 * traffic + rng.uniform(-20, 20))
    active = int(connected * rng.uniform(0.3, 0.6))
    dl_tp = bw * 3.5 * (sinr / 20) * (1 - prb_dl / 200) + rng.uniform(-5, 5)
    ul_tp = bw * 1.2 * (sinr / 20) * (1 - prb_ul / 200) + rng.uniform(-2, 2)
    erab_drop = 0.1 + rng.uniform(0, 0.5) + 0.5 * traffic
    rrc_success = 99.0 - rng.uniform(0, 1.5) - 1.5 * traffic
    ho_success = 97.0 - rng.uniform(0, 2) - 1.0 * traffic
    bler = 2.0 + rng.uniform(0, 3) + 2 * traffic
    ul_interference = -105 + rng.uniform(0, 5) + 3 * traffic

    # Apply anomaly effects
    if is_anomalous:
        atype = anomaly["type"]
        if atype == "interference":
            sinr -= 12
            bler += 10
            dl_tp *= 0.35
            ul_interference += 15
        elif atype == "backhaul_degradation":
            dl_tp *= 0.4
            ul_tp *= 0.4
            erab_drop += 3.0
        elif atype == "hw_fault":
            rrc_success -= 12
            erab_drop += 5.0
            ho_success -= 15
            connected = int(connected * 0.3)
        elif atype == "congestion":
            prb_dl = min(98, prb_dl + 25)
            prb_ul = min(90, prb_ul + 15)
            dl_tp *= 0.5
            connected = int(connected * 1.8)

    status = "NORMAL"
    if is_anomalous:
        status = "DEGRADED" if anomaly["severity"] == "major" else "CRITICAL"
    elif erab_drop > 2.0 or rrc_success < 95 or sinr < 5:
        status = "WARNING"

    return {
        "cell_id": cell_id,
        "site_id": cell.get("site_id", ""),
        "region": cell.get("region", ""),
        "hour": hour,
        "status": status,
        "metrics": {
            "dl_throughput_mbps": round(max(0, dl_tp), 1),
            "ul_throughput_mbps": round(max(0, ul_tp), 1),
            "prb_utilization_dl_pct": round(max(0, min(100, prb_dl)), 1),
            "prb_utilization_ul_pct": round(max(0, min(100, prb_ul)), 1),
            "sinr_avg_db": round(sinr, 1),
            "rsrp_avg_dbm": round(rsrp, 1),
            "connected_ues": max(0, connected),
            "active_ues": max(0, active),
            "erab_drop_rate_pct": round(max(0, erab_drop), 2),
            "rrc_setup_success_pct": round(max(0, min(100, rrc_success)), 1),
            "ho_success_rate_pct": round(max(0, min(100, ho_success)), 1),
            "bler_dl_pct": round(max(0, bler), 1),
            "ul_interference_dbm": round(ul_interference, 1),
        },
    }


# =============================================================================
# ALARM DATABASE — persistent, correlated with anomalies
# =============================================================================

ALARM_DB = []

def _init_alarms():
    """Generate alarm history correlated with active anomalies."""
    global ALARM_DB
    now = datetime.now()

    # Alarms from active anomalies
    alarm_id = 100000
    for cell_id, anomaly in ACTIVE_ANOMALIES.items():
        cell = CELL_LOOKUP.get(cell_id, {})
        site_id = cell.get("site_id", "")

        if anomaly["type"] == "interference":
            ALARM_DB.append({
                "alarm_id": f"ALM-{alarm_id}",
                "type": "UL_INTERFERENCE_HIGH",
                "severity": "Major",
                "domain": "RAN",
                "description": f"Uplink interference increased by 15dB on {cell_id}. External interference source suspected.",
                "affected_element": cell_id,
                "site_id": site_id,
                "raised_time": (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
                "cleared_time": None,
                "status": "ACTIVE",
                "probable_cause": "External interference from adjacent operator or illegal repeater",
            })
            alarm_id += 1
            ALARM_DB.append({
                "alarm_id": f"ALM-{alarm_id}",
                "type": "HIGH_BLER",
                "severity": "Major",
                "domain": "RAN",
                "description": f"DL BLER exceeded 12% on {cell_id}. Correlated with UL interference alarm.",
                "affected_element": cell_id,
                "site_id": site_id,
                "raised_time": (now - timedelta(hours=5, minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
                "cleared_time": None,
                "status": "ACTIVE",
                "probable_cause": "SINR degradation from external interference causing modulation downgrade",
            })
            alarm_id += 1

        elif anomaly["type"] == "backhaul_degradation":
            ALARM_DB.append({
                "alarm_id": f"ALM-{alarm_id}",
                "type": "PACKET_LOSS_BACKHAUL",
                "severity": "Major",
                "domain": "Transport",
                "description": f"Packet loss 4.2% on microwave backhaul link to {site_id}. RSL dropping.",
                "affected_element": site_id,
                "site_id": site_id,
                "raised_time": (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
                "cleared_time": None,
                "status": "ACTIVE",
                "probable_cause": "Microwave link fade margin violation — check RSL and weather conditions",
            })
            alarm_id += 1
            ALARM_DB.append({
                "alarm_id": f"ALM-{alarm_id}",
                "type": "THROUGHPUT_DEGRADATION",
                "severity": "Major",
                "domain": "RAN",
                "description": f"DL throughput dropped 60% on cells at {site_id}. Backhaul bottleneck.",
                "affected_element": cell_id,
                "site_id": site_id,
                "raised_time": (now - timedelta(hours=11, minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                "cleared_time": None,
                "status": "ACTIVE",
                "probable_cause": "Backhaul capacity limitation causing TCP retransmissions",
            })
            alarm_id += 1

        elif anomaly["type"] == "hw_fault":
            ALARM_DB.append({
                "alarm_id": f"ALM-{alarm_id}",
                "type": "BOARD_FAULT",
                "severity": "Critical",
                "domain": "RAN",
                "description": f"Baseband board fault on {cell_id}. RRC setup failures increasing.",
                "affected_element": cell_id,
                "site_id": site_id,
                "raised_time": (now - timedelta(days=1, hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
                "cleared_time": None,
                "status": "ACTIVE",
                "probable_cause": "Hardware failure — baseband processing unit needs replacement",
            })
            alarm_id += 1

        elif anomaly["type"] == "congestion":
            ALARM_DB.append({
                "alarm_id": f"ALM-{alarm_id}",
                "type": "PRB_CONGESTION",
                "severity": "Major",
                "domain": "RAN",
                "description": f"DL PRB utilization exceeded 95% on {cell_id} during event hours.",
                "affected_element": cell_id,
                "site_id": site_id,
                "raised_time": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
                "cleared_time": None,
                "status": "ACTIVE",
                "probable_cause": "High user density during stadium event — capacity expansion needed",
            })
            alarm_id += 1

    # Add some cleared historical alarms
    for i in range(8):
        rng = random.Random(42 + i)
        cell = rng.choice(CELLS)
        alarm_templates = [
            ("HIGH_CPU_UTILIZATION", "Major", "RAN", "CPU utilization exceeded 90% threshold"),
            ("S1_LINK_FAILURE", "Critical", "Core", "S1 interface connectivity lost temporarily"),
            ("HIGH_VSWR", "Critical", "RAN", "Antenna VSWR exceeded threshold — connector issue"),
            ("PTP_SYNC_LOSS", "Critical", "Transport", "PTP synchronization lost for 45 seconds"),
            ("TEMP_ALARM", "Warning", "RAN", "Site temperature above 35°C"),
            ("CONFIG_MISMATCH", "Warning", "OAM", "Running config differs from planned config"),
            ("RACH_FAILURE_HIGH", "Major", "RAN", "RACH failure rate exceeded 10% — preamble conflict"),
            ("LICENSE_EXPIRY_WARNING", "Warning", "OAM", "Feature license expiring in 7 days"),
        ]
        template = alarm_templates[i % len(alarm_templates)]
        raised = now - timedelta(days=rng.randint(1, 7), hours=rng.randint(0, 23))
        ALARM_DB.append({
            "alarm_id": f"ALM-{alarm_id + i}",
            "type": template[0],
            "severity": template[1],
            "domain": template[2],
            "description": f"{template[3]} on {cell['cell_id']}",
            "affected_element": cell["cell_id"],
            "site_id": cell["site_id"],
            "raised_time": raised.strftime("%Y-%m-%d %H:%M:%S"),
            "cleared_time": (raised + timedelta(minutes=rng.randint(15, 180))).strftime("%Y-%m-%d %H:%M:%S"),
            "status": "CLEARED",
            "probable_cause": template[3],
        })

_init_alarms()


# =============================================================================
# CONFIG DATABASE — baseline + recent changes
# =============================================================================

CONFIG_BASELINES = {
    "dl_tx_power": {"value": "46 dBm", "standard": "43-49 dBm"},
    "antenna_tilt": {"value": "4 deg", "standard": "2-8 deg"},
    "a3_offset": {"value": "3 dB", "standard": "2-5 dB"},
    "a3_hysteresis": {"value": "1 dB", "standard": "0.5-2 dB"},
    "a3_time_to_trigger": {"value": "320 ms", "standard": "160-640 ms"},
    "max_connected_ues": {"value": "300", "standard": "200-500"},
    "prach_root_sequence": {"value": "22", "standard": "0-837"},
    "scheduler_algorithm": {"value": "proportional_fair", "standard": "proportional_fair / round_robin"},
    "drx_cycle": {"value": "40 ms", "standard": "20-160 ms"},
    "cio_offset": {"value": "0 dB", "standard": "-6 to 6 dB"},
    "qrxlevmin": {"value": "-124 dBm", "standard": "-140 to -44 dBm"},
    "ul_interference_threshold": {"value": "-100 dBm", "standard": "-110 to -90 dBm"},
}

CONFIG_CHANGES = [
    {"cell_id": "SITE-METRO-002-S2", "param": "ul_interference_threshold", "old": "-100 dBm", "new": "-95 dBm",
     "changed_by": "auto_son", "time": "2026-04-07 09:15:00", "reason": "SON auto-adjustment due to interference"},
    {"cell_id": "SITE-SUBR-001-S1", "param": "dl_tx_power", "old": "46 dBm", "new": "43 dBm",
     "changed_by": "engineer_mk", "time": "2026-04-06 14:30:00", "reason": "Power reduction test for interference mitigation"},
    {"cell_id": "SITE-INDOOR-002-S1", "param": "max_connected_ues", "old": "300", "new": "500",
     "changed_by": "noc_team", "time": "2026-04-07 08:00:00", "reason": "Capacity increase for stadium event"},
    {"cell_id": "SITE-RURAL-001-S3", "param": "a3_offset", "old": "3 dB", "new": "6 dB",
     "changed_by": "engineer_jd", "time": "2026-04-05 11:00:00", "reason": "Reduce unnecessary handovers from weak cell"},
    {"cell_id": "SITE-METRO-003-S1", "param": "antenna_tilt", "old": "4 deg", "new": "6 deg",
     "changed_by": "engineer_mk", "time": "2026-04-06 16:45:00", "reason": "Coverage optimization — reduce overshoot"},
]


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
def root():
    return {
        "name": "Consilium Telecom Data Service",
        "version": "1.0.0",
        "cells": len(CELLS),
        "sites": len(SITES),
        "active_alarms": sum(1 for a in ALARM_DB if a["status"] == "ACTIVE"),
        "endpoints": ["/kpi", "/alarms", "/config", "/topology"],
    }


@app.get("/topology/sites")
def get_sites():
    """List all sites."""
    return {"sites": SITES, "count": len(SITES)}


@app.get("/topology/cells")
def get_cells(site_id: Optional[str] = None, region: Optional[str] = None):
    """List cells, optionally filtered by site or region."""
    result = CELLS
    if site_id:
        result = [c for c in result if c["site_id"] == site_id]
    if region:
        result = [c for c in result if c["region"].lower() == region.lower()]
    return {"cells": result, "count": len(result)}


def _normalize_ids(cell_id: Optional[str], site_id: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Normalize cell/site ID inputs:
    - Handle comma-separated cell IDs by extracting site_id instead
    - Handle cell_id that's actually a site_id (no -S suffix)
    - Strip whitespace
    """
    if cell_id:
        cell_id = cell_id.strip()
        if not cell_id:  # Was only whitespace
            cell_id = None
            return cell_id, site_id
        # Comma-separated → extract site_id from first cell
        if "," in cell_id:
            first = cell_id.split(",")[0].strip()
            # Extract site_id by removing -S1/-S2/-S3 suffix
            if "-S" in first:
                site_id = first.rsplit("-S", 1)[0]
                cell_id = None
            else:
                site_id = first
                cell_id = None
        # cell_id without sector suffix is actually a site_id
        elif cell_id not in CELL_LOOKUP and not cell_id.endswith(("-S1", "-S2", "-S3")):
            # Check if it's a valid site_id
            if any(s["site_id"] == cell_id for s in SITES):
                site_id = cell_id
                cell_id = None
    return cell_id, site_id


def _resolve_cells(cell_id: Optional[str], site_id: Optional[str], region: Optional[str]) -> tuple[list[str], Optional[str]]:
    """
    Resolve cell/site/region to a list of cell IDs.
    Returns (cell_list, error_message). error_message is None if valid.
    """
    cell_id, site_id = _normalize_ids(cell_id, site_id)

    if cell_id:
        if cell_id in CELL_LOOKUP:
            return [cell_id], None
        else:
            available = [s["site_id"] for s in SITES[:5]]
            return [], f"Unknown cell_id: '{cell_id}'. Available sites: {', '.join(available)}. Use site_id for all sectors."
    elif site_id:
        cells = [c["cell_id"] for c in CELLS if c["site_id"] == site_id]
        if cells:
            return cells, None
        else:
            available = [s["site_id"] for s in SITES[:5]]
            return [], f"Unknown site_id: '{site_id}'. Available sites: {', '.join(available)}"
    elif region:
        cells = [c["cell_id"] for c in CELLS if c["region"].lower() == region.lower()]
        if cells:
            return cells, None
        else:
            available = list({s["region"] for s in SITES})
            return [], f"Unknown region: '{region}'. Available regions: {', '.join(available)}"
    return CELL_IDS, None


@app.get("/kpi")
def get_kpi(
    cell_id: Optional[str] = None,
    site_id: Optional[str] = None,
    region: Optional[str] = None,
    hour: int = Query(default=None, description="Hour of day (0-23). Defaults to current hour."),
):
    """
    Get cell-level KPIs. TM Forum TMF628 aligned.
    Returns metrics for specified cell(s) at the given hour.
    """
    if hour is None:
        hour = datetime.now().hour

    target_cells, error = _resolve_cells(cell_id, site_id, region)

    if error:
        return {
            "tool": "kpi_lookup",
            "query": {"cell_id": cell_id, "site_id": site_id, "region": region, "hour": hour},
            "error": error,
            "results": [],
            "summary": f"ERROR: {error}",
        }

    results = [generate_kpi(cid, hour) for cid in target_cells]
    degraded = sum(1 for r in results if r["status"] in ("DEGRADED", "CRITICAL"))

    return {
        "tool": "kpi_lookup",
        "query": {"cell_id": cell_id, "site_id": site_id, "region": region, "hour": hour},
        "results": results,
        "summary": f"Retrieved KPIs for {len(results)} cells at hour {hour}. {degraded} degraded/critical.",
    }


@app.get("/kpi/trend")
def get_kpi_trend(
    cell_id: str = Query(..., description="Cell ID"),
    hours: int = Query(default=24, description="Number of hours to look back"),
):
    """Get KPI trend for a cell over multiple hours."""
    if cell_id not in CELL_LOOKUP:
        return {"error": f"Cell {cell_id} not found"}

    current_hour = datetime.now().hour
    trend = []
    for h_offset in range(hours):
        h = (current_hour - hours + h_offset + 1) % 24
        kpi = generate_kpi(cell_id, h, day=h_offset // 24)
        trend.append(kpi)

    return {
        "tool": "kpi_trend",
        "cell_id": cell_id,
        "hours": hours,
        "trend": trend,
    }


@app.get("/alarms")
def get_alarms(
    cell_id: Optional[str] = None,
    site_id: Optional[str] = None,
    region: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = Query(default=None, description="ACTIVE or CLEARED"),
):
    """
    Query alarms. TM Forum TMF642 aligned.
    """
    # Normalize IDs (handle comma-separated, site_id extraction)
    cell_id, site_id = _normalize_ids(cell_id, site_id)

    # Validate IDs
    if cell_id or site_id or region:
        _, error = _resolve_cells(cell_id, site_id, region)
        if error:
            return {
                "tool": "alarm_query",
                "query": {"cell_id": cell_id, "site_id": site_id, "severity": severity, "status": status},
                "error": error,
                "alarms": [],
                "summary": f"ERROR: {error}",
            }

    result = ALARM_DB

    if cell_id:
        result = [a for a in result if a["affected_element"] == cell_id]
    if site_id:
        result = [a for a in result if a["site_id"] == site_id]
    if region:
        site_ids = {s["site_id"] for s in SITES if s["region"].lower() == region.lower()}
        result = [a for a in result if a["site_id"] in site_ids]
    if severity:
        result = [a for a in result if a["severity"].lower() == severity.lower()]
    if status:
        result = [a for a in result if a["status"].lower() == status.lower()]

    return {
        "tool": "alarm_query",
        "query": {"cell_id": cell_id, "site_id": site_id, "severity": severity, "status": status},
        "alarms": result,
        "summary": f"Found {len(result)} alarms. {sum(1 for a in result if a['status'] == 'ACTIVE')} active.",
    }


@app.get("/config")
def get_config(
    cell_id: Optional[str] = None,
    site_id: Optional[str] = None,
):
    """
    Get configuration and recent changes. TM Forum TMF639 aligned.
    """
    # Normalize IDs
    cell_id, site_id = _normalize_ids(cell_id, site_id)

    # Validate IDs
    if cell_id or site_id:
        _, error = _resolve_cells(cell_id, site_id, None)
        if error:
            return {
                "tool": "config_audit",
                "query": {"cell_id": cell_id, "site_id": site_id},
                "error": error,
                "baseline": None,
                "changes": [],
                "summary": f"ERROR: {error}",
            }

    # Recent changes
    changes = CONFIG_CHANGES
    if cell_id:
        changes = [c for c in changes if c["cell_id"] == cell_id]
    if site_id:
        changes = [c for c in changes if c["cell_id"].startswith(site_id)]

    # Baseline for requested cell or all cells at site
    baseline = None
    if cell_id:
        baseline = {
            "cell_id": cell_id,
            "parameters": CONFIG_BASELINES,
            "overrides": {c["param"]: c["new"] for c in CONFIG_CHANGES if c["cell_id"] == cell_id},
        }
    elif site_id:
        site_cells = [c["cell_id"] for c in CELLS if c["site_id"] == site_id]
        baseline = {
            "site_id": site_id,
            "cells": site_cells,
            "parameters": CONFIG_BASELINES,
            "overrides": {c["cell_id"] + ":" + c["param"]: c["new"] for c in CONFIG_CHANGES if c["cell_id"].startswith(site_id)},
        }

    return {
        "tool": "config_audit",
        "query": {"cell_id": cell_id, "site_id": site_id},
        "baseline": baseline,
        "changes": changes,
        "summary": f"Found {len(changes)} recent configuration changes.",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "cells": len(CELLS),
        "active_alarms": sum(1 for a in ALARM_DB if a["status"] == "ACTIVE"),
        "anomalous_cells": len(ACTIVE_ANOMALIES),
    }
