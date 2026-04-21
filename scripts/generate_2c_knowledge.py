#!/usr/bin/env python3
"""Phase 2C: Generate Knowledge retention rows targeting 4 specific regressions."""

import json
import os
import time
import urllib.request
import ssl

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"
OUTPUT_FILE = "data/v4_corrective/2c_knowledge_retention.jsonl"
SYSTEM_PROMPT = "You are Consilium, a telecom network intelligence assistant. Analyze network data, diagnose issues, and provide actionable recommendations."

COVERAGE_GRID = [
    # PROTO-03: Distinction collapse — restore EPC vs 5GC, control plane terms in NSA/SA (~220 rows)
    ("NSA architecture with EPC core network elements MME SGW PGW and their roles", 30, "PROTO-03"),
    ("SA architecture with 5GC core network functions AMF SMF UPF AUSF and service-based interfaces", 30, "PROTO-03"),
    ("NSA vs SA comparison with explicit EPC and 5GC control plane differences", 30, "PROTO-03"),
    ("EN-DC dual connectivity with MCG SCG split bearer and EPC-5GC interworking", 25, "PROTO-03"),
    ("5GC service-based architecture SBI with NRF NSSF NEF PCF and HTTP/2 interfaces", 25, "PROTO-03"),
    ("EPC signaling procedures attach detach TAU with NAS EMM ESM state machines", 25, "PROTO-03"),
    ("NSA option 3/3a/3x configurations with S1-U and X2 data path differences", 25, "PROTO-03"),
    ("Control plane protocol stack differences NAS RRC NGAP S1-AP between 4G and 5G", 30, "PROTO-03"),

    # PROTO-11: Wrong terminology — restore PSS/SSS signal names for SSB (~220 rows)
    ("SSB structure with PSS and SSS synchronization signals and PBCH in time-frequency grid", 30, "PROTO-11"),
    ("PSS primary synchronization signal for cell ID group detection with 3 sequences", 30, "PROTO-11"),
    ("SSS secondary synchronization signal for physical cell ID determination with 336 sequences", 30, "PROTO-11"),
    ("SSB burst set and beam sweeping with SSB index and L1-RSRP measurement", 25, "PROTO-11"),
    ("Initial cell search procedure using PSS SSS PBCH-DMRS and MIB decoding", 25, "PROTO-11"),
    ("SS-RSRP SS-RSRQ SS-SINR measurements based on SSB for cell selection reselection", 25, "PROTO-11"),
    ("SSB periodicity configuration and half-frame patterns for different frequency ranges FR1 FR2", 25, "PROTO-11"),
    ("CSI-RS vs SSB for beam management and L1-RSRP reporting in 5G NR", 30, "PROTO-11"),

    # PROTO-12: Coverage loss — restore component carrier, SCell, PCell for CA (~220 rows)
    ("Carrier aggregation with PCell SCell and component carrier configuration", 30, "PROTO-12"),
    ("SCell activation deactivation MAC CE procedures and timers", 30, "PROTO-12"),
    ("CA band combinations with contiguous and non-contiguous component carriers", 25, "PROTO-12"),
    ("PCell role in RRC connection and PUCCH for uplink control with CA", 25, "PROTO-12"),
    ("PSCell in dual connectivity SCG configuration with NR-DC and EN-DC", 25, "PROTO-12"),
    ("Cross-carrier scheduling with CIF in PDCCH for multi-CC operation", 25, "PROTO-12"),
    ("CA vs DC comparison for throughput aggregation and architecture differences", 25, "PROTO-12"),
    ("UE capability signaling for CA support with band combo and MIMO layers per CC", 25, "PROTO-12"),
    ("BWP bandwidth part configuration within component carriers for NR CA", 10, "PROTO-12"),

    # PROTO-16: Scoring completeness — restore "registration" in NRF lifecycle (~220 rows)
    ("NRF network repository function with NF registration and discovery procedures", 30, "PROTO-16"),
    ("NF registration lifecycle with NRF including heartbeat and deregistration", 30, "PROTO-16"),
    ("NF discovery and selection via NRF with service profiles and query parameters", 30, "PROTO-16"),
    ("NRF service registration with NF profile NF type and supported services", 25, "PROTO-16"),
    ("NF status notification and subscription via NRF for service availability monitoring", 25, "PROTO-16"),
    ("OAuth2 token-based authorization in 5GC with NRF as authorization server", 25, "PROTO-16"),
    ("NRF in roaming architecture with vNRF hNRF and inter-PLMN discovery", 25, "PROTO-16"),
    ("SCP service communication proxy interaction with NRF for indirect communication", 30, "PROTO-16"),
]

GENERATION_PROMPT = """Generate exactly {count} telecom knowledge/protocol Q&A pairs for training data.

**Category:** {subcategory}
**Regression being fixed:** {regression_id}

**CRITICAL STYLE RULES — every answer MUST follow these:**
1. Use EXACT technical terminology — never paraphrase or simplify standard terms
2. For NSA/SA: always name specific core network elements (EPC: MME, SGW, PGW; 5GC: AMF, SMF, UPF, AUSF, UDM)
3. For SSB: always name PSS (Primary Synchronization Signal) and SSS (Secondary Synchronization Signal) explicitly
4. For CA: always use PCell, SCell, PSCell, component carrier — never just "carrier" or "cell"
5. For NRF: always include "registration" in lifecycle descriptions, name the NF profile fields
6. NO casual analogies ("think of it like...")
7. NO broad conceptual-only explanations — every answer must include specific protocol names, message names, or parameter names
8. Include 3GPP specification references where relevant (TS 38.xxx, TS 23.xxx)
9. Distinguish between protocol layers clearly — RRC, NAS, NGAP, S1-AP are different layers
10. Name specific procedures: registration, PDU session establishment, handover preparation, bearer setup

**FORMAT:** Return a JSON array of objects, each with "user" and "assistant" keys.
- "user": a technical question that a telecom engineer would ask about protocols, architecture, or standards
- "assistant": a 150-300 word precise technical explanation with exact terminology

**VARIATION RULES:**
- Vary question complexity (basic concept, comparison, troubleshooting implication, design rationale)
- Mix question styles: "what is", "how does", "what's the difference", "why does", "explain the procedure"
- Include practical operator perspectives, not just textbook definitions
- Each row must cover a different aspect or angle — no repetition

Return ONLY the JSON array, no other text."""


def call_api(prompt, retries=3):
    """Call Claude API via raw HTTP."""
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    }

    ctx = ssl.create_default_context()
    req = urllib.request.Request(API_URL, data=payload, headers=headers, method="POST")

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["content"][0]["text"]
        except Exception as e:
            print(f"    Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    return None


def parse_response(text):
    """Extract JSON array from response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


def generate_batch(subcategory, count, regression_id):
    """Generate a batch of knowledge rows."""
    prompt = GENERATION_PROMPT.format(
        count=count, subcategory=subcategory, regression_id=regression_id
    )
    text = call_api(prompt)
    if not text:
        return []

    try:
        pairs = parse_response(text)
        rows = []
        for pair in pairs:
            row = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": pair["user"]},
                    {"role": "assistant", "content": pair["assistant"]},
                ]
            }
            rows.append(row)
        return rows
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"    Parse error: {e}")
        return []


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    existing_rows = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing_rows = sum(1 for _ in f)

    total_target = sum(c for _, c, _ in COVERAGE_GRID)
    print(f"Coverage grid: {len(COVERAGE_GRID)} subcategories, {total_target} target rows")
    print(f"Existing rows: {existing_rows}")

    skip_rows = existing_rows
    completed_total = existing_rows

    for i, (subcategory, count, regression_id) in enumerate(COVERAGE_GRID):
        if skip_rows >= count:
            skip_rows -= count
            print(f"[{i+1}/{len(COVERAGE_GRID)}] SKIP (already done): {subcategory}")
            continue
        elif skip_rows > 0:
            count -= skip_rows
            skip_rows = 0
            print(f"[{i+1}/{len(COVERAGE_GRID)}] PARTIAL resume: {subcategory} ({count} remaining)")
        else:
            print(f"[{i+1}/{len(COVERAGE_GRID)}] {subcategory} ({count} rows, {regression_id})")

        batch_rows = []
        remaining = count
        while remaining > 0:
            batch_size = min(5, remaining)
            rows = generate_batch(subcategory, batch_size, regression_id)
            if not rows:
                print(f"    Empty batch, retrying...")
                time.sleep(3)
                continue
            batch_rows.extend(rows)
            remaining -= len(rows)
            completed_total += len(rows)
            print(f"    +{len(rows)} rows (subcat: {len(batch_rows)}/{count}, total: {completed_total}/{total_target})")
            time.sleep(0.3)

        with open(OUTPUT_FILE, "a") as f:
            for row in batch_rows:
                f.write(json.dumps(row) + "\n")

    final_count = 0
    with open(OUTPUT_FILE) as f:
        final_count = sum(1 for _ in f)

    print(f"\n=== PHASE 2C COMPLETE ===")
    print(f"Total rows: {final_count}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
