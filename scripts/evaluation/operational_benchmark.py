"""
Step 4: Telco Operational Benchmark
- 100 questions across 5 categories testing what our system should actually be good at
- Not academic/research questions (that's TeleQnA)
- Focus: incident diagnosis, config generation, KPI analysis, protocol knowledge, routing accuracy

Usage:
  python scripts/evaluation/operational_benchmark.py
  python scripts/evaluation/operational_benchmark.py --model v3    # Test fine-tuned 1.5B
  python scripts/evaluation/operational_benchmark.py --model 7b    # Test base 7B via Ollama
  python scripts/evaluation/operational_benchmark.py --agents       # Test full agent system
"""

import json
import sys
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# =============================================================================
# BENCHMARK QUESTIONS — 100 questions across 5 categories
# =============================================================================

BENCHMARK = [
    # =========================================================================
    # CATEGORY 1: INCIDENT DIAGNOSIS (30 questions)
    # Tests: Can the model correctly identify domain, severity, root causes?
    # =========================================================================

    # RAN incidents (10)
    {
        "id": "INC-RAN-01",
        "category": "incident",
        "domain": "RAN",
        "question": "eNodeB ENB-3456 CPU utilization at 97%. Connected UEs: 450. What is the likely cause and resolution?",
        "expected_domain": "RAN",
        "expected_severity": "Critical",
        "must_contain": ["CPU", "handover", "connected UE", "load balancing"],
        "must_not_contain": ["WAP", "billing", "charging"],
    },
    {
        "id": "INC-RAN-02",
        "category": "incident",
        "domain": "RAN",
        "question": "RACH failure rate jumped from 2% to 18% on cell CELL-78901 in the last hour. No recent config changes.",
        "expected_domain": "RAN",
        "expected_severity": "Major",
        "must_contain": ["PRACH", "interference", "preamble"],
        "must_not_contain": ["WAP", "VoLTE", "billing"],
    },
    {
        "id": "INC-RAN-03",
        "category": "incident",
        "domain": "RAN",
        "question": "DL throughput dropped 40% on cell CELL-23456. PRB utilization is at 45%, so it's not congestion.",
        "expected_domain": "RAN",
        "expected_severity": "Major",
        "must_contain": ["SINR", "interference", "CQI"],
        "must_not_contain": ["congestion", "PRB overload"],
    },
    {
        "id": "INC-RAN-04",
        "category": "incident",
        "domain": "RAN",
        "question": "Handover success rate between CELL-100 and CELL-200 dropped from 98% to 82%. What should I investigate?",
        "expected_domain": "RAN",
        "expected_severity": "Major",
        "must_contain": ["handover", "A3", "neighbor"],
        "must_not_contain": ["WAP", "billing"],
    },
    {
        "id": "INC-RAN-05",
        "category": "incident",
        "domain": "RAN",
        "question": "VSWR alarm on sector 2 of site ENB-5678. Return loss is 8dB instead of normal 25dB.",
        "expected_domain": "RAN",
        "expected_severity": "Critical",
        "must_contain": ["VSWR", "connector", "feeder", "antenna"],
        "must_not_contain": ["software", "configuration"],
    },
    {
        "id": "INC-RAN-06",
        "category": "incident",
        "domain": "RAN",
        "question": "PCI collision detected. Both CELL-300 and CELL-400 are using PCI 127 and they are neighbors.",
        "expected_domain": "RAN",
        "expected_severity": "Major",
        "must_contain": ["PCI", "collision", "neighbor"],
        "must_not_contain": ["WAP", "transport"],
    },
    {
        "id": "INC-RAN-07",
        "category": "incident",
        "domain": "RAN",
        "question": "Cell CELL-500 is completely out of service. BBU is not responding to OAM commands.",
        "expected_domain": "RAN",
        "expected_severity": "Critical",
        "must_contain": ["BBU", "power", "hardware"],
        "must_not_contain": ["billing", "charging"],
    },
    {
        "id": "INC-RAN-08",
        "category": "incident",
        "domain": "RAN",
        "question": "RRC setup success rate is only 85% on gNB GNB-100. What KPIs should I check first?",
        "expected_domain": "RAN",
        "expected_severity": "Major",
        "must_contain": ["RRC", "PDCCH", "RACH"],
        "must_not_contain": ["WAP", "billing"],
    },
    {
        "id": "INC-RAN-09",
        "category": "incident",
        "domain": "RAN",
        "question": "DL PRB utilization is 92% on CELL-600 during busy hour. Users complain of slow data.",
        "expected_domain": "RAN",
        "expected_severity": "Major",
        "must_contain": ["PRB", "congestion", "capacity", "load balancing"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "INC-RAN-10",
        "category": "incident",
        "domain": "RAN",
        "question": "High PDCP packet loss (3.5%) detected on CELL-700. Radio conditions seem normal (SINR > 10dB).",
        "expected_domain": "RAN",
        "expected_severity": "Major",
        "must_contain": ["PDCP", "backhaul", "transport"],
        "must_not_contain": ["WAP"],
    },

    # Core incidents (8)
    {
        "id": "INC-CORE-01",
        "category": "incident",
        "domain": "Core",
        "question": "S1 link failure between eNodeB ENB-8000 and MME MME-02. SCTP association is down.",
        "expected_domain": "Core",
        "expected_severity": "Critical",
        "must_contain": ["S1", "SCTP", "MME", "transport"],
        "must_not_contain": ["WAP", "RACH"],
    },
    {
        "id": "INC-CORE-02",
        "category": "incident",
        "domain": "Core",
        "question": "AMF registration failure rate is 15% on AMF-03. Users can't attach to 5G network.",
        "expected_domain": "Core",
        "expected_severity": "Critical",
        "must_contain": ["AMF", "registration", "AUSF", "UDM"],
        "must_not_contain": ["WAP", "RACH"],
    },
    {
        "id": "INC-CORE-03",
        "category": "incident",
        "domain": "Core",
        "question": "PDU session establishment failure at 20% on SMF-01. IP pool utilization is at 95%.",
        "expected_domain": "Core",
        "expected_severity": "Critical",
        "must_contain": ["PDU", "SMF", "IP pool", "UPF"],
        "must_not_contain": ["WAP", "RACH"],
    },
    {
        "id": "INC-CORE-04",
        "category": "incident",
        "domain": "Core",
        "question": "GTP-U path failure between SGW-01 and PGW-02. Echo requests are timing out.",
        "expected_domain": "Core",
        "expected_severity": "Critical",
        "must_contain": ["GTP", "tunnel", "echo"],
        "must_not_contain": ["WAP", "RACH"],
    },
    {
        "id": "INC-CORE-05",
        "category": "incident",
        "domain": "Core",
        "question": "NRF is not responding to NF discovery requests. Multiple NFs can't find each other.",
        "expected_domain": "Core",
        "expected_severity": "Critical",
        "must_contain": ["NRF", "discovery", "NF"],
        "must_not_contain": ["WAP", "RACH"],
    },
    {
        "id": "INC-CORE-06",
        "category": "incident",
        "domain": "Core",
        "question": "HSS replication lag between primary and standby is 3 seconds and increasing.",
        "expected_domain": "Core",
        "expected_severity": "Major",
        "must_contain": ["HSS", "replication", "failover"],
        "must_not_contain": ["WAP", "RACH"],
    },
    {
        "id": "INC-CORE-07",
        "category": "incident",
        "domain": "Core",
        "question": "Diameter Gx connection lost between PCRF-01 and PGW-01. Port 3868 is unreachable.",
        "expected_domain": "Core",
        "expected_severity": "Critical",
        "must_contain": ["Diameter", "PCRF", "Gx"],
        "must_not_contain": ["WAP", "RACH"],
    },
    {
        "id": "INC-CORE-08",
        "category": "incident",
        "domain": "Core",
        "question": "NSSF is rejecting slice selection requests for SST=1 in tracking area TAC-5000.",
        "expected_domain": "Core",
        "expected_severity": "Critical",
        "must_contain": ["NSSF", "slice", "S-NSSAI"],
        "must_not_contain": ["WAP", "RACH"],
    },

    # Transport incidents (6)
    {
        "id": "INC-TRANS-01",
        "category": "incident",
        "domain": "Transport",
        "question": "Packet loss of 4% detected on backhaul link to site ENB-9000. Link is microwave.",
        "expected_domain": "Transport",
        "expected_severity": "Major",
        "must_contain": ["microwave", "RSL", "rain fade"],
        "must_not_contain": ["WAP", "VoLTE"],
    },
    {
        "id": "INC-TRANS-02",
        "category": "incident",
        "domain": "Transport",
        "question": "BGP peer between PE-NYC-01 and PE-LAX-02 is flapping. Goes down and up every 5 minutes.",
        "expected_domain": "Transport",
        "expected_severity": "Critical",
        "must_contain": ["BGP", "peer", "hold timer"],
        "must_not_contain": ["WAP", "VoLTE"],
    },
    {
        "id": "INC-TRANS-03",
        "category": "incident",
        "domain": "Transport",
        "question": "MPLS LSP for VPN-ENTERPRISE-500 is down. LDP session between PE-01 and PE-02 is lost.",
        "expected_domain": "Transport",
        "expected_severity": "Critical",
        "must_contain": ["MPLS", "LDP", "LSP"],
        "must_not_contain": ["WAP", "VoLTE"],
    },
    {
        "id": "INC-TRANS-04",
        "category": "incident",
        "domain": "Transport",
        "question": "PTP synchronization lost at site ENB-1100. GNSS antenna shows no satellite lock.",
        "expected_domain": "Transport",
        "expected_severity": "Critical",
        "must_contain": ["PTP", "synchronization", "GNSS"],
        "must_not_contain": ["WAP", "VoLTE"],
    },
    {
        "id": "INC-TRANS-05",
        "category": "incident",
        "domain": "Transport",
        "question": "DWDM optical power on lambda 3 dropped by 6dB. OSNR is degrading.",
        "expected_domain": "Transport",
        "expected_severity": "Major",
        "must_contain": ["optical", "OSNR", "amplifier"],
        "must_not_contain": ["WAP", "VoLTE"],
    },
    {
        "id": "INC-TRANS-06",
        "category": "incident",
        "domain": "Transport",
        "question": "QoS policy on the S1 interface is dropping high-priority voice packets. DSCP marking seems wrong.",
        "expected_domain": "Transport",
        "expected_severity": "Major",
        "must_contain": ["QoS", "DSCP", "priority"],
        "must_not_contain": ["WAP"],
    },

    # IMS/VoLTE incidents (6)
    {
        "id": "INC-IMS-01",
        "category": "incident",
        "domain": "IMS",
        "question": "VoLTE call setup failure rate is 12% in the South region. Most failures are SIP 503 from S-CSCF.",
        "expected_domain": "IMS",
        "expected_severity": "Critical",
        "must_contain": ["IMS", "S-CSCF", "SIP", "503"],
        "must_not_contain": ["WAP", "WAP Gateway", "voice-to-video"],
    },
    {
        "id": "INC-IMS-02",
        "category": "incident",
        "domain": "IMS",
        "question": "One-way audio reported on VoLTE calls. Caller can hear callee but callee hears nothing.",
        "expected_domain": "IMS",
        "expected_severity": "Major",
        "must_contain": ["RTP", "SDP", "NAT", "media"],
        "must_not_contain": ["WAP", "RACH"],
    },
    {
        "id": "INC-IMS-03",
        "category": "incident",
        "domain": "IMS",
        "question": "SRVCC handover from VoLTE to 3G is failing. Sv interface between MME and MSC is showing errors.",
        "expected_domain": "IMS",
        "expected_severity": "Critical",
        "must_contain": ["SRVCC", "Sv", "MSC"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "INC-IMS-04",
        "category": "incident",
        "domain": "IMS",
        "question": "Emergency calls (911) over VoLTE are failing. Normal VoLTE calls work fine.",
        "expected_domain": "IMS",
        "expected_severity": "Critical",
        "must_contain": ["emergency", "E-CSCF", "PSAP"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "INC-IMS-05",
        "category": "incident",
        "domain": "IMS",
        "question": "IMS registration success rate dropped to 92%. P-CSCF is returning 403 Forbidden.",
        "expected_domain": "IMS",
        "expected_severity": "Critical",
        "must_contain": ["IMS", "registration", "P-CSCF", "403"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "INC-IMS-06",
        "category": "incident",
        "domain": "IMS",
        "question": "SBC is overwhelmed after a network recovery. 50,000 simultaneous IMS re-registrations hitting it.",
        "expected_domain": "IMS",
        "expected_severity": "Critical",
        "must_contain": ["SBC", "registration", "rate limiting"],
        "must_not_contain": ["WAP"],
    },

    # =========================================================================
    # CATEGORY 2: CONFIG GENERATION (20 questions)
    # Tests: Can the model generate valid YAML for network configurations?
    # =========================================================================
    {
        "id": "CFG-01",
        "category": "config",
        "question": "Create a network slice for URLLC autonomous vehicles with 10ms latency budget",
        "must_contain": ["sst", "URLLC", "latency", "packet_delay"],
        "must_not_contain": [],
        "must_be_yaml": True,
    },
    {
        "id": "CFG-02",
        "category": "config",
        "question": "Configure QoS policy for VoNR with guaranteed 128kbps voice bearer",
        "must_contain": ["5qi", "gbr", "128"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-03",
        "category": "config",
        "question": "Set up carrier aggregation with n78 as primary cell and n1 as secondary",
        "must_contain": ["n78", "n1", "pcell", "scell"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-04",
        "category": "config",
        "question": "Configure a 5G NR cell on n78 band with 100MHz bandwidth and 4x4 MIMO",
        "must_contain": ["n78", "100", "mimo", "4"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-05",
        "category": "config",
        "question": "Set up SON with automatic neighbor relations, mobility load balancing, and MRO",
        "must_contain": ["anr", "mlb", "mro"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-06",
        "category": "config",
        "question": "Configure RAN energy saving with carrier shutdown when PRB utilization below 10%",
        "must_contain": ["energy", "carrier", "shutdown", "prb"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-07",
        "category": "config",
        "question": "Create IoT mMTC network slice with power saving mode and eDRX",
        "must_contain": ["sst", "mMTC", "power_saving", "edrx"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-08",
        "category": "config",
        "question": "Configure IPsec tunnel between eNodeB and security gateway using IKEv2 with AES-256",
        "must_contain": ["ipsec", "ike", "aes", "256"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-09",
        "category": "config",
        "question": "Set up inter-frequency handover from n78 to n1 with A2 and A5 events",
        "must_contain": ["handover", "A2", "A5", "n78", "n1"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-10",
        "category": "config",
        "question": "Configure UPF for edge computing with ULCL traffic steering to local data network",
        "must_contain": ["upf", "ulcl", "local"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-11",
        "category": "config",
        "question": "Set up MOCN RAN sharing between two operators on n78 band with 60/40 resource split",
        "must_contain": ["mocn", "plmn", "60", "40"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-12",
        "category": "config",
        "question": "Configure DRX for low latency with 40ms long DRX cycle and 10ms short DRX",
        "must_contain": ["drx", "40", "10"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-13",
        "category": "config",
        "question": "Set up alarm correlation rules to identify site power failure from multiple alarms",
        "must_contain": ["alarm", "correlation", "power"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-14",
        "category": "config",
        "question": "Configure PM counters for a RAN KPI dashboard with throughput, RRC success, and ERAB drop rate",
        "must_contain": ["throughput", "rrc", "erab"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-15",
        "category": "config",
        "question": "Configure NWDAF for network anomaly detection with real-time data collection",
        "must_contain": ["nwdaf", "anomaly"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-16",
        "category": "config",
        "question": "Set up O-RAN near-RT RIC xApp for intelligent load balancing across cells",
        "must_contain": ["ric", "xapp", "load_balancing"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-17",
        "category": "config",
        "question": "Configure CSFB from LTE to 3G for voice calls with redirection to UARFCN 10713",
        "must_contain": ["csfb", "redirect", "10713"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-18",
        "category": "config",
        "question": "Set up MEC application deployment rules for low-latency video streaming at edge site",
        "must_contain": ["mec", "edge", "video"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-19",
        "category": "config",
        "question": "Configure inter-PLMN 5G roaming with SEPP on N32 interface using TLS",
        "must_contain": ["sepp", "n32", "roaming", "tls"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },
    {
        "id": "CFG-20",
        "category": "config",
        "question": "Set up NF registration in NRF for a new SMF instance with its service profile",
        "must_contain": ["nrf", "smf", "registration"],
        "must_be_yaml": True,
        "must_not_contain": [],
    },

    # =========================================================================
    # CATEGORY 3: KPI ANALYSIS (15 questions)
    # Tests: Can the model interpret KPIs and provide analytical guidance?
    # =========================================================================
    {
        "id": "KPI-01",
        "category": "kpi",
        "question": "ERAB drop rate increased from 0.5% to 2.8% over the past week. How should I investigate?",
        "must_contain": ["radio", "mobility", "transport", "congestion"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-02",
        "category": "kpi",
        "question": "RRC setup success rate is 87% on cell CELL-800. Target is 95%. What's wrong?",
        "must_contain": ["PDCCH", "RACH", "coverage"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-03",
        "category": "kpi",
        "question": "VoLTE MOS score dropped from 3.8 to 3.1. What should I check?",
        "must_contain": ["jitter", "packet loss", "codec"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-04",
        "category": "kpi",
        "question": "Average DL user throughput is 15Mbps on a 20MHz LTE cell. Is this normal?",
        "must_contain": ["spectral efficiency", "PRB", "SINR"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-05",
        "category": "kpi",
        "question": "Handover success rate between two 5G cells is only 88%. How should I analyze this?",
        "must_contain": ["too-late", "too-early", "A3", "TTT"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-06",
        "category": "kpi",
        "question": "Inter-RAT handover from 5G to 4G has 15% failure rate. What's likely causing this?",
        "must_contain": ["measurement", "B1", "coverage"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-07",
        "category": "kpi",
        "question": "Cell CELL-900 shows 95% PRB utilization but only 100 connected users. Is this normal?",
        "must_contain": ["PRB", "throughput", "heavy users"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-08",
        "category": "kpi",
        "question": "Uplink interference level (IoT) increased by 5dB across a cluster of 10 cells. What could cause this?",
        "must_contain": ["interference", "external", "PIM"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-09",
        "category": "kpi",
        "question": "Our network's energy consumption per GB of data is 30% higher than industry average. How to optimize?",
        "must_contain": ["energy", "carrier shutdown", "MIMO", "sleep"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-10",
        "category": "kpi",
        "question": "Attach success rate on MME-01 dropped from 99.5% to 97%. What KPIs should I correlate?",
        "must_contain": ["attach", "authentication", "HSS"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-11",
        "category": "kpi",
        "question": "VoLTE call drop rate is 2% but only in the North region. Other regions are at 0.3%. Why?",
        "must_contain": ["region", "handover", "coverage"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-12",
        "category": "kpi",
        "question": "Paging success rate dropped to 85% on MME-02. What does this indicate?",
        "must_contain": ["paging", "TAU", "tracking area"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-13",
        "category": "kpi",
        "question": "Bearer modification success rate is 90%. What could be causing the 10% failures?",
        "must_contain": ["bearer", "QoS", "resource"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-14",
        "category": "kpi",
        "question": "X2 handover success rate is 99% but S1 handover is only 92%. What does this tell you?",
        "must_contain": ["X2", "S1", "inter-eNB", "MME"],
        "must_not_contain": ["WAP"],
    },
    {
        "id": "KPI-15",
        "category": "kpi",
        "question": "Our 5G SA network shows 5% registration rejection rate. Most rejections are cause code #5. What does this mean?",
        "must_contain": ["registration", "reject", "PLMN"],
        "must_not_contain": ["WAP"],
    },

    # =========================================================================
    # CATEGORY 4: PROTOCOL KNOWLEDGE (20 questions)
    # Tests: Does the model understand telecom protocols correctly?
    # =========================================================================
    {
        "id": "PROTO-01",
        "category": "knowledge",
        "question": "What is 5QI and what are the standard 5QI values for voice, video, and best effort?",
        "must_contain": ["5QI", "QoS", "voice", "GBR"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-02",
        "category": "knowledge",
        "question": "Explain the N4 interface between SMF and UPF. What protocol does it use?",
        "must_contain": ["PFCP", "SMF", "UPF", "forwarding"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-03",
        "category": "knowledge",
        "question": "What is the difference between NSA Option 3x and SA Option 2 in 5G deployment?",
        "must_contain": ["EPC", "5GC", "control plane", "master"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-04",
        "category": "knowledge",
        "question": "How does the 5G NR random access procedure (RACH) work? Describe the 4 steps.",
        "must_contain": ["preamble", "RAR", "Msg3", "contention"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-05",
        "category": "knowledge",
        "question": "What is network slicing? How is S-NSSAI structured?",
        "must_contain": ["SST", "SD", "slice"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-06",
        "category": "knowledge",
        "question": "Explain the role of AMF, SMF, and UPF in 5G core network.",
        "must_contain": ["AMF", "mobility", "SMF", "session", "UPF", "user plane"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-07",
        "category": "knowledge",
        "question": "What is CUPS and why is it important in 5G architecture?",
        "must_contain": ["control", "user plane", "separation"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-08",
        "category": "knowledge",
        "question": "How does HARQ work in LTE/5G NR? What is the difference between synchronous and asynchronous HARQ?",
        "must_contain": ["HARQ", "retransmission", "ACK", "NACK"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-09",
        "category": "knowledge",
        "question": "What is the CU-DU split in 5G RAN? Which protocol layers go where?",
        "must_contain": ["CU", "DU", "RRC", "PDCP", "RLC", "MAC"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-10",
        "category": "knowledge",
        "question": "Explain the Tracking Area Update (TAU) procedure in LTE.",
        "must_contain": ["TAU", "tracking area", "MME", "idle"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-11",
        "category": "knowledge",
        "question": "What is SSB in 5G NR and what does it contain?",
        "must_contain": ["PSS", "SSS", "PBCH", "synchronization"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-12",
        "category": "knowledge",
        "question": "How does carrier aggregation work in LTE/NR? What is the difference between inter-band and intra-band CA?",
        "must_contain": ["component carrier", "PCell", "SCell"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-13",
        "category": "knowledge",
        "question": "What is MIMO and how does massive MIMO differ from regular MIMO?",
        "must_contain": ["antenna", "beamforming", "spatial"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-14",
        "category": "knowledge",
        "question": "Explain the IMS architecture for VoLTE. What are P-CSCF, I-CSCF, and S-CSCF?",
        "must_contain": ["P-CSCF", "I-CSCF", "S-CSCF", "SIP"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-15",
        "category": "knowledge",
        "question": "What is the difference between GBR and Non-GBR bearers in LTE?",
        "must_contain": ["GBR", "guaranteed", "bit rate"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-16",
        "category": "knowledge",
        "question": "How does NRF work in 5G SBA? What is NF discovery?",
        "must_contain": ["NRF", "service", "registration", "discovery"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-17",
        "category": "knowledge",
        "question": "What subcarrier spacings are supported in 5G NR and when is each used?",
        "must_contain": ["15", "30", "60", "120", "kHz"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-18",
        "category": "knowledge",
        "question": "Explain the difference between FDD and TDD. Why is TDD preferred for 5G NR in FR1?",
        "must_contain": ["FDD", "TDD", "uplink", "downlink", "spectrum"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-19",
        "category": "knowledge",
        "question": "What is O-RAN and how does it differ from traditional RAN?",
        "must_contain": ["open", "interface", "vendor", "RIC"],
        "must_not_contain": [],
    },
    {
        "id": "PROTO-20",
        "category": "knowledge",
        "question": "Explain MEC (Multi-access Edge Computing) and its role in 5G.",
        "must_contain": ["edge", "latency", "local"],
        "must_not_contain": [],
    },

    # =========================================================================
    # CATEGORY 5: ROUTING ACCURACY (15 questions)
    # Tests: Does the Supervisor correctly classify query types?
    # =========================================================================
    {
        "id": "ROUTE-01",
        "category": "routing",
        "question": "High CPU on eNodeB ENB-1234 at 92%",
        "expected_route": "incident",
    },
    {
        "id": "ROUTE-02",
        "category": "routing",
        "question": "Generate a YAML config for 5G network slicing",
        "expected_route": "config",
    },
    {
        "id": "ROUTE-03",
        "category": "routing",
        "question": "What does 3GPP say about the N4 interface?",
        "expected_route": "knowledge",
    },
    {
        "id": "ROUTE-04",
        "category": "routing",
        "question": "S1 link failure between eNodeB and MME",
        "expected_route": "incident",
    },
    {
        "id": "ROUTE-05",
        "category": "routing",
        "question": "Configure IPsec tunnel for backhaul encryption",
        "expected_route": "config",
    },
    {
        "id": "ROUTE-06",
        "category": "routing",
        "question": "Explain the difference between NSA and SA 5G",
        "expected_route": "knowledge",
    },
    {
        "id": "ROUTE-07",
        "category": "routing",
        "question": "ERAB drop rate is 3%, how to investigate?",
        "expected_route": "incident",
    },
    {
        "id": "ROUTE-08",
        "category": "routing",
        "question": "Set up QoS policy for VoNR",
        "expected_route": "config",
    },
    {
        "id": "ROUTE-09",
        "category": "routing",
        "question": "What is MIMO and how does massive MIMO work?",
        "expected_route": "knowledge",
    },
    {
        "id": "ROUTE-10",
        "category": "routing",
        "question": "VoLTE call setup failure rate is 15%",
        "expected_route": "incident",
    },
    {
        "id": "ROUTE-11",
        "category": "routing",
        "question": "Create network slice for autonomous vehicles",
        "expected_route": "config",
    },
    {
        "id": "ROUTE-12",
        "category": "routing",
        "question": "How does network slicing work in 5G?",
        "expected_route": "knowledge",
    },
    {
        "id": "ROUTE-13",
        "category": "routing",
        "question": "BGP peer is down between our PE routers",
        "expected_route": "incident",
    },
    {
        "id": "ROUTE-14",
        "category": "routing",
        "question": "Configure O-RAN RIC xApp for load balancing",
        "expected_route": "config",
    },
    {
        "id": "ROUTE-15",
        "category": "routing",
        "question": "What is the role of AMF in 5G core?",
        "expected_route": "knowledge",
    },
]


# =============================================================================
# Scoring Functions
# =============================================================================

@dataclass
class QuestionResult:
    id: str
    category: str
    question: str
    answer: str
    score: float  # 0.0 to 1.0
    details: dict = field(default_factory=dict)
    elapsed: float = 0.0


def score_incident(question: dict, answer: str) -> tuple[float, dict]:
    """Score an incident diagnosis response."""
    answer_lower = answer.lower()
    details = {}
    score = 0.0
    max_score = 0.0

    # Check domain (if expected)
    if "expected_domain" in question:
        max_score += 1.0
        domain = question["expected_domain"].lower()
        if domain in answer_lower:
            score += 1.0
            details["domain"] = "correct"
        else:
            details["domain"] = f"wrong (expected {question['expected_domain']})"

    # Check must_contain keywords
    if question.get("must_contain"):
        for kw in question["must_contain"]:
            max_score += 1.0
            if kw.lower() in answer_lower:
                score += 1.0
                details[f"contains_{kw}"] = True
            else:
                details[f"contains_{kw}"] = False

    # Check must_not_contain (penalty)
    if question.get("must_not_contain"):
        for kw in question["must_not_contain"]:
            if kw.lower() in answer_lower:
                score -= 0.5
                details[f"wrongly_contains_{kw}"] = True

    # Check structure (has severity, causes, steps)
    if "severity" in answer_lower or "critical" in answer_lower or "major" in answer_lower:
        max_score += 0.5
        score += 0.5
        details["has_severity"] = True

    if any(word in answer_lower for word in ["cause", "reason", "probable"]):
        max_score += 0.5
        score += 0.5
        details["has_causes"] = True

    if any(word in answer_lower for word in ["resolution", "step", "action", "check"]):
        max_score += 0.5
        score += 0.5
        details["has_resolution"] = True

    return min(score / max(max_score, 1), 1.0), details


def score_config(question: dict, answer: str) -> tuple[float, dict]:
    """Score a config generation response."""
    answer_lower = answer.lower()
    details = {}
    score = 0.0
    max_score = 0.0

    # Check if YAML-like structure
    max_score += 1.0
    if ":" in answer and ("\n" in answer):
        score += 1.0
        details["is_yaml_like"] = True
    else:
        details["is_yaml_like"] = False

    # Check must_contain keywords
    if question.get("must_contain"):
        for kw in question["must_contain"]:
            max_score += 1.0
            if kw.lower() in answer_lower:
                score += 1.0
                details[f"contains_{kw}"] = True
            else:
                details[f"contains_{kw}"] = False

    # Check for repetition (penalty)
    lines = answer.split("\n")
    if len(lines) > 10:
        unique_lines = set(line.strip() for line in lines if line.strip())
        repetition_ratio = len(unique_lines) / len(lines)
        if repetition_ratio < 0.5:
            score -= 1.0
            details["excessive_repetition"] = True

    return min(max(score / max(max_score, 1), 0), 1.0), details


def score_kpi(question: dict, answer: str) -> tuple[float, dict]:
    """Score a KPI analysis response."""
    return score_incident(question, answer)  # Same keyword-based scoring


def score_knowledge(question: dict, answer: str) -> tuple[float, dict]:
    """Score a protocol knowledge response."""
    answer_lower = answer.lower()
    details = {}
    score = 0.0
    max_score = 0.0

    # Check must_contain keywords
    if question.get("must_contain"):
        for kw in question["must_contain"]:
            max_score += 1.0
            if kw.lower() in answer_lower:
                score += 1.0
                details[f"contains_{kw}"] = True
            else:
                details[f"contains_{kw}"] = False

    # Check for table-dumping (penalty)
    if answer.count("|") > 20 or answer.count("+--") > 5:
        score -= 1.0
        details["table_dump"] = True

    # Check for repetition (penalty)
    words = answer_lower.split()
    if len(words) > 50:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:
            score -= 1.0
            details["excessive_repetition"] = True

    return min(max(score / max(max_score, 1), 0), 1.0), details


def score_routing(question: dict, actual_route: str) -> tuple[float, dict]:
    """Score routing accuracy."""
    expected = question.get("expected_route", "")
    correct = actual_route == expected
    return (1.0 if correct else 0.0), {
        "expected": expected,
        "actual": actual_route,
        "correct": correct,
    }


# =============================================================================
# Main evaluation runner
# =============================================================================

def run_benchmark_slm(model_name: str = "v3"):
    """Run benchmark using fine-tuned SLM via MLX."""
    from mlx_lm import load, generate

    adapter = str(PROJECT_ROOT / f"models/telco-slm-{model_name}-mlx/adapter")
    print(f"Loading TelcoGPT {model_name}...")
    model, tokenizer = load("Qwen/Qwen2.5-1.5B-Instruct", adapter_path=adapter)

    system = (
        "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
        "Give practical, structured answers. Never output raw tables."
    )

    results = []
    for q in BENCHMARK:
        if q["category"] == "routing":
            continue  # Routing tests need the agent system

        start = time.time()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": q["question"]},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        answer = generate(model, tokenizer, prompt=text, max_tokens=400, verbose=False)
        elapsed = time.time() - start

        # Score
        if q["category"] == "incident":
            score, details = score_incident(q, answer)
        elif q["category"] == "config":
            score, details = score_config(q, answer)
        elif q["category"] == "kpi":
            score, details = score_kpi(q, answer)
        elif q["category"] == "knowledge":
            score, details = score_knowledge(q, answer)
        else:
            score, details = 0.0, {}

        results.append(QuestionResult(
            id=q["id"], category=q["category"], question=q["question"],
            answer=answer[:500], score=score, details=details, elapsed=elapsed,
        ))

        print(f"  [{q['id']}] {score:.2f} ({elapsed:.1f}s) {q['question'][:60]}...")

    return results


def run_benchmark_ollama(model_name: str = "qwen2.5:7b-instruct"):
    """Run benchmark using Ollama model."""
    import httpx

    system = (
        "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
        "Give practical, structured answers. Never output raw tables."
    )

    results = []
    for q in BENCHMARK:
        if q["category"] == "routing":
            continue

        start = time.time()
        try:
            resp = httpx.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": q["question"]},
                    ],
                    "stream": False,
                    "options": {"num_predict": 400},
                },
                timeout=120,
                verify=False,
            )
            answer = resp.json().get("message", {}).get("content", "")
        except Exception as e:
            answer = f"ERROR: {e}"
        elapsed = time.time() - start

        if q["category"] == "incident":
            score, details = score_incident(q, answer)
        elif q["category"] == "config":
            score, details = score_config(q, answer)
        elif q["category"] == "kpi":
            score, details = score_kpi(q, answer)
        elif q["category"] == "knowledge":
            score, details = score_knowledge(q, answer)
        else:
            score, details = 0.0, {}

        results.append(QuestionResult(
            id=q["id"], category=q["category"], question=q["question"],
            answer=answer[:500], score=score, details=details, elapsed=elapsed,
        ))

        print(f"  [{q['id']}] {score:.2f} ({elapsed:.1f}s) {q['question'][:60]}...")

    return results


def run_benchmark_agents(enable_rag=False):
    """Run benchmark using the full agent system."""
    import os
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    sys.path.insert(0, str(PROJECT_ROOT))
    from agents.telco_agents import AgentOrchestrator

    print(f"Loading agent system... (RAG={'ON' if enable_rag else 'OFF'})")
    orch = AgentOrchestrator(skip_rag=not enable_rag)

    results = []
    for q in BENCHMARK:
        start = time.time()

        if q["category"] == "routing":
            # Only test classification
            classification = orch.supervisor.classify(q["question"])
            elapsed = time.time() - start
            score, details = score_routing(q, classification)
            results.append(QuestionResult(
                id=q["id"], category="routing", question=q["question"],
                answer=classification, score=score, details=details, elapsed=elapsed,
            ))
        else:
            r = orch.run(q["question"])
            elapsed = time.time() - start
            answer = r.answer

            if q["category"] == "incident":
                score, details = score_incident(q, answer)
            elif q["category"] == "config":
                score, details = score_config(q, answer)
            elif q["category"] == "kpi":
                score, details = score_kpi(q, answer)
            elif q["category"] == "knowledge":
                score, details = score_knowledge(q, answer)
            else:
                score, details = 0.0, {}

            details["agent"] = r.agent
            details["routed_category"] = r.category
            results.append(QuestionResult(
                id=q["id"], category=q["category"], question=q["question"],
                answer=answer[:500], score=score, details=details, elapsed=elapsed,
            ))

        print(f"  [{q['id']}] {score:.2f} ({elapsed:.1f}s) {q['question'][:60]}...")

    return results


def print_summary(results: list[QuestionResult], model_name: str):
    """Print benchmark summary."""
    print(f"\n{'='*60}")
    print(f"BENCHMARK RESULTS: {model_name}")
    print(f"{'='*60}")

    # Overall
    total_score = sum(r.score for r in results)
    max_score = len(results)
    print(f"\nOverall: {total_score:.1f}/{max_score} ({100*total_score/max_score:.1f}%)")

    # By category
    categories = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = []
        categories[r.category].append(r)

    print(f"\n{'Category':<20} {'Score':>8} {'Count':>6} {'Avg':>8} {'Avg Time':>10}")
    print(f"{'-'*54}")
    for cat, cat_results in sorted(categories.items()):
        cat_score = sum(r.score for r in cat_results)
        cat_max = len(cat_results)
        avg_score = cat_score / cat_max if cat_max > 0 else 0
        avg_time = sum(r.elapsed for r in cat_results) / cat_max if cat_max > 0 else 0
        print(f"{cat:<20} {cat_score:>6.1f}/{cat_max:<3} {cat_max:>4}   {avg_score:>6.1%}   {avg_time:>8.1f}s")

    # Worst performing questions
    print(f"\n--- Worst 10 Questions ---")
    worst = sorted(results, key=lambda r: r.score)[:10]
    for r in worst:
        print(f"  [{r.id}] {r.score:.2f} — {r.question[:70]}")

    return {
        "model": model_name,
        "overall_score": total_score / max_score,
        "by_category": {
            cat: sum(r.score for r in rs) / len(rs)
            for cat, rs in categories.items()
        },
        "results": [asdict(r) for r in results],
    }


def main():
    parser = argparse.ArgumentParser(description="Telco Operational Benchmark")
    parser.add_argument("--model", choices=["v3", "7b", "7b-ft", "7b-v2", "7b-v3", "7b-v4", "7b-merged", "llama-v1", "llama-v2", "llama-v3-patch", "llama-v3", "llama-v4", "llama-v41", "llama-base", "base", "phi4"], default="v3",
                       help="Model to test: v3 (fine-tuned 1.5B), 7b (Ollama 7B), 7b-ft/v2/v3/v4/merged (fine-tuned Qwen 7B), llama-v1 (Llama 3.1 8B), llama-base (untuned Llama 3.1 8B), base (Ollama 1.5B), phi4 (Microsoft Phi-4 14B)")
    parser.add_argument("--agents", action="store_true",
                       help="Test the full agent system instead of a single model")
    parser.add_argument("--rag", action="store_true",
                       help="Enable RAG retrieval in agent system (use with --agents)")
    parser.add_argument("--limit", type=int, default=0,
                       help="Limit to first N questions (0=all)")
    args = parser.parse_args()

    global BENCHMARK
    if args.limit > 0:
        BENCHMARK = BENCHMARK[:args.limit]

    print(f"Telco Operational Benchmark — {len(BENCHMARK)} questions")
    print(f"{'='*60}")

    if args.agents:
        results = run_benchmark_agents(enable_rag=args.rag)
        label = "Agent System (Fine-tuned + RAG)" if args.rag else "Agent System (Fine-tuned, no RAG)"
        summary = print_summary(results, label)
    elif args.model == "v3":
        results = run_benchmark_slm("v3")
        summary = print_summary(results, "TelcoGPT v3 (fine-tuned 1.5B)")
    elif args.model == "7b":
        results = run_benchmark_ollama("qwen2.5:7b-instruct")
        summary = print_summary(results, "Qwen 2.5 7B (Ollama, no fine-tuning)")
    elif args.model == "7b-ft":
        results = run_benchmark_ollama("telco-7b-ft")
        summary = print_summary(results, "TelcoGPT 7B (fine-tuned v1, 2000 steps)")
    elif args.model == "7b-v2":
        results = run_benchmark_ollama("telco-7b-v2")
        summary = print_summary(results, "TelcoGPT 7B (fine-tuned v2, 1500 steps)")
    elif args.model == "7b-v3":
        results = run_benchmark_ollama("telco-7b-v3")
        summary = print_summary(results, "TelcoGPT 7B (fine-tuned v3, 2145 steps, RunPod A40)")
    elif args.model == "7b-merged":
        results = run_benchmark_ollama("telco-7b-merged")
        summary = print_summary(results, "TelcoGPT 7B (merged v1+v2, 60/40 weight)")
    elif args.model == "7b-v4":
        results = run_benchmark_ollama("telco-7b-v4")
        summary = print_summary(results, "TelcoGPT 7B v4 (66K public datasets, standard HF)")
    elif args.model == "llama-v1":
        results = run_benchmark_ollama("llama-telco-v1")
        summary = print_summary(results, "Llama 3.1 8B (fine-tuned v1, 2137 steps, v1 data)")
    elif args.model == "llama-v2":
        results = run_benchmark_ollama("llama-telco-v2")
        summary = print_summary(results, "Llama 3.1 8B (fine-tuned v2, 2997 steps, v2 49K data)")
    elif args.model == "llama-v3-patch":
        results = run_benchmark_ollama("llama-telco-v3-patch")
        summary = print_summary(results, "Llama 3.1 8B (v3 patch-tune from v2, 484 steps, 7.7K corrective)")
    elif args.model == "llama-v3":
        results = run_benchmark_ollama("llama-telco-v3")
        summary = print_summary(results, "Llama 3.1 8B (v3 full retrain, 3030 steps, 48.5K cleaned+corrective)")
    elif args.model == "llama-v4":
        results = run_benchmark_ollama("llama-telco-v4")
        summary = print_summary(results, "Llama 3.1 8B (v4 patch-tune from v2, 461 steps, 7.4K balanced patch)")
    elif args.model == "llama-v41":
        results = run_benchmark_ollama("llama-telco-v41")
        summary = print_summary(results, "Llama 3.1 8B (v4.1 micro-patch from v4, 162 steps, 1.3K targeted)")
    elif args.model == "llama-base":
        results = run_benchmark_ollama("llama3.1:8b-instruct-q4_K_M")
        summary = print_summary(results, "Llama 3.1 8B Instruct (base, no fine-tuning)")
    elif args.model == "phi4":
        results = run_benchmark_ollama("phi4:14b")
        summary = print_summary(results, "Microsoft Phi-4 14B (base, no fine-tuning)")
    elif args.model == "base":
        results = run_benchmark_ollama("qwen2.5:1.5b-instruct")
        summary = print_summary(results, "Qwen 2.5 1.5B (base, no fine-tuning)")

    # Save results
    suffix = "agents-rag" if (args.agents and args.rag) else ("agents" if args.agents else args.model)
    output_path = PROJECT_ROOT / "models" / f"benchmark_{suffix}.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
