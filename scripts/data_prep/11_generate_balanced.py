#!/usr/bin/env python3
"""
11_generate_balanced.py — Sequential, coverage-grid-based synthetic data generator.

Fixes issues from 09_generate_v2_synthetic.py:
  - Sequential API calls (no threading stalls)
  - Coverage grid ensures balanced topic distribution
  - Generates in small focused batches per topic
  - Resumes from existing files

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  python 11_generate_balanced.py --category kpi_rebalance
  python 11_generate_balanced.py --category protocol
  python 11_generate_balanced.py --category troubleshooting
  python 11_generate_balanced.py --category all

Outputs to: data/v2_synthetic/
"""

import anthropic
import httpx
import json
import os
import sys
import time
import random
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "v2_synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = (
    "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
    "You have deep knowledge of 3GPP standards, 5G/LTE network operations, RAN optimization, "
    "core network, transport, and IMS/VoLTE. You assist network engineers with diagnostics, "
    "configuration, troubleshooting, and standards interpretation."
)

# ─── Coverage Grids ──────────────────────────────────────────────────────────
# Each entry: (topic, target_count, [theme seeds])

KPI_REBALANCE_GRID = [
    ("VoLTE / IMS / Voice", 100, [
        "VoLTE MOS score degrading below 3.5 — codec, jitter, packet loss analysis",
        "VoLTE call setup time exceeding 3 seconds — SIP signaling delays",
        "IMS registration failure rate increase — P-CSCF, S-CSCF diagnostics",
        "SIP 503 errors from P-CSCF during busy hour — capacity vs config",
        "VoLTE codec negotiation failing — EVS to AMR-WB fallback triggers",
        "eSRVCC preparation failure rate high — inter-RAT voice continuity",
        "VoNR call setup failure on 5G SA — EPS fallback triggers",
        "RTP packet loss causing voice quality degradation — transport vs radio",
        "VoLTE jitter exceeding 30ms causing choppy audio",
        "One-way audio on VoLTE calls — NAT traversal and media path issues",
    ]),
    ("Signaling / Core", 100, [
        "NAS signaling storm from massive IoT device registration",
        "Paging congestion due to incorrect TAI list configuration",
        "S1AP reset frequency increasing on specific eNBs",
        "NGAP UE context release rate abnormally high",
        "GTPv2 create session response latency from SMF",
        "MME overload causing attach reject with cause #22",
        "AMF selection failure during inter-PLMN handover",
        "Diameter Rx interface timeout causing QoS bearer setup failure",
        "SCTP association failure between eNB and MME",
        "NAS authentication failure rate spike after HSS migration",
    ]),
    ("Transport / Backhaul", 80, [
        "S1/NG interface flapping — SCTP heartbeat timeout tuning",
        "IPsec tunnel between eNB and SecGW dropping packets — MTU and fragmentation",
        "Fronthaul link CRC errors causing DU-RU sync loss",
        "VLAN misconfiguration causing management and data plane mixing",
        "Clock synchronization failure on remote cell site — PTP and GPS issues",
        "Asymmetric routing causing path MTU issues on X2 interface",
        "Backhaul congestion causing packet drops during busy hour",
        "Microwave link degradation during rain — adaptive modulation impact on capacity",
    ]),
    ("Interference / RF", 100, [
        "Uplink interference (RTWP/IoT) rising on specific sectors — external vs internal",
        "SSB beam RSRP imbalance across sectors — antenna and beamforming issues",
        "CQI distribution degradation after neighbor cell activation",
        "PIM (passive intermodulation) causing uplink noise floor rise",
        "Cross-border interference on specific EARFCN/NR-ARFCN",
        "Pilot pollution in dense urban — excessive overlap causing poor SINR",
        "Uplink interference from external sources — spectrum scanner analysis",
        "DL interference pattern appearing at specific time of day",
        "Adjacent channel interference after new carrier activation",
        "Antenna feeder fault causing VSWR alarm and coverage impact",
    ]),
    ("Energy / Infra", 60, [
        "Energy consumption per GB trending upward — capacity vs efficiency",
        "Cell sleep mode not activating during low-traffic hours — parameter audit",
        "MIMO layer adaptation stuck on 2-layer despite capable UEs",
        "Power amplifier efficiency degradation — thermal and aging effects",
        "Battery backup runtime declining — load vs capacity analysis",
        "Solar-powered site energy budget management in off-grid deployment",
    ]),
    ("Handover / Mobility (gaps)", 60, [
        "Inter-RAT handover 5G to 4G failure — B1 threshold and gap configuration",
        "Conditional handover (CHO) execution failure — candidate cell evaluation",
        "DAPS handover interruption time exceeding target — dual active protocol",
        "Ping-pong handover between macro and small cell — hysteresis tuning",
        "Inter-gNB PSCell change failure in NR-DC — Xn interface issues",
        "SRVCC handover failure — IMS to CS voice continuity breakdown",
    ]),
]

PROTOCOL_GRID = [
    ("Mobility Procedures", 600, [
        "Tracking Area Update (TAU) procedure in LTE — triggers, messages, timers",
        "5G registration — initial vs mobility vs periodic vs emergency",
        "Service request in 5G SA — signaling flow and UE states",
        "Deregistration — UE-initiated vs network-initiated",
        "N2 handover — preparation, execution, completion phases",
        "Paging procedure — 5G vs LTE differences, DRX interaction",
        "RRC connection re-establishment after radio link failure",
        "Inter-system handover — EPC to 5GC and back",
    ]),
    ("Session Management", 600, [
        "PDU session establishment end-to-end — UE to DN",
        "PDU session modification — QoS flow add/modify/delete",
        "PFCP session establishment between SMF and UPF — PDR, FAR, QER, URR rules",
        "GTP-U tunnel management on N3 and N9 interfaces",
        "UPF selection criteria and SMF decision logic",
        "Uplink classifier and branching point for multi-homed PDU sessions",
        "PDU session types — IPv4, IPv6, IPv4v6, Ethernet, Unstructured",
        "Always-on PDU session and its operational implications",
    ]),
    ("Network Slicing", 500, [
        "S-NSSAI structure — SST, SD values and their meaning",
        "Network slice selection — NSSF role and NSSAI negotiation",
        "AMF set/slice discovery via NRF for slice-specific routing",
        "Network slice admission control and SLA enforcement",
        "Cross-slice resource isolation mechanisms",
        "Slice-specific authentication and authorization (NSSAA)",
        "URLLC slice configuration — QoS, scheduling priority, preemption",
        "eMBB vs mMTC vs URLLC slice design differences",
    ]),
    ("RAN Architecture", 500, [
        "CU-DU split — CU-CP, CU-UP, DU roles and interfaces",
        "F1-C and F1-U protocol stack between CU and DU",
        "E1 interface between CU-CP and CU-UP",
        "RRC state machine in NR — IDLE, INACTIVE, CONNECTED transitions",
        "RRC setup, reconfiguration, and release procedures",
        "MAC scheduler — time-domain and frequency-domain scheduling",
        "Logical, transport, and physical channel mapping in NR",
        "Semi-persistent scheduling (SPS) and configured grant",
    ]),
    ("O-RAN", 500, [
        "O-RAN architecture — O-CU, O-DU, O-RU and open interfaces",
        "Open fronthaul (7.2x split) — control, user, sync, management planes",
        "Near-RT RIC — xApps, E2 interface, conflict management",
        "Non-RT RIC — rApps, A1 interface, policy and enrichment",
        "O-RAN vs 3GPP — relationship, overlaps, and scope differences",
        "SMO framework and O1/O2 interfaces",
        "O-RAN security architecture and threat model",
        "Multi-vendor interoperability testing in O-RAN",
    ]),
    ("PHY / Beam Management", 400, [
        "SSB beam sweeping, measurement, and reporting",
        "CSI-RS based beam management and L1-RSRP reporting",
        "Beam failure detection and recovery procedure",
        "BWP (bandwidth part) configuration and switching",
        "CORESET and search space configuration for PDCCH",
        "HARQ operation in NR — process management, feedback timing",
        "DMRS configuration and channel estimation",
        "SRS configuration and uplink beam management",
    ]),
    ("Carrier Aggregation / DC", 400, [
        "EN-DC (Option 3x) — MCG, SCG bearer types and split bearer",
        "NR-DC (Option 4) — MN and SN roles",
        "SA NR carrier aggregation — intra-band and inter-band",
        "SCell activation/deactivation and dormant BWP",
        "LTE-NR CA vs DC — when to use which",
        "SCG failure handling and recovery procedures",
        "Power control in dual connectivity scenarios",
        "Fast MCG link recovery in EN-DC",
    ]),
    ("QoS Framework", 500, [
        "5G QoS model — QoS flows, QoS rules, and QFI",
        "5QI to QoS characteristics mapping — standardized vs non-standardized",
        "GBR vs non-GBR vs delay-critical GBR bearers",
        "Reflective QoS and derived QoS rules",
        "QoS notification control and policy enforcement at PCF",
        "EPS bearer to 5G QoS flow mapping during interworking",
        "MDBV (maximum data burst volume) for URLLC flows",
        "QoS flow binding to DRB and scheduling priority",
    ]),
    ("IMS / Voice", 500, [
        "IMS architecture — P/I/S-CSCF roles and SIP signaling",
        "VoLTE call flow — SIP INVITE to media negotiation",
        "EPS fallback for voice — from 5G SA to LTE",
        "SRVCC procedure — PS to CS voice continuity",
        "IMS emergency call — routing and location reporting",
        "VoNR end-to-end call flow on 5G SA",
        "IMS registration and re-registration — timers and edge cases",
        "SDP offer/answer for codec negotiation — EVS, AMR-WB, AMR-NB",
    ]),
    ("Security", 400, [
        "5G security architecture — AUSF, SEAF, ARPF, SIDF",
        "5G-AKA vs EAP-AKA' authentication procedures",
        "SUPI/SUCI privacy mechanism in 5G",
        "NAS and AS security — ciphering and integrity protection",
        "Security edge protection proxy (SEPP) for roaming",
        "Network domain security using TLS on SBI interfaces",
        "Subscriber key hierarchy — K, CK, IK, KAUSF, KAMF, KgNB",
        "Replay protection and bidding-down attack prevention",
    ]),
    ("SBA / Core NFs", 600, [
        "Service-based architecture — NF discovery, selection, communication",
        "NRF — NF registration, discovery, and subscription",
        "HTTP/2 based SBI interface and service-based interactions",
        "AMF — GUAMI allocation, UE context management, NAS termination",
        "SMF — session management, IP allocation, UPF control",
        "PCF — policy rules, PCC rules, and subscription data",
        "UDM/UDR — subscriber data management and storage",
        "NEF — exposure framework for third-party applications",
        "NWDAF — network analytics, data collection, and ML-based predictions",
        "SCP — service communication proxy and indirect communication",
    ]),
    ("Compare & Contrast", 500, [
        "S-NSSAI vs DNN — what each identifies and when each matters",
        "N2 vs N3 interface — control plane vs user plane paths",
        "EPS bearer vs 5G QoS flow — mapping and migration",
        "CU vs DU — what runs where and why the split exists",
        "TAU (4G) vs Registration Update (5G) — procedures compared",
        "GTP-C vs PFCP — control protocols for user plane management",
        "AMF vs MME — function mapping between 5G and 4G core",
        "Xn vs X2 — inter-node interfaces in 5G vs LTE",
        "SBA vs point-to-point interfaces — architectural evolution",
        "NSA vs SA deployment — architecture, limitations, migration path",
    ]),
]

TROUBLESHOOTING_GRID = [
    ("Radio / RF Issues", 500, [
        "User complains of no service in a 5G coverage area",
        "Massive MIMO cell showing poor sector throughput despite low load",
        "Sudden CQI degradation on multiple cells at same site",
        "Cell showing high PRB utilization but low user count",
        "Poor indoor coverage after new building construction nearby",
        "Interference pattern appearing every evening 6-8pm",
        "Single user poor speed — isolate UE vs network issue",
        "SSB beam coverage hole in specific azimuth direction",
    ]),
    ("Voice / VoLTE Issues", 400, [
        "Users unable to make VoLTE calls but data works fine",
        "One-way audio on VoLTE calls — direction-specific",
        "VoLTE call drops at cell edge during handover",
        "Poor voice quality (MOS < 3.0) on specific cells",
        "VoLTE call setup failure — SIP 486 Busy Here from network side",
        "SRVCC handover failing — user falls to no-service during CS fallback",
        "Emergency call (112/911) routing failure on specific site",
        "VoNR not activating despite 5G SA registration success",
    ]),
    ("Core / Signaling Issues", 400, [
        "Users unable to register after MME/AMF software upgrade",
        "PDN/PDU session setup failure for specific APN/DNN",
        "Data works but DNS resolution failing for users",
        "Roaming users unable to access data services",
        "Dedicated bearer setup failure for enterprise VPN APN",
        "Intermittent data stall 2-5 seconds during mobility",
        "TAU reject causing UE to go into limited service mode",
        "Massive attach storm after site outage recovery",
    ]),
    ("Transport Issues", 400, [
        "S1/NG interface flapping between RAN and core",
        "IPsec tunnel dropping packets — MTU and PMTUD issues",
        "Fronthaul CRC errors causing DU-RU sync loss",
        "Clock synchronization failure — PTP/GPS diagnostics",
        "VLAN misconfiguration causing management and user plane mixing",
        "Microwave link degradation during rain — capacity impact",
        "Asymmetric routing causing X2/Xn path issues",
        "Transport QoS misconfiguration causing VoLTE packet drops",
    ]),
    ("Multi-Domain / Operations", 500, [
        "New site integration — end-to-end checklist and verification",
        "Post-swap cell verification — KPI acceptance criteria",
        "Mass event (concert/stadium) capacity planning and tuning",
        "Network sharing (MOCN) — diagnosing partner-specific issue",
        "Firmware upgrade rollback — when and how to decide",
        "Alarm correlation — linking transport alarms to RAN KPI impact",
        "Drive test analysis — translating measurements to parameter changes",
        "Neighbor relation audit — missing, one-way, or conflicting definitions",
    ]),
    ("5G-Specific Issues", 400, [
        "UE stuck in LTE despite 5G NSA coverage available",
        "EN-DC SCG addition failure — SgNB add reject analysis",
        "5G SA registration success but no data — PDU session issue",
        "NR cell reselection not happening — SIB priorities misconfigured",
        "mmWave cell excessive handover — beam management tuning",
        "5G throughput not matching expected for TDD pattern",
        "NSA to SA migration — UE behavior differences and issues",
        "Network slice not being selected — NSSAI configuration problem",
    ]),
    ("Performance Optimization", 400, [
        "Cell throughput 40% below theoretical maximum — systematic analysis",
        "Uplink-limited cell in dense urban — PUSCH optimization",
        "Massive MIMO beamforming not providing expected gain",
        "Carrier aggregation benefit less than expected — activation rate low",
        "DL scheduling efficiency poor — CCE/PDCCH bottleneck",
        "Sleep mode / energy saving not reducing power consumption",
        "Latency optimization for gaming/URLLC traffic on shared cell",
        "Coverage-capacity tradeoff — optimal power and tilt settings",
    ]),
]

# ─── Generation Prompts ──────────────────────────────────────────────────────

KPI_PROMPT = """Generate {batch_size} unique telecom training examples about KPI analysis and root cause analysis.

**Topic area:** {topic}
**Specific theme:** {theme}

Generate realistic questions a network engineer would ask, with detailed expert answers.

**Answer must include:**
- What the symptom means operationally
- 3-5 likely causes ranked by probability
- For each cause: specific counters/logs/parameters to inspect
- Concrete remediation actions
- Real counter names, timer values, parameter names

**Vary the format:** {format_instruction}

Return ONLY a JSON array of objects with "question" and "answer" fields. No markdown wrapping."""

PROTOCOL_PROMPT = """Generate {batch_size} unique telecom training examples about protocol knowledge.

**Topic area:** {topic}
**Specific theme:** {theme}

Generate realistic questions and detailed expert answers.

**Answer must include:**
- Plain-English explanation first
- Relevant 3GPP spec reference (e.g., TS 23.501)
- Specific message names and signaling flows
- Error cases and operational relevance

**Vary the format:** {format_instruction}

Return ONLY a JSON array of objects with "question" and "answer" fields. No markdown wrapping."""

TROUBLESHOOT_PROMPT = """Generate {batch_size} unique telecom troubleshooting training examples.

**Topic area:** {topic}
**Specific theme:** {theme}

Frame questions as real trouble tickets with symptoms and context.

**Answer must include:**
- Numbered step-by-step investigation
- At each step: what to check, tool/command to use, what result means
- Decision branches: "If X → step N; if Y → step M"
- Specific CLI commands, counter names, alarm IDs
- Resolution actions and verification
- Escalation path

**Vary the format:** {format_instruction}

Return ONLY a JSON array of objects with "question" and "answer" fields. No markdown wrapping."""

FORMAT_INSTRUCTIONS = [
    "Use structured sections with headers and numbered steps.",
    "Use flowing paragraphs with embedded reasoning — no bullet points.",
    "Use concise bullet-point format — direct and actionable.",
    "Use a mix of structured headers for causes and paragraph for analysis.",
    "Use a decision-tree format with clear branching logic.",
]

# ─── Engine ──────────────────────────────────────────────────────────────────

def generate_batch(client, prompt, model):
    """Make a single API call, return list of QA pairs."""
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                temperature=0.9,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Extract JSON
            if text.startswith("["):
                examples = json.loads(text)
            else:
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    examples = json.loads(text[start:end])
                else:
                    print(f"    ⚠ No JSON array found, retry {attempt+1}")
                    continue

            valid = [ex for ex in examples
                     if isinstance(ex, dict) and "question" in ex and "answer" in ex
                     and len(ex["answer"]) > 100]
            if valid:
                return valid
            print(f"    ⚠ No valid examples, retry {attempt+1}")

        except json.JSONDecodeError as e:
            print(f"    ⚠ JSON error: {e}, retry {attempt+1}")
        except anthropic.RateLimitError:
            wait = 15 * (attempt + 1)
            print(f"    ⏳ Rate limit, waiting {wait}s...")
            time.sleep(wait)
        except anthropic.APIError as e:
            print(f"    ⚠ API error: {e}, retry {attempt+1}")
            time.sleep(5)
        except httpx.TimeoutException:
            print(f"    ⏳ Request timed out (>120s), retry {attempt+1}")
            time.sleep(3)
        except Exception as e:
            print(f"    ⚠ Unexpected error: {e}, retry {attempt+1}")
            time.sleep(5)
    return []


def format_training(question, answer):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
    }


def get_line_count(path):
    if not path.exists():
        return 0
    with open(path) as f:
        return sum(1 for _ in f)


def run_grid(client, grid, prompt_template, output_file, batch_size, model):
    """Generate data according to a coverage grid."""
    existing = get_line_count(output_file)
    total_target = sum(count for _, count, _ in grid)

    if existing >= total_target:
        print(f"✅ {output_file.name}: {existing}/{total_target} already done")
        return existing

    print(f"\n{'='*60}")
    print(f"🔄 Generating: {output_file.name}")
    print(f"   Existing: {existing}, Target: {total_target}, Remaining: {total_target - existing}")
    print(f"{'='*60}")

    # Figure out how much each topic needs, accounting for existing data
    # Simple approach: skip topics proportionally based on existing count
    records_to_skip = existing
    generated_total = existing

    with open(output_file, "a") as f:
        for topic_name, topic_target, themes in grid:
            if records_to_skip >= topic_target:
                records_to_skip -= topic_target
                print(f"\n  ⏭ {topic_name}: {topic_target} — already covered, skipping")
                continue

            # Partial skip
            topic_remaining = topic_target - records_to_skip
            records_to_skip = 0

            print(f"\n  📝 {topic_name}: generating {topic_remaining}")
            topic_generated = 0

            consecutive_failures = 0
            while topic_generated < topic_remaining:
                theme = random.choice(themes)
                fmt = random.choice(FORMAT_INSTRUCTIONS)
                batch = min(batch_size, topic_remaining - topic_generated)

                prompt = prompt_template.format(
                    batch_size=batch,
                    topic=topic_name,
                    theme=theme,
                    format_instruction=fmt,
                )

                examples = generate_batch(client, prompt, model)

                if not examples:
                    consecutive_failures += 1
                    print(f"    ⚠ Empty batch ({consecutive_failures} consecutive failures)")
                    if consecutive_failures >= 5:
                        print(f"    ❌ Too many failures, skipping rest of {topic_name}")
                        break
                    time.sleep(5)
                    continue

                consecutive_failures = 0
                for ex in examples:
                    if topic_generated >= topic_remaining:
                        break
                    record = format_training(ex["question"], ex["answer"])
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    topic_generated += 1
                    generated_total += 1

                f.flush()
                print(f"    [{generated_total}/{total_target}] +{len(examples)} from: {theme[:50]}...")

                time.sleep(0.5)  # Gentle pacing

            print(f"  ✅ {topic_name}: done ({topic_generated} generated)")

    final = get_line_count(output_file)
    print(f"\n✅ {output_file.name}: {final} total records")
    return final


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True,
                        choices=["kpi_rebalance", "protocol", "troubleshooting", "all"])
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--model", default="claude-sonnet-4-20250514")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Set ANTHROPIC_API_KEY first")
        sys.exit(1)

    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=120.0,  # 2 min timeout on all HTTP requests
    )
    random.seed(42)

    print(f"📊 Balanced Synthetic Data Generator")
    print(f"   Model: {args.model}")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Category: {args.category}")

    t0 = time.time()
    results = {}

    if args.category in ("kpi_rebalance", "all"):
        results["kpi_rebalance"] = run_grid(
            client, KPI_REBALANCE_GRID, KPI_PROMPT,
            OUTPUT_DIR / "kpi_rca_rebalance.jsonl", args.batch_size, args.model
        )

    if args.category in ("protocol", "all"):
        results["protocol"] = run_grid(
            client, PROTOCOL_GRID, PROTOCOL_PROMPT,
            OUTPUT_DIR / "protocol_balanced.jsonl", args.batch_size, args.model
        )

    if args.category in ("troubleshooting", "all"):
        results["troubleshooting"] = run_grid(
            client, TROUBLESHOOTING_GRID, TROUBLESHOOT_PROMPT,
            OUTPUT_DIR / "troubleshooting_balanced.jsonl", args.batch_size, args.model
        )

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"📊 DONE — {elapsed/60:.1f} minutes")
    for k, v in results.items():
        print(f"   {k}: {v} records")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
