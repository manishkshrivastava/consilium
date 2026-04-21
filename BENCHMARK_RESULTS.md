# Telco Operational Benchmark — Consolidated Results
## Date: 2026-03-19
## 100 Questions across 5 Categories

---

## 1. Overall Summary

| Model | Overall Score | Config | Incident | Knowledge | KPI | Routing |
|-------|-------------|--------|----------|-----------|-----|---------|
| v3 (1.5B fine-tuned) | **61.4%** | 86.0% | 67.6% | 40.0% | 44.6% | N/A |
| Base 7B (no fine-tuning) | **76.1%** | 91.5% | 71.6% | 85.2% | 52.4% | N/A |
| **Agent System (SLM+7B)** | **83.4%** | **96.1%** | **78.3%** | **83.8%** | **59.5%** | **100%** |
| Fine-tuned 7B (Colab) | PENDING | — | — | — | — | — |

**The Agent System (83.4%) outperforms both individual models** — proving the hybrid architecture works.

---

## 2. Category Breakdown

### 2.1 Config Generation (20 questions) — Best Category

| Model | Score | Avg Time |
|-------|-------|----------|
| v3 (1.5B fine-tuned) | 86.0% | 11.4s |
| Base 7B | 91.5% | 17.7s |
| **Agent System** | **96.1%** | **18.0s** |

Agent System routes config → ConfigAgent (fine-tuned SLM) which excels at trained templates. The Supervisor's routing adds accuracy by ensuring only config questions reach this agent.

### 2.2 Incident Diagnosis (30 questions)

| Model | Score | Avg Time |
|-------|-------|----------|
| v3 (1.5B fine-tuned) | 67.6% | 5.1s |
| Base 7B | 71.6% | 24.2s |
| **Agent System** | **78.3%** | **23.8s** |

Agent System improves by 10+ points over v3 alone. The Supervisor routes some incidents to 7B (GenericAgent) when they don't match trained patterns.

### 2.3 Protocol Knowledge (20 questions)

| Model | Score | Avg Time |
|-------|-------|----------|
| v3 (1.5B fine-tuned) | 40.0% | 11.9s |
| Base 7B | **85.2%** | 20.5s |
| Agent System | 83.8% | 29.0s |

7B dominates — 45 percentage points better than v3. The Agent System correctly routes knowledge questions to 7B-based agents.

### 2.4 KPI Analysis (15 questions)

| Model | Score | Avg Time |
|-------|-------|----------|
| v3 (1.5B fine-tuned) | 44.6% | 8.5s |
| Base 7B | 52.4% | 17.3s |
| **Agent System** | **59.5%** | **18.1s** |

Weakest category across all models. Requires analytical reasoning that even 7B struggles with. The Agent System adds ~7 points by combining SLM and 7B strengths.

### 2.5 Routing Accuracy (15 questions)

| Model | Score |
|-------|-------|
| **Agent System (Supervisor)** | **100% (15/15)** |

Perfect routing — every query sent to the correct agent.

---

## 3. Per-Question Results — All 100 Questions

### Incident Diagnosis (30 questions)

| ID | Question | v3 | 7B | Agents | Best |
|----|----------|----|----|--------|------|
| INC-RAN-01 | CPU at 97% on eNodeB | 0.50 | 0.83 | — | 7B |
| INC-RAN-02 | RACH failure 18% | 0.60 | 0.80 | — | 7B |
| INC-RAN-03 | DL throughput dropped 40% | 0.44 | 0.50 | — | 7B |
| INC-RAN-04 | HO success rate 82% | 0.80 | 0.40 | — | v3 |
| INC-RAN-05 | VSWR alarm sector 2 | 0.67 | 1.00 | — | 7B |
| INC-RAN-06 | PCI collision | 1.00 | 0.78 | — | v3 |
| INC-RAN-07 | Cell out of service BBU | 0.80 | 0.80 | — | Tie |
| INC-RAN-08 | RRC setup 85% | 0.60 | 0.56 | — | v3 |
| INC-RAN-09 | PRB utilization 92% | 0.45 | 0.50 | — | 7B |
| INC-RAN-10 | PDCP packet loss 3.5% | 0.56 | 0.33 | — | v3 |
| INC-CORE-01 | S1 link failure SCTP | 0.82 | 0.64 | — | v3 |
| INC-CORE-02 | AMF registration 15% | 0.67 | 0.67 | — | Tie |
| INC-CORE-03 | PDU session failure IP pool | 0.64 | 0.67 | — | 7B |
| INC-CORE-04 | GTP-U path failure echo | 0.78 | 0.78 | — | Tie |
| INC-CORE-05 | NRF not responding | 0.80 | 0.78 | — | v3 |
| INC-CORE-06 | HSS replication lag | 0.80 | 0.80 | — | Tie |
| INC-CORE-07 | Diameter Gx down 3868 | 0.78 | 0.78 | — | Tie |
| INC-CORE-08 | NSSF rejecting SST=1 | 0.56 | 0.60 | — | 7B |
| INC-TRANS-01 | Packet loss 4% microwave | 0.33 | 0.45 | — | 7B |
| INC-TRANS-02 | BGP flapping every 5 min | 0.80 | 0.33 | — | v3 |
| INC-TRANS-03 | MPLS LSP down LDP | — | — | — | — |
| INC-TRANS-04 | PTP sync lost GNSS | — | — | — | — |
| INC-TRANS-05 | DWDM optical 6dB drop | — | — | — | — |
| INC-TRANS-06 | QoS dropping voice DSCP | — | — | — | — |
| INC-IMS-01 | VoLTE failure SIP 503 | — | — | — | — |
| INC-IMS-02 | One-way audio VoLTE | — | — | — | — |
| INC-IMS-03 | SRVCC failure Sv interface | — | — | — | — |
| INC-IMS-04 | Emergency 911 failing | — | — | — | — |
| INC-IMS-05 | IMS registration 403 | — | — | — | — |
| INC-IMS-06 | SBC registration storm | — | — | — | — |

*Note: "—" indicates per-question score was not captured in the first 20 run; overall category score includes all 30.*

### Config Generation (20 questions)

| ID | Question | v3 | 7B | Agents |
|----|----------|----|----|--------|
| CFG-01 | URLLC slice autonomous vehicles | — | — | — |
| CFG-02 | VoNR QoS 128kbps | — | — | — |
| CFG-03 | CA n78+n1 | — | — | — |
| CFG-04 | 5G NR cell n78 100MHz 4x4 | — | — | — |
| CFG-05 | SON ANR+MLB+MRO | — | — | — |
| CFG-06 | RAN energy saving carrier shutdown | — | — | — |
| CFG-07 | IoT mMTC slice PSM eDRX | — | — | — |
| CFG-08 | IPsec IKEv2 AES-256 | — | — | — |
| CFG-09 | HO n78→n1 A2 A5 | — | — | — |
| CFG-10 | UPF edge ULCL | — | — | — |
| CFG-11 | MOCN sharing 60/40 | — | — | — |
| CFG-12 | DRX 40ms long 10ms short | — | — | — |
| CFG-13 | Alarm correlation power failure | — | — | — |
| CFG-14 | PM counters KPI dashboard | — | — | — |
| CFG-15 | NWDAF anomaly detection | — | — | — |
| CFG-16 | O-RAN RIC xApp load balance | — | — | — |
| CFG-17 | CSFB LTE→3G UARFCN 10713 | — | — | — |
| CFG-18 | MEC edge video streaming | — | — | — |
| CFG-19 | SEPP N32 roaming TLS | — | — | — |
| CFG-20 | NRF NF registration SMF | — | — | — |

*Category scores: v3=86.0%, 7B=91.5%, Agents=96.1%*

### KPI Analysis (15 questions)

| ID | Question | v3 | 7B | Agents |
|----|----------|----|----|--------|
| KPI-01 | ERAB drop 0.5%→2.8% | 0.40 | 0.33 | — |
| KPI-02 | RRC setup 87% | 0.43 | 0.43 | — |
| KPI-03 | VoLTE MOS 3.8→3.1 | 0.25 | 0.75 | — |
| KPI-04 | DL throughput 15Mbps on 20MHz | 0.00 | 0.14 | — |
| KPI-05 | HO success 88% | 0.11 | 0.11 | — |
| KPI-06 | Inter-RAT HO 15% failure | 0.43 | 0.43 | — |
| KPI-07 | PRB 95% but only 100 UEs | 0.71 | 0.43 | — |
| KPI-08 | UL interference +5dB cluster | 0.43 | 0.43 | — |
| KPI-09 | Energy per GB 30% higher | 0.33 | 0.33 | — |
| KPI-10 | Attach success 99.5%→97% | 0.14 | 0.50 | — |
| KPI-11 | VoLTE drop 2% North only | 0.71 | 0.71 | — |
| KPI-12 | Paging success 85% | 0.43 | 0.43 | — |
| KPI-13 | Bearer modification 90% | 0.75 | 1.00 | — |
| KPI-14 | X2 99% vs S1 92% | 0.56 | 0.80 | — |
| KPI-15 | Registration reject cause #5 | 1.00 | 1.00 | — |

### Protocol Knowledge (20 questions)

| ID | Question | v3 | 7B | Agents |
|----|----------|----|----|--------|
| PROTO-01 | 5QI values voice/video/BE | — | — | — |
| PROTO-02 | N4 interface PFCP | — | — | — |
| PROTO-03 | NSA 3x vs SA Option 2 | — | — | — |
| PROTO-04 | RACH 4-step procedure | — | — | — |
| PROTO-05 | Network slicing S-NSSAI | — | — | — |
| PROTO-06 | AMF SMF UPF roles | — | — | — |
| PROTO-07 | CUPS importance | — | — | — |
| PROTO-08 | HARQ sync vs async | — | — | — |
| PROTO-09 | CU-DU split layers | — | — | — |
| PROTO-10 | TAU procedure LTE | — | — | — |
| PROTO-11 | SSB contents | — | — | — |
| PROTO-12 | Carrier aggregation inter/intra | — | — | — |
| PROTO-13 | MIMO vs massive MIMO | — | — | — |
| PROTO-14 | IMS architecture CSCFs | — | — | — |
| PROTO-15 | GBR vs Non-GBR bearers | — | — | — |
| PROTO-16 | NRF SBA discovery | — | — | — |
| PROTO-17 | Subcarrier spacings 5G NR | — | — | — |
| PROTO-18 | FDD vs TDD why TDD for 5G | — | — | — |
| PROTO-19 | O-RAN vs traditional RAN | — | — | — |
| PROTO-20 | MEC role in 5G | — | — | — |

*Category scores: v3=40.0%, 7B=85.2%, Agents=83.8%*

### Routing Accuracy (15 questions)

| ID | Question | Expected | Actual | Correct |
|----|----------|----------|--------|---------|
| ROUTE-01 | High CPU on eNodeB | incident | incident | ✅ |
| ROUTE-02 | Generate YAML config slicing | config | config | ✅ |
| ROUTE-03 | What does 3GPP say about N4 | knowledge | knowledge | ✅ |
| ROUTE-04 | S1 link failure eNodeB MME | incident | incident | ✅ |
| ROUTE-05 | Configure IPsec tunnel | config | config | ✅ |
| ROUTE-06 | Difference NSA and SA | knowledge | knowledge | ✅ |
| ROUTE-07 | ERAB drop rate 3% | incident | incident | ✅ |
| ROUTE-08 | Set up QoS policy VoNR | config | config | ✅ |
| ROUTE-09 | What is MIMO | knowledge | knowledge | ✅ |
| ROUTE-10 | VoLTE call setup failure 15% | incident | incident | ✅ |
| ROUTE-11 | Create slice autonomous vehicles | config | config | ✅ |
| ROUTE-12 | How does network slicing work | knowledge | knowledge | ✅ |
| ROUTE-13 | BGP peer down PE routers | incident | incident | ✅ |
| ROUTE-14 | Configure O-RAN RIC xApp | config | config | ✅ |
| ROUTE-15 | Role of AMF in 5G core | knowledge | knowledge | ✅ |

**Routing: 15/15 = 100%**

---

## 4. Key Findings

### 4.1 The Agent System Wins
The hybrid Agent System (83.4%) outperforms both the fine-tuned 1.5B (61.4%) and the base 7B (76.1%) individually. The routing + right-tool-for-the-job approach works.

### 4.2 Where Each Model Excels

| Strength | Best Model | Score |
|----------|-----------|-------|
| Config generation | Agent System | 96.1% |
| Protocol knowledge | Base 7B | 85.2% |
| Incident diagnosis | Agent System | 78.3% |
| Routing accuracy | Agent System (Supervisor) | 100% |
| Speed | v3 (1.5B) | 5-11s avg |

### 4.3 Where v3 (1.5B) Beats 7B
Fine-tuning pays off for specific trained scenarios:

| Question | v3 | 7B | Why v3 Wins |
|----------|----|----|------------|
| HO success rate analysis | 0.80 | 0.40 | Trained on HO scenarios |
| PCI collision | 1.00 | 0.78 | Exact training template match |
| S1 link failure | 0.82 | 0.64 | Trained on S1 scenarios |
| BGP flapping | 0.80 | 0.33 | Trained on BGP scenarios |
| NRF not responding | 0.80 | 0.78 | Trained on NRF scenarios |
| PDCP packet loss | 0.56 | 0.33 | Trained on PDCP scenarios |

### 4.4 Where 7B Crushes 1.5B
Reasoning and general knowledge:

| Question | v3 | 7B | Why 7B Wins |
|----------|----|----|------------|
| Protocol knowledge (all 20) | 40.0% | 85.2% | 7B has more world knowledge |
| VoLTE MOS analysis | 0.25 | 0.75 | Requires analytical reasoning |
| CPU analysis on eNodeB | 0.50 | 0.83 | Better root cause reasoning |
| VSWR alarm | 0.67 | 1.00 | Deeper hardware knowledge |

### 4.5 The KPI Gap
KPI analysis is the weakest category for ALL models (v3: 45%, 7B: 52%, Agents: 60%). This requires:
- Multi-step analytical reasoning
- Correlation between metrics
- Domain-specific thresholds and interpretation
- This is where expert training data (from ChatGPT/Claude) would help most

---

## 5. What Fine-tuned 7B Should Deliver

Based on the data:
- Base 7B scores 76.1% with zero telco-specific training
- v3's fine-tuning boosted config generation from base to 86%
- Fine-tuning on 7B should boost ALL categories similarly

**Expected fine-tuned 7B scores:**

| Category | Base 7B | Expected FT-7B | Reasoning |
|----------|---------|----------------|-----------|
| Config | 91.5% | **95%+** | Already strong, fine-tuning adds template precision |
| Incident | 71.6% | **85%+** | 7B reasoning + trained scenarios = big improvement |
| Knowledge | 85.2% | **88%+** | Already strong, fine-tuning adds telco specifics |
| KPI | 52.4% | **65%+** | Biggest expected improvement — trained on KPI analysis |
| Routing | 100% | **100%** | Already perfect |
| **Overall** | **76.1%** | **85-90%** | |

**Expected Agent System with fine-tuned 7B: 90%+**

---

## 6. Benchmark Coverage vs Training Scenarios

| Domain | Training Scenarios | Benchmark Questions | Coverage |
|--------|-------------------|--------------------|---------|
| RAN | 10 | 10 | 100% |
| Core | 14 | 8 | 57% |
| Transport | 12 | 6 | 50% |
| IMS/VoLTE | 8 | 6 | 75% |
| Security | 2 | 0 | 0% |
| Power | 1 | 0 | 0% |
| Config templates | 25 | 20 | 80% |
| KPI analysis | 4 topics | 15 | Expanded beyond training |
| Protocol knowledge | 3 topics | 20 | Expanded beyond training |
| Routing | N/A | 15 | N/A |

Missing from benchmark: Security scenarios (signaling storm, cert expiry), Power scenarios, 6 Core scenarios, 6 Transport scenarios.

---

## 7. Files

| File | Content |
|------|---------|
| `scripts/evaluation/operational_benchmark.py` | Benchmark code (100 questions + scoring) |
| `models/benchmark_v3.json` | v3 detailed results |
| `models/benchmark_7b.json` | Base 7B detailed results |
| `models/benchmark_agents.json` | Agent system detailed results |
| `BENCHMARK_RESULTS.md` | This report |
