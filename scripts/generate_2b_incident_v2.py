#!/usr/bin/env python3
"""Phase 2B: Generate Incident recovery rows — raw HTTP, smaller batches, resume-safe."""

import json
import os
import time
import random
import urllib.request
import urllib.error
import ssl

random.seed(42)

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"
OUTPUT_FILE = "data/v4_corrective/2b_incident_recovery.jsonl"
SYSTEM_PROMPT = "You are Consilium, a telecom network intelligence assistant. Analyze network data, diagnose issues, and provide actionable recommendations."

COVERAGE_GRID = [
    # INC-RAN-01: Generic triage drift (~240 rows)
    ("RAN handover inter-frequency failures with A3/A5 event analysis", 30, "INC-RAN-01"),
    ("RAN handover intra-frequency failures with neighbor relation issues", 30, "INC-RAN-01"),
    ("RAN inter-RAT handover failures between LTE and 5G NR", 30, "INC-RAN-01"),
    ("RAN too-early and too-late handover with timer/threshold tuning", 25, "INC-RAN-01"),
    ("RAN ping-pong handover between cells with SON optimization", 25, "INC-RAN-01"),
    ("RAN load balancing failures with MLB and traffic steering", 30, "INC-RAN-01"),
    ("RAN SON/ANR issues with automatic neighbor relation management", 25, "INC-RAN-01"),
    ("RAN handover to wrong cell with PCI confusion or mod-3 clash", 25, "INC-RAN-01"),
    ("RAN conditional handover and DAPS handover failures in 5G NR", 20, "INC-RAN-01"),
    # INC-RAN-10: Scoring completeness (~175 rows)
    ("RAN backhaul congestion causing throughput degradation", 30, "INC-RAN-10"),
    ("RAN fronthaul CPRI/eCPRI capacity issues affecting cell performance", 25, "INC-RAN-10"),
    ("RAN midhaul latency impacting scheduling and HARQ timing", 25, "INC-RAN-10"),
    ("RAN backhaul packet loss causing retransmissions and KPI drops", 25, "INC-RAN-10"),
    ("RAN transport sync issues affecting timing advance and GPS", 25, "INC-RAN-10"),
    ("RAN microwave backhaul degradation from weather or alignment", 25, "INC-RAN-10"),
    ("RAN fronthaul fiber cut or degradation impacting BBU-RRU link", 20, "INC-RAN-10"),
    # INC-IMS-01: Scoring completeness (~230 rows)
    ("IMS VoLTE call failures with SIP 503 Service Unavailable", 30, "INC-IMS-01"),
    ("IMS registration failures with SIP 403 Forbidden responses", 25, "INC-IMS-01"),
    ("IMS call setup failures with SIP 408 Request Timeout", 25, "INC-IMS-01"),
    ("IMS P-CSCF or S-CSCF overload causing call failures", 30, "INC-IMS-01"),
    ("IMS VoLTE call drops mid-session with RTP/RTCP issues", 25, "INC-IMS-01"),
    ("IMS VoNR call failures and EPS fallback issues", 25, "INC-IMS-01"),
    ("IMS emergency call routing failures with E-CSCF", 20, "INC-IMS-01"),
    ("IMS codec negotiation failures and SDP offer/answer issues", 15, "INC-IMS-01"),
    ("IMS re-registration storms and timer expiry issues", 15, "INC-IMS-01"),
    ("IMS Rx interface failures between PCRF and P-CSCF for QoS", 20, "INC-IMS-01"),
    # INC-TRANS-02: Wrong layer + generic triage (~235 rows)
    ("Transport BGP flapping causing route instability and service impact", 30, "INC-TRANS-02"),
    ("Transport BGP route leak or hijack affecting traffic paths", 25, "INC-TRANS-02"),
    ("Transport MPLS LSP failure and label switching path recovery", 30, "INC-TRANS-02"),
    ("Transport MPLS TE tunnel rerouting causing latency spikes", 25, "INC-TRANS-02"),
    ("Transport DWDM wavelength failure and optical power degradation", 25, "INC-TRANS-02"),
    ("Transport fiber cut impact on multiple services with protection switching", 25, "INC-TRANS-02"),
    ("Transport IP routing convergence delays after topology change", 25, "INC-TRANS-02"),
    ("Transport QoS marking mismatch between network domains", 20, "INC-TRANS-02"),
    ("Transport timing and synchronization failures PTP/SyncE", 15, "INC-TRANS-02"),
    ("Transport peering point congestion between operator and IX", 15, "INC-TRANS-02"),
]

GENERATION_PROMPT = """Generate exactly {count} telecom incident troubleshooting Q&A pairs for training data.

**Category:** {subcategory}
**Regression being fixed:** {regression_id}

**CRITICAL STYLE RULES — every answer MUST follow these:**
1. Start with a decisive diagnosis — name the specific cause in the first sentence
2. NEVER use probability percentages ("30% likely", "probably X%")
3. NEVER use "possible causes are…" or "possible causes include…"
4. NEVER list causes with probability rankings
5. Name specific network functions, protocols, and interfaces explicitly
6. Give a specific first check / first action — not a generic list
7. Use exact technical terms: specific NF names (AMF, SMF, UPF, gNB, eNB), protocol names (S1-AP, NGAP, X2, Xn, GTP, PFCP), interface names (N2, N3, N4, S1-U, S1-MME)
8. For IMS: always cite specific SIP response codes (503, 403, 408, etc.)
9. For transport: always name the specific protocol/technology (BGP, MPLS, DWDM, OSPF, IS-IS)
10. For RAN: always name the specific procedure (handover, load balancing, SON, ANR) and measurement events (A1-A6, B1-B2)

**FORMAT:** Return a JSON array of objects, each with "user" and "assistant" keys.
- "user": a realistic NOC engineer question with specific KPIs, cell IDs, timestamps, and measurable symptoms
- "assistant": a 150-300 word decisive diagnosis with specific first action

**VARIATION RULES:**
- Vary cell IDs, site names, timestamps, KPI values across rows
- Mix severity levels (critical outage, degradation, intermittent)
- Include different network generations (4G, 5G NSA, 5G SA) where applicable
- Each row must be substantially different — no template repetition

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
    # Find the JSON array
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


def generate_batch(subcategory, count, regression_id):
    """Generate a batch of incident rows."""
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

    # Resume: count existing rows per subcategory index
    existing_rows = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing_rows = sum(1 for _ in f)

    total_target = sum(c for _, c, _ in COVERAGE_GRID)
    print(f"Coverage grid: {len(COVERAGE_GRID)} subcategories, {total_target} target rows")
    print(f"Existing rows: {existing_rows}")

    # If resuming, figure out where we left off
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

        # Generate in sub-batches of 5 for reliability
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

        # Write after each subcategory
        with open(OUTPUT_FILE, "a") as f:
            for row in batch_rows:
                f.write(json.dumps(row) + "\n")

    final_count = 0
    with open(OUTPUT_FILE) as f:
        final_count = sum(1 for _ in f)

    print(f"\n=== PHASE 2B COMPLETE ===")
    print(f"Total rows: {final_count}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
