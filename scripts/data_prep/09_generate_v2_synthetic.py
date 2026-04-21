#!/usr/bin/env python3
"""
09_generate_v2_synthetic.py — Generate ~15K synthetic training examples using Claude API.

Targets the weak areas from Llama v1 benchmark:
  - KPI/RCA reasoning (61.1%) → 6,000 examples
  - Protocol knowledge (73.0%) → 6,000 examples
  - Troubleshooting chains        → 3,000 examples

Uses parallel API calls (10 concurrent) for speed while keeping Sonnet for quality.

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  python 09_generate_v2_synthetic.py [--batch-size 15] [--workers 10] [--model claude-sonnet-4-20250514]

Outputs to: data/v2_synthetic/
"""

import anthropic
import json
import os
import sys
import time
import random
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "v2_synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = (
    "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
    "You have deep knowledge of 3GPP standards, 5G/LTE network operations, RAN optimization, "
    "core network, transport, and IMS/VoLTE. You assist network engineers with diagnostics, "
    "configuration, troubleshooting, and standards interpretation."
)

# ─── Topic Seeds ─────────────────────────────────────────────────────────────

KPI_THEMES = [
    # Accessibility
    "RRC setup success rate dropping below 95% on 5G NR cells",
    "RACH failure rate spike on specific LTE sectors",
    "Attach success rate degradation in MME pool",
    "RAN paging success rate drop during busy hour",
    "S1 setup failure rate increase after software upgrade",
    "SgNB addition success rate low in EN-DC",
    "Random access preamble collision rate increasing",
    "NG setup failure between gNB and AMF",
    # Retainability
    "ERAB drop rate exceeding 1% threshold on LTE cells",
    "5G NR call drop rate spike in specific tracking area",
    "VoLTE call drop during SRVCC handover",
    "PDU session release abnormal rate increase",
    "Bearer modification failure rate climbing",
    "Context release due to UE inactivity timer misconfiguration",
    "Radio link failure rate increase after antenna tilt change",
    "DRB retainability degradation on mmWave cells",
    # Throughput / Data
    "Cell DL throughput 50% below expected for 20MHz LTE cell",
    "5G NR UE throughput low despite good SINR (>20dB)",
    "UL throughput degradation during rain events on mmWave",
    "User-perceived throughput drop in dense urban macro",
    "TCP throughput low despite good radio conditions (bufferbloat)",
    "Carrier aggregation not activating despite capable UEs",
    "Peak throughput regression after parameter change",
    "MCS distribution skewed to low values despite good RF",
    # Latency
    "RTT latency exceeding 50ms on 5G SA network",
    "Control plane latency high during registration procedure",
    "User plane latency spike on URLLC slice",
    "GTP-U tunnel delay increasing on N3 interface",
    "Fronthaul latency jitter causing scheduling issues",
    "Core network signaling latency during AMF overload",
    # Handover
    "Inter-RAT handover success rate below 90% (5G to LTE)",
    "Intra-frequency handover failure rate spike",
    "Inter-frequency handover ping-pong between layers",
    "X2 handover preparation failure rate high",
    "Xn handover failure between gNBs from different vendors",
    "Conditional handover (CHO) execution failure",
    "DAPS handover interruption time exceeding target",
    "Inter-gNB PSCell change failure in NR-DC",
    # VoLTE / IMS
    "VoLTE MOS score degrading below 3.5",
    "VoLTE call setup time exceeding 3 seconds",
    "IMS registration failure rate increase",
    "SIP 503 errors from P-CSCF during busy hour",
    "VoLTE codec negotiation failing (EVS to AMR-WB fallback)",
    "eSRVCC preparation failure rate high",
    "VoNR call setup failure on 5G SA",
    "RTP packet loss causing voice quality degradation",
    # Utilization / Capacity
    "PRB utilization exceeding 80% on LTE cells",
    "PDCCH CCE utilization causing scheduling bottleneck",
    "PUSCH BLER high on cell-edge users",
    "Uplink interference (RTWP/IoT) rising on specific sectors",
    "SSB beam RSRP imbalance across sectors",
    "CQI distribution degradation after neighbor cell activation",
    "DL power utilization reaching maximum on specific carrier",
    "Transport backhaul utilization at 90% causing packet drops",
    # Energy / Infra
    "Energy consumption per GB trending upward",
    "Cell sleep mode not activating during low-traffic hours",
    "MIMO layer adaptation not working (stuck on 2-layer)",
    "Power headroom report showing UE at max power",
    # Signaling
    "NAS signaling storm from massive IoT device registration",
    "Paging congestion due to incorrect TAI list configuration",
    "S1AP reset frequency increasing on specific eNBs",
    "NGAP UE context release rate abnormally high",
    "GTPv2 create session response latency from SMF",
]

PROTOCOL_THEMES = [
    # Core mobility
    "Tracking Area Update (TAU) procedure in LTE — triggers, messages, timers",
    "5G registration procedure — initial vs mobility vs periodic vs emergency",
    "Service request procedure in 5G SA — signaling flow and UE states",
    "PDU session establishment end-to-end — UE to DN",
    "PDU session modification — QoS flow add/modify/delete",
    "AN release and UE context management at AMF",
    "Deregistration procedure — UE-initiated vs network-initiated",
    "N2 handover procedure — preparation, execution, completion phases",
    # User plane
    "PFCP session establishment between SMF and UPF — rules (PDR, FAR, QER, URR)",
    "GTP-U tunnel management on N3 and N9 interfaces",
    "UPF selection criteria and SMF decision logic",
    "Uplink classifier and branching point for multi-homed PDU sessions",
    "N6 interface and traffic detection function (TDF)",
    "Buffering and paging at UPF for idle-mode UE data",
    # Slicing
    "S-NSSAI structure — SST, SD values and their meaning",
    "Network slice selection — NSSF role and NSSAI negotiation",
    "AMF set/slice discovery via NRF for slice-specific routing",
    "Network slice admission control and SLA enforcement",
    "Cross-slice resource isolation mechanisms",
    "Slice-specific authentication and authorization (NSSAA)",
    # RAN architecture
    "CU-DU split architecture — CU-CP, CU-UP, DU roles and interfaces",
    "F1-C and F1-U protocol stack between CU and DU",
    "E1 interface between CU-CP and CU-UP",
    "RRC state machine in NR — IDLE, INACTIVE, CONNECTED transitions",
    "RRC setup, reconfiguration, and release procedures",
    "MAC scheduler operation — time-domain and frequency-domain scheduling",
    # O-RAN
    "O-RAN architecture — O-CU, O-DU, O-RU and open interfaces",
    "Open fronthaul interface (7.2x split) — control, user, sync, management planes",
    "Near-RT RIC — xApps, E2 interface, conflict management",
    "Non-RT RIC — rApps, A1 interface, policy and enrichment",
    "O-RAN Alliance specifications vs 3GPP — relationship and scope",
    "SMO framework and O1/O2 interfaces",
    # Beam management / PHY
    "SSB beam management — beam sweeping, measurement, reporting",
    "CSI-RS based beam management — L1-RSRP reporting",
    "Beam failure detection and recovery procedure",
    "BWP (bandwidth part) configuration and switching",
    "CORESET and search space configuration for PDCCH",
    "HARQ operation in NR — process management, feedback timing",
    # Carrier aggregation / DC
    "LTE-NR carrier aggregation configuration",
    "EN-DC (Option 3x) — MCG, SCG bearer types and split bearer",
    "NR-DC (Option 4) — MN and SN roles",
    "SA NR carrier aggregation — intra-band and inter-band",
    "SCell activation/deactivation and dormant BWP",
    # QoS
    "5G QoS model — QoS flows, QoS rules, and QFI",
    "5QI to QoS characteristics mapping — standardized vs non-standardized",
    "GBR vs non-GBR vs delay-critical GBR bearers",
    "Reflective QoS and derived QoS rules",
    "QoS notification control and policy enforcement at PCF",
    # IMS / Voice
    "IMS architecture — P/I/S-CSCF roles and SIP signaling",
    "VoLTE call flow — SIP INVITE to media negotiation",
    "EPS fallback for voice — from 5G SA to LTE",
    "SRVCC procedure — PS to CS voice continuity",
    "IMS emergency call — routing and location reporting",
    "VoNR end-to-end call flow on 5G SA",
    # Security
    "5G security architecture — AUSF, SEAF, ARPF, SIDF",
    "5G-AKA vs EAP-AKA' authentication procedures",
    "SUPI/SUCI privacy mechanism in 5G",
    "NAS and AS security — ciphering and integrity protection",
    "Security edge protection proxy (SEPP) for roaming",
    # SBA / Core
    "Service-based architecture (SBA) — NF discovery, selection, communication",
    "NRF — NF registration, discovery, and subscription",
    "HTTP/2 based SBI interface and service-based interactions",
    "AMF — GUAMI allocation, UE context management",
    "SMF — session management, IP allocation, UPF control",
    "PCF — policy rules, PCC rules, and subscription data",
    "UDM/UDR — subscriber data management and storage",
    "NEF — exposure framework for third-party applications",
    "NWDAF — network analytics and data collection",
]

TROUBLESHOOTING_THEMES = [
    # Radio
    "User complains of no service in a 5G coverage area",
    "Massive MIMO cell showing poor sector throughput despite low load",
    "Users unable to make VoLTE calls but data works fine",
    "Intermittent call drops at specific geographic location",
    "UE stuck in LTE despite 5G NSA coverage available",
    "Poor indoor coverage after new building construction nearby",
    "Interference pattern appearing every evening 6-8pm",
    "Single user complaining poor speed — isolate UE vs network issue",
    "Cell showing high PRB utilization but low user count",
    "Sudden CQI degradation on multiple cells same site",
    # Core
    "Users unable to register on network after MME software upgrade",
    "PDN connectivity request failure for specific APN",
    "Data session works but DNS resolution failing for users",
    "Roaming users unable to access data services",
    "UE getting redirected to 3G despite 4G coverage",
    "Dedicated bearer setup failure for enterprise VPN APN",
    "Intermittent data stall lasting 2-5 seconds during mobility",
    "TAU reject causing UE to go into limited service mode",
    # Transport
    "S1 interface flapping between eNB and EPC",
    "IPsec tunnel between eNB and SecGW dropping packets",
    "Fronthaul link showing CRC errors causing DU-RU sync loss",
    "VLAN misconfiguration causing management and data plane mixing",
    "Clock synchronization failure on remote cell site (PTP/GPS)",
    "Asymmetric routing causing path MTU issues on X2 interface",
    # Multi-domain
    "New site integration — end-to-end checklist and verification",
    "Post-swap cell verification — KPI acceptance criteria",
    "Mass event (concert/stadium) capacity planning and tuning",
    "Network sharing (MOCN) — diagnosing partner-specific issue",
    "Firmware upgrade rollback — when and how to decide",
    "Alarm correlation — linking transport alarms to RAN KPI impact",
    "Drive test analysis — translating measurements to parameter changes",
    "OSS/NMS showing stale data — troubleshooting collection chain",
]

# ─── Generation Templates ────────────────────────────────────────────────────

KPI_GENERATION_PROMPT = """Generate {batch_size} unique telco training examples about KPI analysis and RCA (root cause analysis).

**Theme to focus on:** {theme}

For each example, generate a realistic question a network engineer would ask, and a detailed expert answer.

**Question styles to vary across the batch:**
- "I'm seeing [metric] at [value] on [scope]. What could cause this?"
- "Our [KPI] dropped from [X] to [Y] after [event]. How do I diagnose?"
- "[alarm/threshold] triggered on [element]. Walk me through the RCA."
- "Compare normal vs abnormal [KPI] values and explain the diagnostic approach."

**Answer requirements:**
- Start with interpreting what the symptom means operationally
- List 3-5 likely causes ranked by probability
- For each cause, explain what to inspect (specific counters, logs, parameters)
- End with concrete remediation actions
- Use real counter names, timer values, and parameter names where applicable
- Avoid generic advice like "contact vendor" — be specific

**Format diversity (vary across the batch):**
- 60% structured (sections with headers or numbered steps)
- 20% flowing paragraph with embedded reasoning
- 20% concise bullet-point format

Return ONLY a JSON array of objects, each with "question" and "answer" fields. No markdown, no extra text.
"""

PROTOCOL_GENERATION_PROMPT = """Generate {batch_size} unique telco training examples about protocol knowledge and standards.

**Theme to focus on:** {theme}

For each example, generate a realistic question and detailed expert answer.

**Question styles to vary across the batch:**
- "Explain [procedure/concept] in detail."
- "What's the difference between [A] and [B]?"
- "Walk me through the [procedure] message flow step by step."
- "What happens if [misconfiguration/failure] occurs during [procedure]?"
- "How does [component A] interact with [component B] during [scenario]?"

**Answer requirements:**
- Start with plain-English explanation of the concept
- Include the relevant 3GPP specification reference (e.g., TS 23.501, TS 38.331)
- Explain the signaling flow or architecture with specific message names
- Cover error cases and what goes wrong in practice
- Connect to operational relevance (why an engineer should care)

**Format diversity:**
- 60% structured with clear sections
- 20% compare-and-contrast tables or lists
- 20% narrative explanation

Return ONLY a JSON array of objects, each with "question" and "answer" fields. No markdown, no extra text.
"""

TROUBLESHOOTING_GENERATION_PROMPT = """Generate {batch_size} unique telco training examples about troubleshooting workflows.

**Theme to focus on:** {theme}

For each example, generate a realistic trouble ticket scenario and expert diagnosis.

**Question format:**
Frame as a real scenario: "We're seeing [symptom]. [Context]. How should we investigate?"

**Answer requirements:**
- Step-by-step investigation workflow (numbered steps)
- At each step: what to check, what tool/command/counter to use, what the result means
- Decision points: "If you see X, go to step N; if Y, go to step M"
- Include specific CLI commands, counter names, alarm IDs where applicable
- End with resolution actions and verification steps
- Include an escalation path if root cause isn't found

**Format diversity:**
- 70% structured step-by-step diagnosis tree
- 20% investigation workflow with decision branches
- 10% escalation narrative with resolution

Return ONLY a JSON array of objects, each with "question" and "answer" fields. No markdown, no extra text.
"""


# ─── Generation Engine (Parallel) ────────────────────────────────────────────

write_lock = threading.Lock()


def generate_batch(client, prompt_template, theme, batch_size, model):
    """Generate a batch of examples for a given theme."""
    prompt = prompt_template.format(batch_size=batch_size, theme=theme)

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                temperature=0.9,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()

            # Try to extract JSON array from response
            if text.startswith("["):
                examples = json.loads(text)
            else:
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    examples = json.loads(text[start:end])
                else:
                    print(f"  ⚠ No JSON array found, retrying...")
                    continue

            # Validate structure
            valid = []
            for ex in examples:
                if isinstance(ex, dict) and "question" in ex and "answer" in ex:
                    if len(ex["answer"]) > 100:
                        valid.append(ex)

            if valid:
                return valid
            else:
                print(f"  ⚠ No valid examples in batch, retrying...")

        except json.JSONDecodeError as e:
            print(f"  ⚠ JSON parse error: {e}, retrying...")
        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"  ⏳ Rate limited, waiting {wait}s...")
            time.sleep(wait)
        except anthropic.APIError as e:
            print(f"  ⚠ API error: {e}, retrying...")
            time.sleep(5)

    return []


def format_as_training(question, answer):
    """Format a QA pair as a ChatML training example."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
    }


def get_progress(output_file):
    """Count existing examples in an output file."""
    if not output_file.exists():
        return 0
    with open(output_file) as f:
        return sum(1 for _ in f)


def worker_task(client, prompt_template, theme, batch_size, model, output_file, task_id):
    """Single worker: generate a batch and write to file."""
    examples = generate_batch(client, prompt_template, theme, batch_size, model)
    count = 0

    if examples:
        with write_lock:
            with open(output_file, "a") as f:
                for ex in examples:
                    record = format_as_training(ex["question"], ex["answer"])
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1
                f.flush()

    return count


def run_generator(client, name, prompt_template, themes, target_count, output_file, batch_size, model, max_workers):
    """Generate examples for one category using parallel workers."""
    existing = get_progress(output_file)
    if existing >= target_count:
        print(f"✅ {name}: {existing}/{target_count} already done, skipping")
        return existing

    remaining = target_count - existing
    print(f"\n{'='*60}")
    print(f"🔄 {name}: {existing}/{target_count} done, generating {remaining} more ({max_workers} parallel workers)")
    print(f"{'='*60}")

    generated = existing
    theme_idx = 0

    # Build task queue — one task per batch
    tasks = []
    temp_remaining = remaining
    while temp_remaining > 0:
        batch = min(batch_size, temp_remaining)
        theme = themes[theme_idx % len(themes)]
        tasks.append((theme, batch))
        temp_remaining -= batch
        theme_idx += 1

    print(f"  📋 Queued {len(tasks)} batches across {len(themes)} themes")

    completed_batches = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, (theme, batch) in enumerate(tasks):
            future = executor.submit(
                worker_task, client, prompt_template, theme, batch, model, output_file, i
            )
            futures[future] = (i, theme, batch)

        for future in as_completed(futures):
            i, theme, batch = futures[future]
            try:
                count = future.result()
                generated += count
                completed_batches += 1

                if completed_batches % 10 == 0 or completed_batches == len(tasks):
                    print(f"  📊 [{generated}/{target_count}] — {completed_batches}/{len(tasks)} batches done")

            except Exception as e:
                print(f"  ❌ Batch {i} failed: {e}")

    # Verify final count from file
    final_count = get_progress(output_file)
    print(f"✅ {name}: {final_count}/{target_count} complete")
    return final_count


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic telco training data via Claude API")
    parser.add_argument("--batch-size", type=int, default=15, help="Examples per API call (default: 15)")
    parser.add_argument("--workers", type=int, default=10, help="Parallel API calls (default: 10)")
    parser.add_argument("--model", default="claude-sonnet-4-20250514", help="Claude model to use")
    parser.add_argument("--kpi-count", type=int, default=6000, help="KPI/RCA examples to generate")
    parser.add_argument("--protocol-count", type=int, default=6000, help="Protocol examples to generate")
    parser.add_argument("--troubleshoot-count", type=int, default=3000, help="Troubleshooting examples to generate")
    parser.add_argument("--dry-run", action="store_true", help="Generate 5 examples per category to test")
    args = parser.parse_args()

    if args.dry_run:
        args.kpi_count = 5
        args.protocol_count = 5
        args.troubleshoot_count = 5
        args.batch_size = 5
        args.workers = 3
        print("🧪 DRY RUN: generating 5 examples per category\n")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set. Export it first:")
        print('   export ANTHROPIC_API_KEY="sk-ant-..."')
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    total_target = args.kpi_count + args.protocol_count + args.troubleshoot_count

    print(f"📊 Synthetic Data Generator for Llama v2 (PARALLEL)")
    print(f"   Model: {args.model}")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Parallel workers: {args.workers}")
    print(f"   Targets: KPI={args.kpi_count}, Protocol={args.protocol_count}, Troubleshoot={args.troubleshoot_count}")
    print(f"   Total: {total_target}")
    print(f"   Output: {OUTPUT_DIR}")

    # Shuffle themes for variety across runs
    random.seed(42)
    kpi_themes = KPI_THEMES.copy()
    proto_themes = PROTOCOL_THEMES.copy()
    ts_themes = TROUBLESHOOTING_THEMES.copy()
    random.shuffle(kpi_themes)
    random.shuffle(proto_themes)
    random.shuffle(ts_themes)

    t0 = time.time()

    kpi_done = run_generator(
        client, "KPI/RCA", KPI_GENERATION_PROMPT, kpi_themes,
        args.kpi_count, OUTPUT_DIR / "kpi_rca.jsonl", args.batch_size, args.model, args.workers
    )

    proto_done = run_generator(
        client, "Protocol Knowledge", PROTOCOL_GENERATION_PROMPT, proto_themes,
        args.protocol_count, OUTPUT_DIR / "protocol_knowledge.jsonl", args.batch_size, args.model, args.workers
    )

    ts_done = run_generator(
        client, "Troubleshooting", TROUBLESHOOTING_GENERATION_PROMPT, ts_themes,
        args.troubleshoot_count, OUTPUT_DIR / "troubleshooting.jsonl", args.batch_size, args.model, args.workers
    )

    elapsed = time.time() - t0
    total_done = kpi_done + proto_done + ts_done

    print(f"\n{'='*60}")
    print(f"📊 GENERATION COMPLETE")
    print(f"   KPI/RCA:          {kpi_done}")
    print(f"   Protocol:         {proto_done}")
    print(f"   Troubleshooting:  {ts_done}")
    print(f"   Total:            {total_done}")
    print(f"   Time:             {elapsed/60:.1f} minutes")
    print(f"   Output:           {OUTPUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
