"""
Step 3: Prepare training data for fine-tuning Llama 3.1 8B
- Convert 3GPP documents into instruction-response pairs
- Generate synthetic NOC incident data
- Create intent-to-config (TeleYAML) training pairs
- Format everything as Llama 3.1 chat template
"""

from pathlib import Path
import json
import random
import re
from typing import List, Dict

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw" / "tspec_llm"
OUTPUT_DIR = DATA_DIR / "processed"
SYNTHETIC_DIR = DATA_DIR / "synthetic"


# =============================================================================
# 1. Extract Q&A pairs from 3GPP documents
# =============================================================================

def extract_sections_from_markdown(filepath: Path) -> List[Dict[str, str]]:
    """Extract headed sections from a 3GPP markdown document."""
    sections = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return sections

    # Split by headers (##, ###, ####)
    parts = re.split(r"\n(#{2,4}\s+.+)\n", content)

    current_title = ""
    for i, part in enumerate(parts):
        if re.match(r"#{2,4}\s+", part):
            current_title = part.strip("# \n")
        elif current_title and len(part.strip()) > 100:
            sections.append({
                "title": current_title,
                "content": part.strip()[:2000],  # Cap at 2000 chars
                "source": filepath.name,
            })

    return sections


def create_3gpp_qa_pairs(sections: List[Dict]) -> List[Dict]:
    """Convert document sections into instruction-response pairs."""
    qa_pairs = []

    question_templates = [
        "Explain the concept of {title} as defined in 3GPP specifications.",
        "What does the 3GPP standard say about {title}?",
        "Describe {title} in the context of telecom networks.",
        "As a network engineer, I need to understand {title}. Can you explain?",
        "What is {title} and how does it work in 5G/LTE networks?",
        "Summarize the 3GPP specification for {title}.",
    ]

    for section in sections:
        if len(section["content"].split()) < 30:
            continue  # Skip very short sections

        template = random.choice(question_templates)
        question = template.format(title=section["title"])

        qa_pairs.append({
            "instruction": question,
            "response": section["content"],
            "source": section["source"],
            "category": "3gpp_knowledge",
        })

    return qa_pairs


# =============================================================================
# 2. Generate synthetic NOC incident data
# =============================================================================

# Templates for realistic NOC scenarios
NOC_SCENARIOS = [
    {
        "alarm": "High CPU utilization on eNodeB {site_id} — CPU at {cpu}%",
        "diagnosis": "The eNodeB at site {site_id} is experiencing high CPU load ({cpu}%). "
                     "This is commonly caused by: 1) Excessive handover processing due to "
                     "parameter misconfiguration, 2) Software bug in the current firmware version, "
                     "3) Abnormal traffic pattern (possible signaling storm). "
                     "Recommended checks: Review handover statistics, check connected UE count, "
                     "verify firmware version against known issues.",
        "resolution": "1. Check current connected UEs: if > {ue_threshold}, consider load balancing\n"
                      "2. Review handover success rate: if < 95%, adjust HO parameters\n"
                      "3. If firmware is below v{fw_version}, schedule upgrade\n"
                      "4. Monitor for 30 minutes after adjustment\n"
                      "5. If persists, escalate to L2 with RAN trace data",
        "severity": "Major",
        "domain": "RAN",
    },
    {
        "alarm": "S1 link failure between eNodeB {site_id} and MME {mme_id}",
        "diagnosis": "S1 interface connectivity lost between eNodeB {site_id} and MME {mme_id}. "
                     "Impact: UEs cannot perform initial attach or handover via this MME. "
                     "If redundant MME exists, traffic should failover. "
                     "Root causes: 1) Transport network issue (VLAN/IP routing), "
                     "2) MME overload or process crash, 3) SCTP association timeout, "
                     "4) Firewall rule change blocking SCTP port 36412.",
        "resolution": "1. Verify transport connectivity: ping MME IP from eNodeB\n"
                      "2. Check SCTP association status on both ends\n"
                      "3. Verify no recent firewall changes on port 36412\n"
                      "4. Check MME process status and capacity\n"
                      "5. If transport OK, restart SCTP association\n"
                      "6. Escalate to transport team if ping fails",
        "severity": "Critical",
        "domain": "Core",
    },
    {
        "alarm": "Throughput degradation on cell {cell_id} — DL throughput dropped {drop}%",
        "diagnosis": "Downlink throughput on cell {cell_id} has dropped by {drop}% compared to "
                     "the baseline. Possible causes: 1) Increased interference from neighboring "
                     "cells, 2) Hardware degradation (PA/TRX), 3) Parameter change (scheduler, "
                     "power settings), 4) New physical obstruction affecting RF propagation, "
                     "5) Increased user load without capacity expansion.",
        "resolution": "1. Check RSSI/SINR trends on affected cell\n"
                      "2. Compare PRB utilization — if >80%, capacity issue\n"
                      "3. Review recent CM changes in the last 24h\n"
                      "4. Run RF scan for interference detection\n"
                      "5. If hardware suspected, check VSWR and PA alarms\n"
                      "6. Consider temporary tilt/power adjustment",
        "severity": "Major",
        "domain": "RAN",
    },
    {
        "alarm": "VoLTE call setup failure rate exceeds {threshold}% on {region}",
        "diagnosis": "VoLTE call setup success rate has dropped below acceptable threshold in "
                     "{region}. Current failure rate: {threshold}%. "
                     "Analysis of failure causes: 1) IMS registration failures (check P-CSCF), "
                     "2) Bearer setup failures (dedicated EPS bearer for QCI=1), "
                     "3) DNS resolution issues for IMS domain, "
                     "4) Certificate expiry on SBC/P-CSCF.",
        "resolution": "1. Check IMS registration success rate\n"
                      "2. Verify dedicated bearer setup (QCI=1) success rate\n"
                      "3. Test DNS resolution for IMS APN\n"
                      "4. Check SBC and P-CSCF certificate validity\n"
                      "5. Review SIP signaling traces for error codes\n"
                      "6. If 403/503 errors, check HSS subscription data",
        "severity": "Critical",
        "domain": "IMS/VoLTE",
    },
    {
        "alarm": "Packet loss rate exceeds {loss}% on backhaul link to site {site_id}",
        "diagnosis": "Backhaul link to site {site_id} showing {loss}% packet loss. "
                     "This affects all services on the site including voice and data. "
                     "Potential causes: 1) Microwave link degradation (rain fade, alignment), "
                     "2) Fiber cut or degradation, 3) Router/switch port errors (CRC, frame), "
                     "4) QoS misconfiguration causing drops under load, "
                     "5) MTU mismatch causing fragmentation.",
        "resolution": "1. Check backhaul link type (MW/Fiber/Ethernet)\n"
                      "2. For microwave: check RSL, SNR, and modulation level\n"
                      "3. For fiber: check optical power levels (Tx/Rx)\n"
                      "4. Check interface error counters (CRC, drops, overruns)\n"
                      "5. Verify MTU settings end-to-end\n"
                      "6. Run iperf/traceroute to isolate hop with loss\n"
                      "7. If MW rain fade, wait for weather improvement + verify ATPC",
        "severity": "Major",
        "domain": "Transport",
    },
]


def generate_noc_training_data(n_samples: int = 5000) -> List[Dict]:
    """Generate synthetic NOC incident training data."""
    training_data = []

    for _ in range(n_samples):
        scenario = random.choice(NOC_SCENARIOS)

        # Fill in random values
        params = {
            "site_id": f"ENB-{random.randint(1000, 9999)}",
            "cell_id": f"CELL-{random.randint(10000, 99999)}",
            "mme_id": f"MME-{random.randint(1, 8):02d}",
            "cpu": random.randint(85, 99),
            "ue_threshold": random.randint(200, 500),
            "fw_version": f"{random.randint(18, 23)}.{random.randint(0, 9)}",
            "drop": random.randint(20, 60),
            "threshold": random.randint(5, 25),
            "region": random.choice(["North", "South", "East", "West", "Central"]),
            "loss": round(random.uniform(1.5, 10.0), 1),
        }

        alarm = scenario["alarm"].format(**params)
        diagnosis = scenario["diagnosis"].format(**params)
        resolution = scenario["resolution"].format(**params)

        # Create different instruction formats
        instruction_type = random.choice(["diagnose", "resolve", "full"])

        if instruction_type == "diagnose":
            training_data.append({
                "instruction": f"I'm seeing this alarm in the NOC: '{alarm}'. "
                              f"What could be causing this?",
                "response": diagnosis,
                "category": "noc_diagnosis",
                "severity": scenario["severity"],
                "domain": scenario["domain"],
            })
        elif instruction_type == "resolve":
            training_data.append({
                "instruction": f"Alarm: '{alarm}'\nDiagnosis: {diagnosis}\n\n"
                              f"What are the resolution steps?",
                "response": resolution,
                "category": "noc_resolution",
                "severity": scenario["severity"],
                "domain": scenario["domain"],
            })
        else:
            training_data.append({
                "instruction": f"NOC Alert: '{alarm}'\n\n"
                              f"Please provide full incident analysis and resolution steps.",
                "response": f"**Diagnosis:**\n{diagnosis}\n\n**Resolution Steps:**\n{resolution}",
                "category": "noc_full",
                "severity": scenario["severity"],
                "domain": scenario["domain"],
            })

    return training_data


# =============================================================================
# 3. Generate intent-to-config (TeleYAML) training data
# =============================================================================

INTENT_CONFIG_PAIRS = [
    {
        "intent": "Create a network slice for autonomous vehicles requiring ultra-low latency",
        "config": """network_slice:
  name: autonomous-vehicle-slice
  sst: 2  # URLLC
  sd: "0x000001"
  qos_profile:
    5qi: 1
    priority_level: 1
    packet_delay_budget_ms: 10
    packet_error_rate: 1e-6
  resource_allocation:
    guaranteed_bitrate_dl: 50Mbps
    guaranteed_bitrate_ul: 25Mbps
    max_data_burst: 4096bytes
  isolation: hard
  nssai:
    - sst: 2
      sd: "0x000001"
""",
    },
    {
        "intent": "Configure a 5G cell with 100MHz bandwidth on n78 band with 4x4 MIMO",
        "config": """cell_config:
  cell_id: 1
  nr_band: n78
  duplex_mode: TDD
  channel_bandwidth_mhz: 100
  subcarrier_spacing_khz: 30
  scs_specific_carrier:
    offset_to_carrier: 0
    subcarrier_spacing: kHz30
    carrier_bandwidth_prbs: 273
  mimo:
    antenna_ports: 4
    layers_dl: 4
    layers_ul: 2
    transmission_scheme: codebook
  tdd_pattern:
    dl_slots: 7
    ul_slots: 2
    flexible_slots: 1
    period_ms: 5
  power:
    max_transmit_power_dbm: 49
    reference_signal_power_dbm: 15
""",
    },
    {
        "intent": "Set up QoS policy for VoNR with guaranteed voice quality",
        "config": """qos_policy:
  name: vonr-voice-policy
  qos_flows:
    - qfi: 1
      5qi: 1
      arp:
        priority_level: 1
        preemption_capability: may_preempt
        preemption_vulnerability: not_preemptable
      gbr:
        dl: 128kbps
        ul: 128kbps
      mbr:
        dl: 256kbps
        ul: 256kbps
      packet_delay_budget_ms: 100
      packet_error_rate: 1e-2
      averaging_window_ms: 2000
  reflective_qos: false
  notification_control: requested
""",
    },
    {
        "intent": "Configure inter-frequency handover from n78 to n1 with A2-A5 event triggers",
        "config": """handover_config:
  source_cell:
    nr_band: n78
    frequency_mhz: 3500
  target_cell:
    nr_band: n1
    frequency_mhz: 2100
  measurement_config:
    gap_config:
      gap_offset: 0
      mgl: ms6
      mgrp: ms40
    measurement_objects:
      - mo_id: 1
        nr_arfcn: 431000  # n78
      - mo_id: 2
        nr_arfcn: 422000  # n1
    report_configs:
      - report_id: 1
        event: A2
        threshold_rsrp: -110
        hysteresis_db: 2
        time_to_trigger_ms: 640
      - report_id: 2
        event: A5
        threshold1_rsrp: -100  # serving below this
        threshold2_rsrp: -90   # neighbor above this
        hysteresis_db: 2
        time_to_trigger_ms: 320
  execution:
    t304_ms: 200
    drx_config_target: short_cycle
""",
    },
    {
        "intent": "Enable carrier aggregation combining n78 (primary) and n1 (secondary) for increased throughput",
        "config": """carrier_aggregation:
  mode: inter_band_ca
  pcell:
    nr_band: n78
    channel_bandwidth_mhz: 100
    subcarrier_spacing_khz: 30
    serving_cell_index: 0
  scells:
    - nr_band: n1
      channel_bandwidth_mhz: 20
      subcarrier_spacing_khz: 15
      serving_cell_index: 1
      activation: deactivation_timer
      scell_deactivation_timer_ms: 2560
  cross_carrier_scheduling: false
  pdcp_config:
    duplication: false
    split_bearer: true
    primary_path: pcell
""",
    },
]


def generate_intent_config_data(n_samples: int = 2000) -> List[Dict]:
    """Generate intent-to-configuration training pairs."""
    training_data = []

    instruction_templates = [
        "Convert this network intent to configuration: {intent}",
        "As a network engineer, I need to: {intent}\nGenerate the YAML configuration.",
        "Network intent: {intent}\n\nProvide the corresponding network configuration in YAML format.",
        "Generate 5G network configuration for the following requirement: {intent}",
    ]

    for _ in range(n_samples):
        pair = random.choice(INTENT_CONFIG_PAIRS)
        template = random.choice(instruction_templates)

        training_data.append({
            "instruction": template.format(intent=pair["intent"]),
            "response": pair["config"].strip(),
            "category": "intent_to_config",
        })

    return training_data


# =============================================================================
# 4. Format for Llama 3.1 chat template
# =============================================================================

SYSTEM_PROMPT = (
    "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
    "You have deep knowledge of 3GPP standards, 5G/LTE network operations, "
    "RAN optimization, core network, transport, and IMS/VoLTE. "
    "You assist network engineers with diagnostics, configuration, "
    "troubleshooting, and standards interpretation."
)


def format_as_llama_chat(examples: List[Dict]) -> List[Dict]:
    """Format training data as Llama 3.1 chat conversations."""
    formatted = []

    for ex in examples:
        conversation = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": ex["instruction"]},
                {"role": "assistant", "content": ex["response"]},
            ],
            "category": ex.get("category", "general"),
        }
        formatted.append(conversation)

    return formatted


# =============================================================================
# Main
# =============================================================================

def main():
    print("TELCO SLM - Phase 1: Training Data Preparation")
    print("=" * 60)

    all_data = []

    # 1. Extract from 3GPP docs (if downloaded)
    if RAW_DIR.exists():
        print("\n[1/3] Extracting Q&A pairs from 3GPP documents...")
        md_files = list(RAW_DIR.rglob("*.md"))
        print(f"  Found {len(md_files)} markdown files")

        all_sections = []
        for f in md_files[:500]:  # Process first 500 files initially
            all_sections.extend(extract_sections_from_markdown(f))

        print(f"  Extracted {len(all_sections)} sections")
        qa_pairs = create_3gpp_qa_pairs(all_sections)
        print(f"  Created {len(qa_pairs)} Q&A pairs")
        all_data.extend(qa_pairs)
    else:
        print("\n[1/3] 3GPP data not found — skipping (run 01_download_tspec.py first)")

    # 2. Generate synthetic NOC data
    print("\n[2/3] Generating synthetic NOC incident data...")
    noc_data = generate_noc_training_data(n_samples=5000)
    print(f"  Generated {len(noc_data)} NOC training examples")
    all_data.extend(noc_data)

    # 3. Generate intent-to-config data
    print("\n[3/3] Generating intent-to-config (TeleYAML) data...")
    config_data = generate_intent_config_data(n_samples=2000)
    print(f"  Generated {len(config_data)} config training examples")
    all_data.extend(config_data)

    # Format for Llama 3.1
    print(f"\nTotal training examples: {len(all_data)}")
    formatted = format_as_llama_chat(all_data)

    # Shuffle and split
    random.shuffle(formatted)
    split_idx = int(len(formatted) * 0.9)
    train_data = formatted[:split_idx]
    val_data = formatted[split_idx:]

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    train_path = OUTPUT_DIR / "train.jsonl"
    val_path = OUTPUT_DIR / "val.jsonl"

    for path, data in [(train_path, train_data), (val_path, val_data)]:
        with open(path, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    print(f"\nSaved:")
    print(f"  Training: {train_path} ({len(train_data)} examples)")
    print(f"  Validation: {val_path} ({len(val_data)} examples)")

    # Stats
    print(f"\nCategory breakdown:")
    from collections import Counter
    cats = Counter(d["category"] for d in formatted)
    for cat, count in cats.most_common():
        print(f"  {cat}: {count}")

    print("\n" + "=" * 60)
    print("Phase 1 Complete! Next: Run Phase 2 (fine-tuning)")
    print("  python scripts/training/train_qlora.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
