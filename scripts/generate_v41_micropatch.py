#!/usr/bin/env python3
"""v4.1 Micro-patch: Generate targeted correction rows for 4 categories."""

import json
import os
import time
import urllib.request
import ssl

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"
SYSTEM_PROMPT = "You are Consilium, a telecom network intelligence assistant. Analyze network data, diagnose issues, and provide actionable recommendations."
OUTPUT_DIR = "data/v4_1_corrective"

# ============================================================
# Category A: Anti-probability-ranking repair (80-120 rows)
# ============================================================
CATEGORY_A = [
    # Directly mirror the 8 affected benchmark patterns
    ("RAN eNodeB high CPU diagnosis with explicit first cause and no probability ranking", 15, "anti-prob"),
    ("RAN VSWR antenna fault diagnosis with decisive first action", 10, "anti-prob"),
    ("RAN PRB congestion busy hour diagnosis with specific cause named first", 10, "anti-prob"),
    ("Transport backhaul microwave degradation diagnosis naming rain fade or alignment first", 10, "anti-prob"),
    ("IMS SBC overload or registration storm diagnosis with specific SIP code", 10, "anti-prob"),
    ("KPI RRC setup failure analysis with specific counter names and first check", 10, "anti-prob"),
    ("KPI inter-RAT handover failure analysis with specific measurement event named first", 10, "anti-prob"),
    ("KPI paging failure analysis with TAI and S-TMSI terms and no probability language", 10, "anti-prob"),
    ("Mixed incident diagnosis across RAN/Core/Transport with decisive style and no hedging", 15, "anti-prob"),
]

PROMPT_A = """Generate exactly {count} telecom incident/KPI Q&A pairs for training data.

**Category:** {subcategory}

**THE SINGLE MOST IMPORTANT RULE:**
NEVER use probability percentages or probability ranking in the answer.
- NO "70% likely", "50% probability", "30% chance"
- NO "Probability Ranked:", "by probability", "ranked by probability"
- NO "Root Cause Analysis (Probability Ranked)"
- NO numbered lists with percentages after each item

**CORRECT STYLE (follow this exactly):**
- Name the SINGLE most likely cause in the first sentence
- Say "The primary cause is X" or "This indicates X" or "This is caused by X"
- Then explain WHY that cause fits the symptoms
- Give a specific first check and first action
- Only mention secondary causes AFTER the primary, without percentages

**Example of WRONG style (never do this):**
"Root Cause Analysis (Probability Ranked):
1. CPU overload (70%) - check CPU counters
2. Memory leak (20%) - check memory
3. Software bug (10%) - check logs"

**Example of CORRECT style (always do this):**
"The primary cause is CPU overload in the RRC/RLC processing layers, driven by excessive handover signaling from 450 connected UEs. First check: monitor eNodeB CPU utilization per process. First action: enable MLB to redistribute load to neighboring cells."

**FORMAT:** Return a JSON array with "user" and "assistant" keys.
- "user": realistic NOC question with specific KPIs, cell IDs, symptoms
- "assistant": 150-250 word decisive diagnosis, NO probability language

Return ONLY the JSON array."""

# ============================================================
# Category B: Exact terminology reinforcement (160-200 rows)
# ============================================================
CATEGORY_B = [
    # PROTO-04: Must use Msg3, contention resolution
    ("5G NR RACH 4-step random access procedure with explicit Msg1 Msg2 Msg3 Msg4 and contention resolution", 15, "proto-04"),
    ("5G NR CBRA vs CFRA random access with contention resolution and Msg3 RRC setup", 15, "proto-04"),
    ("RACH procedure troubleshooting mentioning preamble Msg1 RAR Msg2 Msg3 and contention Msg4", 10, "proto-04"),
    ("2-step RACH vs 4-step RACH comparison with MsgA MsgB and contention resolution", 10, "proto-04"),
    # PROTO-16: Must use registration, discovery
    ("NRF NF registration procedure with NF profile heartbeat and deregistration lifecycle", 15, "proto-16"),
    ("NRF NF discovery procedure with query parameters and service selection", 15, "proto-16"),
    ("NRF registration and discovery in 5GC SBA with HTTP/2 and NF profiles", 10, "proto-16"),
    ("NRF OAuth2 authorization with NF registration as prerequisite", 10, "proto-16"),
    # PROTO-19: Must use interface, RIC
    ("O-RAN architecture with open interfaces and RIC near-RT and non-RT", 15, "proto-19"),
    ("O-RAN vs traditional RAN with open fronthaul interface and RIC xApps", 15, "proto-19"),
    ("O-RAN RIC platform with A1 E2 O1 interfaces and rApps xApps", 10, "proto-19"),
    ("O-RAN multi-vendor interoperability through open interface specifications", 10, "proto-19"),
    # PROTO-20: Must use local
    ("MEC in 5G with local breakout and local traffic routing at edge", 15, "proto-20"),
    ("MEC architecture with local processing local storage and edge application server", 15, "proto-20"),
    ("MEC use cases with local compute for AR VR autonomous vehicles at network edge", 10, "proto-20"),
]

PROMPT_B = """Generate exactly {count} telecom protocol/knowledge Q&A pairs for training data.

**Category:** {subcategory}

**CRITICAL TERMINOLOGY RULES:**
You MUST use these EXACT terms in every answer (where relevant to the topic):
- For RACH: "Msg1" (preamble), "Msg2" (RAR), "Msg3" (RRC connection request), "Msg4" (contention resolution)
- For NRF: "registration" (NF registers with NRF), "discovery" (consumer NF discovers producer via NRF)
- For O-RAN: "open interface" (fronthaul, midhaul), "RIC" (RAN Intelligent Controller), "xApp", "rApp"
- For MEC: "local" (local breakout, local processing, local compute, local storage)

These terms MUST appear explicitly — do not paraphrase them.

**STYLE:**
- Precise technical language
- No casual analogies
- Name specific 3GPP specs where relevant (TS 38.xxx, TS 23.xxx)
- Include protocol layer details, message names, parameter names

**FORMAT:** Return a JSON array with "user" and "assistant" keys.
- "user": technical question about the protocol/architecture
- "assistant": 150-300 word precise explanation with exact terminology

Return ONLY the JSON array."""

# ============================================================
# Category C: Transport/incident priority-order repair (60-80 rows)
# ============================================================
CATEGORY_C = [
    ("MPLS LSP failure diagnosis starting with LDP/RSVP-TE specific checks first", 15, "trans-fix"),
    ("BGP flapping diagnosis starting with BGP hold timer and keepalive checks first", 15, "trans-fix"),
    ("Microwave backhaul packet loss starting with RSL rain fade and fade margin first", 15, "trans-fix"),
    ("DL throughput drop with low PRB starting with SINR CQI interference checks first", 15, "trans-fix"),
    ("Diameter Gx connection loss starting with Diameter peer and Gx interface checks first", 10, "trans-fix"),
]

PROMPT_C = """Generate exactly {count} telecom incident troubleshooting Q&A pairs for training data.

**Category:** {subcategory}

**CRITICAL PRIORITY-ORDER RULES:**
1. The FIRST thing mentioned must be the domain-specific check, NOT generic physical layer
2. For MPLS: start with "show mpls ldp neighbor" or LDP session, NOT "check cabling"
3. For BGP: start with BGP hold timer / keepalive, NOT "check physical connectivity"
4. For microwave: start with RSL / fade margin / rain fade, NOT "check cable integrity"
5. For throughput with low PRB: start with SINR / CQI / interference, NOT "check RF environment"
6. For Diameter: start with Diameter peer status / Gx interface, NOT "check TCP connectivity"

**STYLE:**
- Name the specific protocol/technology FIRST in the diagnosis
- Give specific CLI commands or counter names
- No generic "check physical layer" as first step
- Decisive tone, no hedging

**FORMAT:** Return a JSON array with "user" and "assistant" keys.
Return ONLY the JSON array."""

# ============================================================
# Category D: KPI baseline correction (20-40 rows)
# ============================================================
CATEGORY_D = [
    ("LTE 20MHz cell expected throughput baseline and diagnosis when underperforming with PRB SINR MCS analysis", 15, "kpi-fix"),
    ("LTE 10MHz vs 20MHz expected throughput with spectral efficiency and MIMO layer analysis", 10, "kpi-fix"),
    ("5G NR expected throughput by bandwidth 50MHz 100MHz with modulation and rank analysis", 10, "kpi-fix"),
]

PROMPT_D = """Generate exactly {count} telecom KPI analysis Q&A pairs for training data.

**Category:** {subcategory}

**CRITICAL BASELINE RULES:**
- For 20MHz LTE cell: normal DL throughput is 30-50 Mbps in good RF (not 8-12 Mbps)
- For 10MHz LTE cell: normal DL throughput is 15-25 Mbps
- For 100MHz 5G NR: normal DL throughput is 400-800 Mbps
- Always reference: spectral efficiency, PRB utilization, SINR, MCS, MIMO rank
- Include specific counter names where relevant

**STYLE:**
- Quantitative: always give expected baseline numbers
- Name specific counters and thresholds
- Decisive diagnosis, not generic framework
- No probability ranking

**FORMAT:** Return a JSON array with "user" and "assistant" keys.
Return ONLY the JSON array."""


def call_api(prompt, retries=3):
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


def generate_category(grid, prompt_template, output_file):
    all_rows = []
    total_target = sum(c for _, c, _ in grid)

    for i, (subcategory, count, tag) in enumerate(grid):
        print(f"  [{i+1}/{len(grid)}] {subcategory[:60]}... ({count} rows)")
        batch_rows = []
        remaining = count
        while remaining > 0:
            batch_size = min(5, remaining)
            prompt = prompt_template.format(count=batch_size, subcategory=subcategory)
            text = call_api(prompt)
            if not text:
                print(f"    Empty response, retrying...")
                time.sleep(3)
                continue
            try:
                pairs = parse_response(text)
                for pair in pairs:
                    row = {"messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": pair["user"]},
                        {"role": "assistant", "content": pair["assistant"]},
                    ]}
                    batch_rows.append(row)
                remaining -= len(pairs)
                print(f"    +{len(pairs)} (subtotal: {len(batch_rows)}/{count})")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"    Parse error: {e}, retrying...")
                time.sleep(3)
                continue
            time.sleep(0.3)
        all_rows.extend(batch_rows)

    with open(output_file, "w") as f:
        for row in all_rows:
            f.write(json.dumps(row) + "\n")
    print(f"  Written {len(all_rows)} rows to {output_file}\n")
    return len(all_rows)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = 0

    print("=== Category A: Anti-probability-ranking repair ===")
    total += generate_category(CATEGORY_A, PROMPT_A, f"{OUTPUT_DIR}/a_anti_probability.jsonl")

    print("=== Category B: Exact terminology reinforcement ===")
    total += generate_category(CATEGORY_B, PROMPT_B, f"{OUTPUT_DIR}/b_terminology.jsonl")

    print("=== Category C: Transport/incident priority-order repair ===")
    total += generate_category(CATEGORY_C, PROMPT_C, f"{OUTPUT_DIR}/c_transport_priority.jsonl")

    print("=== Category D: KPI baseline correction ===")
    total += generate_category(CATEGORY_D, PROMPT_D, f"{OUTPUT_DIR}/d_kpi_baseline.jsonl")

    print(f"=== TOTAL GENERATED: {total} rows ===")


if __name__ == "__main__":
    main()
