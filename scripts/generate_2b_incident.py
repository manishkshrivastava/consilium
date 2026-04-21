#!/usr/bin/env python3
"""Phase 2B: Generate Incident recovery rows targeting 4 specific regressions."""

import json
import os
import time
import random
import anthropic

random.seed(42)

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OUTPUT_FILE = "data/v4_corrective/2b_incident_recovery.jsonl"
SYSTEM_PROMPT = "You are Consilium, a telecom network intelligence assistant. Analyze network data, diagnose issues, and provide actionable recommendations."

# Coverage grid: each entry = (subcategory, count_to_generate, regression_source)
COVERAGE_GRID = [
    # === INC-RAN-01: Generic triage drift — restore handover, load balancing, SON specifics ===
    # Target: ~240 rows
    ("RAN handover inter-frequency failures with A3/A5 event analysis", 30, "INC-RAN-01"),
    ("RAN handover intra-frequency failures with neighbor relation issues", 30, "INC-RAN-01"),
    ("RAN inter-RAT handover failures between LTE and 5G NR", 30, "INC-RAN-01"),
    ("RAN too-early and too-late handover with timer/threshold tuning", 25, "INC-RAN-01"),
    ("RAN ping-pong handover between cells with SON optimization", 25, "INC-RAN-01"),
    ("RAN load balancing failures with MLB and traffic steering", 30, "INC-RAN-01"),
    ("RAN SON/ANR issues with automatic neighbor relation management", 25, "INC-RAN-01"),
    ("RAN handover to wrong cell with PCI confusion or mod-3 clash", 25, "INC-RAN-01"),
    ("RAN conditional handover and DAPS handover failures in 5G NR", 20, "INC-RAN-01"),

    # === INC-RAN-10: Scoring completeness — restore "backhaul" term ===
    # Target: ~175 rows
    ("RAN backhaul congestion causing throughput degradation", 30, "INC-RAN-10"),
    ("RAN fronthaul CPRI/eCPRI capacity issues affecting cell performance", 25, "INC-RAN-10"),
    ("RAN midhaul latency impacting scheduling and HARQ timing", 25, "INC-RAN-10"),
    ("RAN backhaul packet loss causing retransmissions and KPI drops", 25, "INC-RAN-10"),
    ("RAN transport sync issues affecting timing advance and GPS", 25, "INC-RAN-10"),
    ("RAN microwave backhaul degradation from weather or alignment", 25, "INC-RAN-10"),
    ("RAN fronthaul fiber cut or degradation impacting BBU-RRU link", 20, "INC-RAN-10"),

    # === INC-IMS-01: Scoring completeness — restore SIP 503, IMS domain specifics ===
    # Target: ~230 rows
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

    # === INC-TRANS-02: Wrong layer + generic triage — restore BGP/MPLS/DWDM, peer specifics ===
    # Target: ~235 rows
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


def generate_batch(client, subcategory, count, regression_id):
    """Generate a batch of incident rows."""
    prompt = GENERATION_PROMPT.format(
        count=count,
        subcategory=subcategory,
        regression_id=regression_id,
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Extract JSON array
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        pairs = json.loads(text)

        # Convert to chat-completion format
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

    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def main():
    client = anthropic.Anthropic(api_key=API_KEY)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    total_target = sum(count for _, count, _ in COVERAGE_GRID)
    print(f"Coverage grid: {len(COVERAGE_GRID)} subcategories, {total_target} total rows")
    print(f"Output: {OUTPUT_FILE}")
    print()

    all_rows = []

    # Resume support: check existing output
    existing = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing = sum(1 for _ in f)
        print(f"Found {existing} existing rows, will append")

    completed_count = 0

    for i, (subcategory, count, regression_id) in enumerate(COVERAGE_GRID):
        print(f"[{i+1}/{len(COVERAGE_GRID)}] {subcategory} ({count} rows, {regression_id})")

        # Generate in sub-batches of 10 for quality
        batch_rows = []
        remaining = count
        while remaining > 0:
            batch_size = min(10, remaining)
            rows = generate_batch(client, subcategory, batch_size, regression_id)
            batch_rows.extend(rows)
            remaining -= len(rows)
            if not rows:
                print(f"  Failed batch, retrying in 5s...")
                time.sleep(5)
                continue
            print(f"  Got {len(rows)} rows (subtotal: {len(batch_rows)}/{count})")
            time.sleep(0.5)  # Rate limit courtesy

        all_rows.extend(batch_rows)
        completed_count += len(batch_rows)
        print(f"  Subtotal so far: {completed_count}")

        # Write incrementally after each subcategory
        with open(OUTPUT_FILE, 'a') as f:
            for row in batch_rows:
                f.write(json.dumps(row) + '\n')

    print(f"\n=== PHASE 2B COMPLETE ===")
    print(f"Total rows generated: {completed_count}")
    print(f"Output: {OUTPUT_FILE}")

    # Category breakdown
    by_regression = {}
    for _, count, reg_id in COVERAGE_GRID:
        by_regression[reg_id] = by_regression.get(reg_id, 0) + count
    print("\nTarget breakdown by regression:")
    for reg_id, count in sorted(by_regression.items()):
        print(f"  {reg_id}: {count}")


if __name__ == "__main__":
    main()
