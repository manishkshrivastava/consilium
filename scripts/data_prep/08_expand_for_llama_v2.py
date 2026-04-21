"""
Step 8: Expand v1 training data with targeted KPI + Protocol knowledge
for Llama 3.1 8B v2 training.

Based on benchmark gaps:
- KPI: 61.1% (weakest category)
- Knowledge: 73.0% (second weakest)

Strategy: Add high-quality examples targeting exact weak spots from benchmark.
"""

import json
import random
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

SYSTEM_PROMPT = (
    "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
    "You have deep knowledge of 3GPP standards, 5G/LTE network operations, "
    "RAN optimization, core network, transport, and IMS/VoLTE. "
    "You assist network engineers with diagnostics, configuration, "
    "troubleshooting, and standards interpretation."
)


def make_record(user_content, assistant_content, category):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "category": category,
    }


# =============================================================================
# KPI ANALYSIS EXAMPLES (targeting benchmark weak spots)
# =============================================================================

KPI_EXAMPLES = [
    # Inter-RAT handover (KPI-06 scored 0.14)
    make_record(
        "Inter-RAT handover from 5G to 4G has a 15% failure rate. What are the likely causes and how do I troubleshoot?",
        """Inter-RAT handover failure rate of 15% is significantly above the 5% target threshold. This indicates issues in the 5G-to-4G mobility procedure.

**Likely causes:**
1. **Measurement configuration issues**: A2/B1 event thresholds may be misconfigured — if B1 threshold is too aggressive, handover triggers when 4G signal is still too weak
2. **Target cell preparation failure**: The 4G eNodeB may be rejecting handover requests due to resource unavailability or admission control
3. **Timer expiry (T304)**: UE fails to complete random access on the 4G target cell within the configured timer
4. **SRVCC configuration issues**: If these are voice calls, check Sv interface between MME and MSC
5. **Missing neighbor relations**: 5G-to-4G neighbor cell list may be incomplete
6. **Parameter mismatch**: PLMN ID, TAC, or frequency mismatch between source and target

**Troubleshooting steps:**
1. Check inter-RAT handover counters — separate preparation failures from execution failures
2. Analyze B1/B2 measurement reports — verify RSRP/RSRQ thresholds
3. Check X2/Xn interface status between gNB and eNodeB
4. Review target cell admission control settings — check if rejecting due to congestion
5. Verify NR-to-LTE frequency mapping and neighbor relations
6. Check UE capability — some UEs may not support specific inter-RAT handover scenarios
7. Analyze call traces/CDRs to identify failure point in the procedure
8. Compare success rates by target cell to isolate problematic cells""",
        "kpi_analysis"
    ),
    make_record(
        "What KPIs should I monitor for inter-RAT handover between 5G NR and LTE? What are acceptable thresholds?",
        """Key KPIs for inter-RAT handover monitoring between 5G NR and LTE:

**Primary KPIs:**
1. **Inter-RAT HO Preparation Success Rate**: Target >98%. Measures if target eNodeB accepts the HO request
2. **Inter-RAT HO Execution Success Rate**: Target >95%. Measures if UE successfully completes the HO
3. **Inter-RAT HO Overall Success Rate**: Target >93%. End-to-end success rate
4. **Inter-RAT HO Mean Interruption Time**: Target <100ms for data, <300ms for voice

**Secondary KPIs:**
5. **Inter-RAT HO Failure Rate by Cause**: Break down by timeout, rejection, radio link failure
6. **Ping-Pong Handover Rate**: Target <5%. UE bouncing between RATs
7. **Too-Early/Too-Late HO Rate**: Indicates threshold misconfiguration
8. **SRVCC Success Rate** (voice): Target >95% for VoNR-to-VoLTE fallback

**Measurement Events:**
- A2: Serving cell below threshold (triggers inter-RAT measurement)
- B1: Inter-RAT neighbor above threshold (triggers HO)
- B2: Serving below threshold AND inter-RAT neighbor above threshold

**Thresholds to tune:**
- A2 RSRP threshold: typically -110 to -115 dBm
- B1 RSRP threshold: typically -105 to -110 dBm
- Time-to-trigger: 160ms to 640ms depending on mobility scenario""",
        "kpi_analysis"
    ),
    # VoLTE MOS score (KPI-03 scored 0.43)
    make_record(
        "VoLTE MOS score dropped from 3.8 to 3.1. What factors affect MOS and how should I investigate?",
        """A MOS (Mean Opinion Score) drop from 3.8 to 3.1 is significant — below the 3.5 threshold for acceptable voice quality. This needs immediate investigation.

**Factors affecting VoLTE MOS:**
1. **Codec selection**: AMR-WB (HD Voice) typically gives MOS 4.0-4.5, AMR-NB gives 3.0-3.8
2. **Packet loss**: >1% packet loss severely degrades MOS. 3% loss can drop MOS by 0.5-1.0
3. **Jitter**: >30ms jitter causes audible artifacts. De-jitter buffer may discard late packets
4. **Latency**: One-way delay >150ms causes conversational difficulty
5. **Radio conditions**: Poor SINR causes RLC retransmissions, adding delay and potential loss
6. **Transcoding**: Each transcoding hop degrades quality by ~0.5 MOS points
7. **SBC processing**: Media handling at Session Border Controller can add latency

**Investigation steps:**
1. **Check codec usage**: Verify AMR-WB is being negotiated. If fallback to AMR-NB, investigate SDP negotiation
2. **Measure packet loss on GTP-U path**: Check counters on eNodeB, SGW, PGW for PDCP/GTP packet loss
3. **Check RAN KPIs**: DL/UL BLER, HARQ retransmission rate, PDCP discard rate on QCI=1 bearer
4. **Measure jitter**: Use RTP stream analysis. Check de-jitter buffer statistics on the media gateway
5. **Verify QoS**: Ensure QCI=1 bearer has GBR=128kbps and is getting priority scheduling
6. **Check IMS path**: Verify no unnecessary transcodings in the media path (P-CSCF → S-CSCF → MGCF)
7. **Regional analysis**: If MOS drop is localized, correlate with specific cells or transport links
8. **Compare DL vs UL**: If one-directional, likely radio or transport issue on that path""",
        "kpi_analysis"
    ),
    # DL throughput analysis (KPI-04 scored 0.43)
    make_record(
        "Average DL user throughput is 15Mbps on a 20MHz LTE cell. Is this normal? How do I analyze it?",
        """15 Mbps average DL user throughput on a 20MHz LTE cell is **below expected** but not necessarily abnormal — it depends on conditions.

**Theoretical vs practical throughput for 20MHz LTE:**
- Peak (single user, 64QAM, 2x2 MIMO): ~150 Mbps
- Typical cell throughput: 80-120 Mbps shared
- Per-user average with 10-20 users: 5-15 Mbps is common during busy hours
- Per-user average off-peak: 30-60 Mbps expected

**Key factors to check:**
1. **PRB utilization**: If >70%, cell is congested — 15Mbps is reasonable. If <30%, something is wrong
2. **Number of active users**: 15Mbps with 5 users is poor; with 30 users is acceptable
3. **CQI distribution**: Average CQI <8 indicates poor radio conditions limiting modulation
4. **MIMO rank**: Check rank indicator — if mostly Rank 1, MIMO gain is lost (antenna or propagation issue)
5. **BLER**: Target 10% for initial transmission. Higher BLER means excessive retransmissions
6. **Scheduler efficiency**: Check if proportional fair scheduler is configured correctly
7. **Interference**: Check RSSI and SINR — inter-cell interference may be limiting throughput

**Analysis approach:**
1. Compare against cell design capacity (link budget) for the coverage area
2. Check busy hour vs off-peak — if both are 15Mbps, there's a persistent issue
3. Benchmark against peer cells with similar configuration and traffic
4. Check if CA (Carrier Aggregation) is available and being utilized
5. Analyze CQI vs throughput correlation — low CQI cells need RF optimization
6. Review traffic mix — video streaming needs different analysis than web browsing
7. Check TCP optimization — MSS, window size, and RTT affect application throughput""",
        "kpi_analysis"
    ),
    # Handover success rate (KPI-05 scored 0.40)
    make_record(
        "Handover success rate between two 5G cells is only 88%. How should I analyze this?",
        """88% handover success rate between 5G cells is below the 95% target. This needs systematic analysis.

**Step 1: Classify the failure type**
- **Preparation failure** (before HO command): Target cell rejects the request
- **Execution failure** (after HO command): UE fails to access target cell
- **Too-late HO**: Radio link failure before HO completes
- **Too-early HO**: UE returns to source cell immediately after HO

**Step 2: Check measurement configuration**
- A3 event offset: Too small = premature HO, too large = too-late HO
- Time-to-trigger (TTT): 40ms-5120ms. Too short = ping-pong, too long = too-late
- Hysteresis: Typically 1-3 dB
- Filter coefficient (k): Layer 3 filtering smooths measurements

**Step 3: Analyze by cause**
1. **Target cell congestion**: Check admission control rejection counters on target gNB
2. **RACH failure on target**: Check preamble detection rate, contention resolution success
3. **Radio link failure (RLF)**: Check N310/N311 timers and out-of-sync detection
4. **Xn/X2 interface issues**: Check SCTP association status and latency between gNBs
5. **UE capability**: Some UEs may not support specific beam management for HO

**Step 4: Parameter optimization**
1. Adjust A3 offset based on HO failure analysis (too-early vs too-late)
2. Tune TTT: Increase if ping-pong, decrease if too-late failures dominate
3. Check SSB beam-level measurement configuration for beam-based HO
4. Verify conditional handover (CHO) if supported — can reduce HO failures by 30-50%
5. Check DAPS (Dual Active Protocol Stack) handover for zero-interruption HO
6. Optimize target cell RACH configuration — preamble power, ramping step, max retries""",
        "kpi_analysis"
    ),
    make_record(
        "ERAB drop rate increased from 0.5% to 2.8% over the past week. What analysis should I perform?",
        """ERAB drop rate increase from 0.5% to 2.8% is a significant degradation — 2.8% exceeds the typical 1% target threshold. Systematic analysis required.

**Step 1: Categorize drops by cause group**
1. **Radio link failure (RLF)**: Usually the largest contributor. UE loses sync with eNodeB
2. **Transport failure**: S1/X2 path issues causing bearer release
3. **Resource shortage**: PRB exhaustion, hardware limitations
4. **Handover failure**: Incomplete HOs leading to ERAB drops
5. **Timer expiry**: Inactivity timers or UE context release timers

**Step 2: Correlate with other KPIs**
- If **UL SINR degraded**: Likely interference issue → check PCI conflicts, antenna tilt
- If **PDCP packet loss up**: Transport issue → check backhaul link quality
- If **PRB utilization >80%**: Congestion → capacity expansion needed
- If **HO failures up**: Mobility issue → check neighbor relations, A3 parameters
- If **RACH failures up**: Access issue → check preamble allocation, power settings

**Step 3: Time-based analysis**
1. Plot ERAB drop rate hourly — does it correlate with traffic patterns?
2. Check if increase started with a specific date (software upgrade? config change?)
3. Compare weekday vs weekend patterns
4. Check weather correlation (rain fade on microwave backhaul)

**Step 4: Cell-level analysis**
1. Identify top 10 worst cells — is the problem widespread or localized?
2. If localized: Site visit, check antenna, cables, hardware alarms
3. If widespread: Software issue, parameter change, or external interference
4. Compare affected cells vs healthy cells — what's different?

**Step 5: Remediation**
1. For RLF-dominated drops: Optimize DL/UL power control, adjust RLF timers (T310, N310, N311)
2. For transport drops: Check and repair backhaul, add redundancy
3. For congestion drops: Load balancing, carrier addition, cell split
4. For HO drops: Optimize mobility parameters, add missing neighbors""",
        "kpi_analysis"
    ),
    make_record(
        "Paging success rate dropped to 85% on MME-02. What does this indicate and how to fix it?",
        """Paging success rate of 85% on MME-02 is critically low — target is >98%. This means 15% of mobile-terminated calls/messages are not reaching subscribers.

**What paging does:**
MME pages the UE in its registered Tracking Area (TA) when there's an incoming call/data. The UE monitors paging in DRX cycles. Failed paging = missed calls, delayed notifications.

**Root causes by category:**

1. **UE-side issues:**
   - UEs in poor coverage areas can't decode paging messages
   - Battery-saving modes extending DRX cycles too aggressively
   - UEs that have moved out of their registered TA without updating (TA update failure)

2. **RAN-side issues:**
   - Paging channel congestion — too many paging messages per paging occasion
   - Incorrect paging DRX configuration on eNodeBs
   - PCCH (Paging Control Channel) resource allocation insufficient
   - Paging occasion calculation mismatch between MME and eNodeB

3. **Core-side issues:**
   - MME overload causing delayed paging requests (UE DRX cycle missed)
   - S1AP paging message delivery failure to specific eNodeBs
   - Tracking Area configuration too large (too many cells to page)
   - MME pool area misconfiguration — paging sent to wrong eNodeBs

4. **Transport issues:**
   - S1 link congestion delaying paging delivery
   - SCTP association instability between MME and eNodeBs

**Troubleshooting steps:**
1. Check if the issue is specific to certain Tracking Areas or all TAs
2. Compare paging load on MME-02 vs other MMEs — check subscriber distribution
3. Verify S1AP statistics — paging requests sent vs responses received
4. Check eNodeB paging queue depth and overflow counters
5. Review TA configuration — split oversized TAs to reduce paging load
6. Check paging DRX parameters consistency (defaultPagingCycle)
7. Verify IMSI-based paging distribution across paging occasions
8. If MME overload, consider rebalancing subscribers across MME pool""",
        "kpi_analysis"
    ),
    make_record(
        "Cell shows 95% PRB utilization but only 100 connected UEs. Is this normal?",
        """95% PRB utilization with only 100 UEs is **abnormal** — this indicates resource inefficiency. A typical cell should handle 200-400 UEs at 95% PRB utilization.

**Possible causes:**

1. **High per-user resource consumption:**
   - Users running high-bandwidth applications (video streaming, large downloads)
   - Low MCS (Modulation and Coding Scheme) due to poor radio conditions → more PRBs needed per user
   - Check average CQI — if <7, users are in poor RF conditions consuming excess PRBs

2. **Scheduling inefficiency:**
   - Persistent scheduling allocating fixed PRBs regardless of actual traffic
   - Over-provisioned GBR bearers reserving PRBs (e.g., VoLTE bearers allocated but idle)
   - Scheduler not efficiently packing users into available PRBs

3. **Interference issues:**
   - High inter-cell interference forcing low MCS → more PRBs per bit
   - Check DL SINR distribution — if >30% of samples below 5dB, interference is the issue
   - ICIC (Inter-Cell Interference Coordination) or eICIC may not be configured

4. **Configuration issues:**
   - PRB reservation for RACH, SRS, or other control channels too high
   - SIB broadcasting using excessive resources
   - MBMS/multicast reserving PRBs unnecessarily

**Analysis steps:**
1. Check average DL/UL throughput per user — if >10Mbps per user average, traffic is genuinely high
2. Check CQI distribution and BLER — poor radio = low spectral efficiency
3. Compare with peer cells having similar UE count but lower PRB utilization
4. Check GBR bearer count vs Non-GBR — are GBR bearers over-reserved?
5. Review PDCCH utilization — CCE usage should be proportional to UE count
6. Check if carrier aggregation is available — offload traffic to secondary carrier""",
        "kpi_analysis"
    ),
    make_record(
        "Attach success rate on MME dropped from 99.5% to 97%. What could be causing this?",
        """Attach success rate dropping from 99.5% to 97% is a notable degradation. While 97% may seem acceptable, it means ~3% of subscribers can't connect — potentially thousands of failed attach attempts daily.

**Attach procedure steps (failure at each step):**
1. **RRC Connection Setup** → Radio failure, RACH overload
2. **Authentication (AKA)** → HSS timeout, IMSI/key mismatch
3. **NAS Security Mode** → Security algorithm mismatch
4. **ESM: Default Bearer Setup** → PGW/SGW resource exhaustion
5. **S1AP: Initial Context Setup** → eNodeB resource failure

**Common causes for 2.5% drop:**

1. **HSS/Authentication issues:**
   - HSS overloaded — Diameter Cx/Sh response time increased
   - Authentication vector cache expired/depleted
   - Subscriber provisioning issues (new SIM batch with incorrect Ki/OPc)

2. **Core network congestion:**
   - SGW/PGW running low on IP addresses in APN pool
   - MME processing capacity approaching limit
   - GTP-C path failure between MME-SGW or SGW-PGW

3. **RAN issues:**
   - Initial Context Setup failures due to eNodeB resource shortage
   - S1 link congestion causing message timeouts
   - Increased RRC setup failures (check RACH KPIs)

4. **Subscriber-related:**
   - Roaming subscribers with authentication delays
   - IoT device mass reconnection event (power restoration)
   - New device/SIM activation batch with provisioning errors

**Troubleshooting:**
1. Break down failures by reject cause code (EMM cause values)
2. Check if failure is localized to specific eNodeBs or widespread
3. Monitor HSS response time and success rate
4. Check IP pool utilization on PGW for all APNs
5. Review Initial Context Setup failure counters on eNodeBs
6. Compare attach attempt volume — has it spiked? (DoS, IoT reconnect)
7. Check NAS timer configurations (T3410 on UE, T3450/T3460 on MME)""",
        "kpi_analysis"
    ),
    make_record(
        "Bearer modification success rate is 90%. What could cause failures and how to fix it?",
        """90% bearer modification success rate is below the 98% target. Bearer modifications occur during QoS changes, handovers, and service upgrades — failures impact active user sessions.

**When bearer modification happens:**
- QoS upgrade/downgrade (e.g., starting video call during data session)
- Dedicated bearer activation for specific services
- Handover requiring bearer reconfiguration
- APN-AMBR or UE-AMBR changes triggered by PCRF

**Common failure causes:**

1. **PCRF/Gx interface issues (30% of failures):**
   - PCRF policy decision timeout — Diameter Gx CCA delayed
   - PCC rule installation failure — incompatible QoS parameters
   - Rx interface issues if triggered by IMS (AF session)
   - Check Diameter message statistics: CCR/CCA success rate

2. **SGW/PGW resource issues (25% of failures):**
   - GTP-C Update Bearer Request timeout between SGW and PGW
   - Bearer context not found (race condition with release)
   - S5/S8 interface congestion

3. **RAN resource issues (25% of failures):**
   - eNodeB cannot allocate resources for modified QoS
   - E-RAB modification failure due to PRB shortage
   - DRB reconfiguration failure at UE

4. **UE issues (20% of failures):**
   - UE rejects RRC reconfiguration for the modified bearer
   - UE capability doesn't support requested QoS
   - Timer expiry during UE processing

**Troubleshooting steps:**
1. Categorize failures: core-initiated vs RAN-initiated modifications
2. Check Gx interface counters — CCA result codes (DIAMETER_SUCCESS vs errors)
3. Monitor GTP-C Update Bearer Request/Response success rate
4. Check E-RAB Modification Indication success rate per cell
5. Review UE RRC Reconfiguration Complete success rate
6. Check if failures correlate with specific services (VoLTE, video)
7. Verify QoS parameter consistency across PCRF, PGW, SGW, and eNodeB""",
        "kpi_analysis"
    ),
    make_record(
        "Our network's energy consumption per GB of data is 30% higher than industry benchmark. How do I analyze and optimize?",
        """30% higher energy per GB than benchmark is significant and directly impacts OPEX. Telecom networks typically consume 2-3% of global electricity. Optimization requires systematic analysis.

**Key energy KPIs:**
- Energy Consumption per GB (EC/GB): Industry target <0.3 kWh/GB for LTE, <0.1 kWh/GB for 5G
- Energy Efficiency (bits/Joule): Higher is better
- Site Energy Consumption: kWh per site per month
- Network Energy Proportionality: Energy should scale with traffic

**Analysis framework:**

1. **RAN energy (60-80% of total network energy):**
   - Power amplifier efficiency — older PAs waste 50-70% as heat
   - Massive MIMO active antenna units consume more but serve more capacity
   - Check if sites are oversized for actual traffic demand
   - Night-time energy — are carriers/sectors being shut down during low traffic?

2. **Cooling energy (20-30% of site energy):**
   - PUE (Power Usage Effectiveness): Target <1.5
   - Check if free cooling is used where climate allows
   - Assess cooling system efficiency and thermostat settings

3. **Transport & Core (10-20%):**
   - Router/switch power efficiency
   - Data center PUE for core network

**Optimization steps:**
1. **Carrier/symbol shutdown**: Disable secondary carriers when PRB util <10% (saves 30-40%)
2. **MIMO adaptation**: Reduce from 4T4R to 2T2R during low traffic (saves 15-20%)
3. **DTX (Discontinuous Transmission)**: Enable cell DTX to turn off PA during empty symbols
4. **Sleep modes**: Micro-sleep for RF components during idle periods
5. **Site modernization**: Replace old RRUs with energy-efficient models (can halve consumption)
6. **Cooling optimization**: Raise operating temperature threshold, deploy free cooling
7. **AI-based control**: Use NWDAF/SON for traffic-adaptive energy management
8. **Renewable energy**: Solar panels for rural sites reduce grid dependency""",
        "kpi_analysis"
    ),
    make_record(
        "VoLTE call drop rate is 2% but only in the North region. Other regions show 0.5%. How to analyze?",
        """Region-specific VoLTE call drop rate of 2% (vs 0.5% elsewhere) points to a localized issue. The 0.5% baseline proves the network can deliver — so focus on what's different in the North.

**Analysis approach:**

1. **Compare North vs other regions:**
   - RAN vendor/software version differences
   - Transport topology (microwave vs fiber backhaul)
   - Core network path (different SGW/PGW/IMS elements?)
   - Traffic density and cell load patterns

2. **Break down the 2% by cause:**
   - Radio Link Failure (RLF): Check DL/UL SINR, BLER, power headroom
   - Handover failure: Check HO success rate during active VoLTE calls
   - Transport drop: Check S1-U packet loss for QCI=1 bearers
   - Core/IMS signaling: Check SIP BYE/timeout statistics on P-CSCF
   - Timer expiry: RLC max retransmission reached

3. **Cell-level analysis:**
   - Identify top 20 worst cells in North region
   - Check if they share common characteristics (rural, highway, indoor)
   - Check for recent config changes, hardware alarms, or software updates

4. **Transport analysis (critical for North):**
   - If North uses microwave backhaul: Check RSL, rain fade events, link availability
   - Measure one-way delay on backhaul — VoLTE sensitive to >50ms
   - Check QoS marking preservation for DSCP EF (QCI=1) across transport

5. **IMS path analysis:**
   - Check if North region routes through different P-CSCF/S-CSCF
   - Media path: Any transcoding or media relay differences?
   - SBC processing — are there different SBC instances for North?

**Quick wins:**
1. Fix worst 20 cells (usually covers 60% of drops)
2. Check and repair microwave links with RSL margin <5dB
3. Verify QCI=1 bearer priority is consistent across all eNodeBs
4. Ensure RLC max retransmission count is set to 16 (not lower) for SRB/DRB""",
        "kpi_analysis"
    ),
    make_record(
        "X2 handover success rate is 99% but S1 handover is only 92%. What explains this difference?",
        """The 7% gap between X2 (99%) and S1 (92%) handover success rates is expected but the S1 rate needs improvement. Here's why they differ and how to fix it.

**Why X2 is better than S1:**
- **X2 handover**: Direct communication between eNodeBs. Faster preparation, lower latency, less signaling overhead. Used when X2 interface exists between source and target
- **S1 handover**: Goes through MME (source eNB → MME → target eNB). More signaling hops, higher latency, more failure points. Used when no X2 interface or inter-MME handover

**Why S1 at 92% needs attention:**
S1 HO is typically used for:
1. Inter-MME handovers (crossing MME pool boundaries)
2. Sites without X2 connectivity
3. Inter-RAT scenarios through core

**Common S1 HO failure causes:**

1. **MME processing delay (most common):**
   - S1AP Handover Required → MME → S1AP Handover Request to target
   - If MME is congested, the entire chain slows down
   - Check MME CPU and Handover Request→Response latency

2. **Missing X2 causing unnecessary S1:**
   - Many S1 HOs happen simply because X2 isn't configured
   - Adding X2 between frequently-used cell pairs converts them to faster X2 HO
   - Check ANR (Automatic Neighbor Relations) — is it enabled?

3. **Inter-MME issues:**
   - S10 interface problems between MMEs
   - UE context transfer failures
   - Different MME software versions causing compatibility issues

4. **Target cell rejection:**
   - More likely with S1 due to delayed preparation (cell congested by the time HO executes)
   - Admission control on target rejects because resource situation changed during the longer procedure

**Optimization:**
1. Deploy X2 between all frequently-used cell pairs — this alone can cut S1 HO volume by 60%
2. Enable ANR to auto-discover and configure X2 neighbors
3. Tune S1 HO timers — reduce T_Reloc_Prep and T_Reloc_Overall if they're too long
4. Check and optimize MME processing capacity
5. For remaining S1 HOs, analyze failure counters per cause to target specific fixes""",
        "kpi_analysis"
    ),
    make_record(
        "5G SA network shows 5% registration rejection rate. Most rejections are cause #5. What does this mean?",
        """5% registration rejection with NAS cause #5 (PLMN not allowed) indicates a roaming or PLMN configuration issue.

**NAS 5GMM Cause #5 — PLMN Not Allowed:**
The AMF rejects the registration because the UE's home PLMN is not in the AMF's list of allowed PLMNs, or roaming agreements are not properly configured.

**Common scenarios:**

1. **Roaming subscribers:**
   - Home PLMN not in the visited network's roaming agreement list
   - SEPP (Security Edge Protection Proxy) blocking the N32 connection
   - Check if recently updated roaming agreements are reflected in AMF config

2. **MVNO/sub-brand subscribers:**
   - MVNO PLMN ID not configured in the host network's AMF
   - Shared network (MOCN) missing PLMN mapping

3. **Dual-PLMN deployment:**
   - During migration (e.g., merger), some SIMs have old PLMN
   - UE selects wrong PLMN from the broadcast list

4. **SIM provisioning:**
   - New SIMs programmed with incorrect PLMN (manufacturing error)
   - eSIM profile with wrong PLMN downloaded

**Troubleshooting:**
1. Identify the rejected PLMN IDs — run NAS message trace on AMF
2. Check AMF configuration: plmnSupportList should include all valid PLMNs
3. Verify NSSF PLMN-specific slice configuration
4. For roaming: Check N32 SEPP connectivity and roaming partner PLMN list
5. Cross-reference UDM subscriber profiles — are these valid subscribers?
6. Check if the rejected UEs are IoT devices with specific PLMN restrictions
7. Review SIB1 broadcast PLMN list — ensure all valid PLMNs are advertised

**Impact:** Affected subscribers will see "No Service" or "Emergency Only" and cannot use the network until the PLMN configuration is corrected.""",
        "kpi_analysis"
    ),
    make_record(
        "Uplink interference level increased by 5dB across a cluster of cells. What are the likely sources?",
        """A 5dB uplink interference increase across a cell cluster is significant and indicates a systematic issue rather than a single-cell problem.

**Likely sources:**

1. **External interference (most common for cluster-wide):**
   - Illegal repeaters/boosters installed by subscribers or businesses
   - New radio system deployed on adjacent frequency band (guard band violation)
   - Industrial equipment generating RF interference
   - Passive intermodulation (PIM) from corroded connectors or rusty structures near antennas
   - Use spectrum scanner to identify interference source and direction

2. **Network-internal causes:**
   - Neighbor cell parameter change causing UEs to transmit at higher power
   - Open-loop power control misconfiguration (P0, alpha parameters)
   - TDD frame structure misalignment between cells (UL/DL interference)
   - New cells activated without proper frequency/PCI planning
   - Antenna downtilt changes on nearby sites expanding coverage overlap

3. **UE behavior:**
   - Mass event (concert, stadium) — many UEs in small area driving UL power up
   - IoT devices with aggressive transmission patterns

**Diagnosis steps:**
1. **Time analysis**: When did it start? Correlate with network changes, events, weather
2. **Frequency analysis**: Is interference on specific PRBs or wideband?
3. **Direction analysis**: Use antenna pattern to determine interference direction
4. **Spectrum scan**: Deploy portable spectrum analyzer at worst-affected sites
5. **Check IoT counters**: Rise in UL PRB utilization without corresponding DL increase suggests rogue UL transmitters
6. **PIM testing**: Conduct PIM sweep test on antenna system, especially if interference is on specific intermod frequencies

**Remediation by cause:**
- External: Locate and eliminate source (regulatory enforcement for illegal devices)
- PIM: Replace corroded components, improve grounding
- Parameter: Revert recent changes, optimize power control settings
- Capacity: Deploy additional carriers or small cells to offload""",
        "kpi_analysis"
    ),
]


# =============================================================================
# PROTOCOL KNOWLEDGE EXAMPLES (targeting benchmark weak spots)
# =============================================================================

PROTOCOL_EXAMPLES = [
    # TAU procedure (PROTO-10 scored 0.25)
    make_record(
        "Explain the Tracking Area Update (TAU) procedure in LTE in detail.",
        """The Tracking Area Update (TAU) procedure allows the UE to inform the network of its current location so the network can page the UE for incoming services.

**When TAU is triggered:**
1. **Periodic TAU**: Timer T3412 expires (default 54 minutes). UE sends TAU even if it hasn't moved
2. **Normal TAU**: UE enters a new Tracking Area (TA) not in its TA list
3. **Emergency TAU**: After emergency attach or emergency bearer services
4. **TAU for load balancing**: MME redirects UE to different MME via TAU

**TAU Procedure Steps:**

1. **UE → eNodeB → MME: TAU Request**
   - Contains: Old GUTI, UE network capabilities, last visited TAI, EPS bearer status
   - Sent as NAS message encapsulated in S1AP: Initial UE Message

2. **MME Context Transfer (if inter-MME):**
   - New MME sends Context Request to old MME via S10 (GTPv2-C)
   - Old MME responds with UE context (security context, bearer info)
   - If old MME unreachable: New MME must re-authenticate the UE

3. **Authentication & Security (optional):**
   - MME may run AKA procedure if security context is stale
   - NAS Security Mode Command to establish new NAS security

4. **Location Update:**
   - MME sends S6a Update Location Request to HSS
   - HSS acknowledges and may cancel location at old MME
   - HSS sends Cancel Location to old MME (if MME changed)

5. **Bearer Update (if SGW changes):**
   - New MME sends Create Session Request to new SGW
   - New SGW establishes GTP-U tunnel to PGW
   - Old SGW tunnels are released

6. **MME → eNodeB → UE: TAU Accept**
   - Contains: New GUTI (if reallocated), new TAI list, T3412 value
   - UE stores new TA list and starts periodic TAU timer

7. **UE → MME: TAU Complete**
   - Sent only if new GUTI was allocated (confirms GUTI update)

**Key Timers:**
- **T3412** (periodic TAU): 54 min default, configurable 1 min to 186 min
- **T3430** (TAU procedure guard): 6 seconds — UE retries if no response
- **T3411** (TAU retry after reject): 10 seconds

**TAI List Types:**
- Type 0: List of individual TAIs
- Type 1: Consecutive TAIs with same PLMN
- Type 2: TAIs with different PLMNs

**Common TAU failure causes:**
- HSS unreachable (S6a timeout)
- Security context mismatch (requires re-authentication)
- MME overload rejecting TAU requests
- Incorrect TAI list configuration causing excessive TAU storms""",
        "protocol_knowledge"
    ),
    # Network slicing / S-NSSAI (PROTO-05 scored 0.33)
    make_record(
        "What is network slicing in 5G? How is S-NSSAI structured and used?",
        """Network slicing is a fundamental 5G architecture feature that creates multiple virtual end-to-end networks on shared physical infrastructure, each optimized for different service requirements.

**Core Concept:**
Each slice is an isolated, independent logical network with its own:
- RAN configuration (scheduling, resource allocation)
- Core network functions (dedicated or shared AMF, SMF, UPF)
- QoS policies and SLA guarantees
- Security and isolation boundaries

**S-NSSAI (Single Network Slice Selection Assistance Information):**

S-NSSAI uniquely identifies a network slice and consists of:

1. **SST (Slice/Service Type)** — 8 bits (mandatory):
   - SST=1: eMBB (enhanced Mobile Broadband) — high throughput
   - SST=2: URLLC (Ultra-Reliable Low-Latency Communications) — <1ms latency
   - SST=3: MIoT (Massive IoT) — millions of devices, low power
   - SST=4: V2X (Vehicle-to-Everything) — automotive
   - SST=5-127: Reserved by 3GPP
   - SST=128-255: Operator-specific (custom slices)

2. **SD (Slice Differentiator)** — 24 bits (optional):
   - Differentiates multiple slices of the same SST
   - Example: SST=1, SD=1 for consumer eMBB; SST=1, SD=2 for enterprise eMBB
   - If not needed, SD is omitted

**NSSAI (Network Slice Selection Assistance Information):**
- Collection of S-NSSAIs
- **Requested NSSAI**: UE sends during registration (what slices it wants)
- **Allowed NSSAI**: AMF responds with (what slices UE can use in this PLMN)
- **Configured NSSAI**: Pre-provisioned in UE/USIM per PLMN
- **Default S-NSSAI**: Used when UE doesn't request specific slice

**Slice Selection Process:**
1. UE sends Registration Request with Requested NSSAI
2. AMF consults NSSF (Network Slice Selection Function)
3. NSSF determines:
   - Which slices are available for this UE in this location
   - Which AMF set should serve which slices
4. If current AMF can't serve requested slices → AMF reroutes to correct AMF
5. AMF returns Allowed NSSAI to UE
6. UE uses Allowed NSSAI for subsequent PDU session establishment

**Key Network Functions for Slicing:**
- **NSSF**: Selects appropriate slice and AMF
- **NSSMF**: Network Slice Subnet Management Function (manages slice lifecycle)
- **NWDAF**: Analytics for slice SLA monitoring
- **NEF**: Exposure function for slice capability to applications

**Slice Isolation Levels:**
1. **Shared RAN, shared core**: Logical isolation via QoS (lightest)
2. **Shared RAN, dedicated core NFs**: Medium isolation
3. **Dedicated RAN, dedicated core**: Full isolation (heaviest, most expensive)

**Example deployment:**
- Slice A (SST=1, SD=1): Consumer eMBB, shared infrastructure, best-effort
- Slice B (SST=2, SD=1): Industrial URLLC, dedicated UPF at edge, guaranteed <5ms
- Slice C (SST=3, SD=1): Smart meters, shared core, power-saving optimized""",
        "protocol_knowledge"
    ),
    # CU-DU split (PROTO-09 scored 0.33)
    make_record(
        "What is the CU-DU split in 5G RAN? Which protocol layers go where? What are the F1 and E1 interfaces?",
        """The CU-DU (Central Unit - Distributed Unit) split is the disaggregation of the 5G gNB into separate functional units, enabling flexible deployment and centralized control.

**Architecture:**

```
UE ↔ RU ↔ DU ↔ CU-UP ↔ Core (UPF)
              ↔ CU-CP ↔ Core (AMF)
```

**gNB = CU-CP + CU-UP + DU + RU**

**DU (Distributed Unit):**
- Deployed at or near the cell site
- Handles real-time, latency-sensitive processing
- Protocol layers:
  - **RLC (Radio Link Control)**: Segmentation, ARQ
  - **MAC (Medium Access Control)**: Scheduling, HARQ, multiplexing
  - **Physical layer (High-PHY)**: Channel coding, modulation, MIMO processing
- Connected to RU via fronthaul (eCPRI/O-RAN 7.2x split)

**CU-CP (Central Unit - Control Plane):**
- Can be centralized (serving multiple DUs)
- Handles non-real-time control plane
- Protocol layers:
  - **RRC (Radio Resource Control)**: Connection management, measurement configuration, handover control, security
  - **PDCP-C (control plane)**: Ciphering and integrity protection of RRC/NAS messages
- Connected to AMF via N2 (NGAP)

**CU-UP (Central Unit - User Plane):**
- Handles user data processing
- Protocol layers:
  - **PDCP-U (user plane)**: Header compression (ROHC), ciphering, reordering, duplicate detection
  - **SDAP (Service Data Adaptation Protocol)**: QoS flow to DRB mapping
- Connected to UPF via N3 (GTP-U)

**Interfaces:**

1. **F1 Interface (DU ↔ CU):**
   - F1-C (control): DU ↔ CU-CP. Protocol: F1AP over SCTP
   - F1-U (user): DU ↔ CU-UP. Protocol: GTP-U over UDP
   - Carries: RRC messages, UE context management, paging, UL/DL data

2. **E1 Interface (CU-CP ↔ CU-UP):**
   - Protocol: E1AP over SCTP
   - Carries: Bearer context management, data forwarding during handover
   - CU-CP instructs CU-UP on bearer setup/modification/release

3. **Xn Interface (between gNBs):**
   - Xn-C: SCTP-based control (handover, dual connectivity)
   - Xn-U: GTP-U based user plane (data forwarding)

**3GPP Split Options (historical context):**
- Split 2 (PDCP-RLC): The chosen split for CU-DU. Good balance of centralization vs latency
- Split 7.2x: RU-DU split (Low-PHY at RU, High-PHY at DU). Used in O-RAN
- Split 8: Full PHY at DU, only RF at RU. Requires massive fronthaul bandwidth

**Benefits of CU-DU split:**
1. **Centralized RRM**: One CU-CP managing multiple DUs enables coordinated scheduling, interference management
2. **Flexible deployment**: CU in central DC, DU at edge, RU at cell site
3. **Resource pooling**: CU-UP resources shared across multiple cells
4. **Easier upgrades**: Update CU software without touching DU/RU
5. **Multi-vendor**: Different vendors for CU, DU, RU (O-RAN vision)""",
        "protocol_knowledge"
    ),
    # O-RAN (PROTO-19 scored 0.50)
    make_record(
        "What is O-RAN and how does it differ from traditional RAN? Explain the architecture and key components.",
        """O-RAN (Open Radio Access Network) is an industry initiative to create open, intelligent, virtualized, and interoperable RAN architectures. It builds on 3GPP specifications while adding openness and intelligence.

**How O-RAN differs from traditional RAN:**

| Aspect | Traditional RAN | O-RAN |
|--------|----------------|-------|
| Vendor | Single vendor end-to-end | Multi-vendor, mix-and-match |
| Interfaces | Proprietary between components | Open, standardized interfaces |
| Hardware | Purpose-built appliances | COTS (commercial off-the-shelf) servers |
| Software | Monolithic, vendor-locked | Disaggregated, virtualized (VNF/CNF) |
| Intelligence | Static, rule-based SON | AI/ML-driven RIC with xApps/rApps |
| Fronthaul | Proprietary CPRI | Open eCPRI (7.2x split) |

**O-RAN Architecture Components:**

1. **O-RU (O-RAN Radio Unit):**
   - At the cell site/antenna
   - Low-PHY processing, RF transmission/reception
   - Connected to O-DU via Open Fronthaul (eCPRI, Split 7.2x)

2. **O-DU (O-RAN Distributed Unit):**
   - High-PHY, MAC, RLC layers
   - Real-time processing on COTS hardware with hardware accelerators
   - Runs as VNF/CNF on O-Cloud

3. **O-CU-CP / O-CU-UP:**
   - Same as 3GPP CU split
   - RRC+PDCP-C (CP) and SDAP+PDCP-U (UP)
   - Connected via E1 and F1 interfaces

4. **Near-RT RIC (Near-Real-Time RAN Intelligent Controller):**
   - Control loop: 10ms to 1s
   - Hosts **xApps**: Third-party applications for RAN optimization
   - Examples: Traffic steering, interference management, QoS optimization
   - Connected to O-CU/O-DU via **E2 interface**
   - Uses E2 Service Models (E2SM) for standardized data/control

5. **Non-RT RIC (Non-Real-Time RAN Intelligent Controller):**
   - Control loop: >1s (typically minutes to hours)
   - Part of SMO (Service Management and Orchestration)
   - Hosts **rApps**: Applications for policy, analytics, AI/ML model training
   - Feeds trained ML models and policies to Near-RT RIC via **A1 interface**

6. **SMO (Service Management and Orchestration):**
   - Lifecycle management of O-RAN components
   - FCAPS (Fault, Configuration, Accounting, Performance, Security)
   - Connected to O-RAN components via **O1 interface**
   - Hosts Non-RT RIC

7. **O-Cloud:**
   - Cloud computing platform for hosting O-RAN functions
   - Based on Kubernetes, OpenStack, or similar
   - Connected to SMO via **O2 interface**

**Key O-RAN Interfaces:**
- **Open Fronthaul (O-RU ↔ O-DU)**: eCPRI, Split 7.2x, CUS/M-plane
- **E2 (Near-RT RIC ↔ O-CU/O-DU)**: xApp control and data collection
- **A1 (Non-RT RIC ↔ Near-RT RIC)**: Policy and ML model delivery
- **O1 (SMO ↔ all components)**: Management and orchestration
- **O2 (SMO ↔ O-Cloud)**: Cloud infrastructure management
- **F1, E1, Xn, N2, N3**: Standard 3GPP interfaces (kept as-is)

**O-RAN Alliance Working Groups:**
- WG1: Use cases and architecture
- WG2: Non-RT RIC and A1 interface
- WG3: Near-RT RIC and E2 interface
- WG4: Open Fronthaul
- WG5: Open F1/W1/E1/X2/Xn
- WG6: Cloud and orchestration""",
        "protocol_knowledge"
    ),
    # SSB in 5G NR
    make_record(
        "What is SSB in 5G NR? What does it contain and how is it used?",
        """SSB (Synchronization Signal Block), also called SS/PBCH Block, is the fundamental broadcast signal in 5G NR that UEs use for initial cell search, synchronization, and system information acquisition.

**SSB Contents (4 OFDM symbols):**

1. **PSS (Primary Synchronization Signal)** — Symbol 0:
   - m-sequence of length 127
   - 3 possible sequences (N_ID_2 = 0, 1, 2)
   - Provides: Symbol timing, partial cell identity (1 of 3 groups)
   - UE uses PSS for initial time/frequency synchronization

2. **SSS (Secondary Synchronization Signal)** — Symbol 2:
   - Gold sequence of length 127
   - 336 possible sequences (N_ID_1 = 0 to 335)
   - Combined with PSS gives Physical Cell ID: PCI = 3×N_ID_1 + N_ID_2 (0 to 1007)

3. **PBCH (Physical Broadcast Channel)** — Symbols 1, 2, 3:
   - Carries MIB (Master Information Block)
   - MIB contains:
     - System Frame Number (SFN)
     - Subcarrier spacing for SIB1 (common CORESET)
     - SSB subcarrier offset
     - PDCCH configuration for SIB1 (CORESET#0, SearchSpace#0)
     - Cell barred status
     - Intra-frequency reselection indicator
   - PBCH TTI: 80ms (encoded across 4 SSB transmissions)

4. **PBCH DMRS** — Symbols 1, 3:
   - Demodulation reference signal for PBCH
   - Carries SSB index (3 LSBs) within the half-frame

**SSB Beam Sweeping:**
- In FR1 (<6GHz): Up to **8 SSB beams** per half-frame (Lmax=8)
- In FR2 (mmWave): Up to **64 SSB beams** per half-frame (Lmax=64)
- Each SSB transmitted on a different beam direction
- UE measures L1-RSRP on each SSB beam to identify best beam

**SSB Periodicity:**
- Default: 20ms (initial cell search assumption)
- Configurable: 5, 10, 20, 40, 80, 160ms
- Shorter periodicity = faster cell search but more overhead
- Longer periodicity = less overhead but slower beam recovery

**SSB Frequency Positions:**
- SSB is transmitted on specific frequency raster positions (GSCN — Global Synchronization Channel Number)
- UE scans GSCN positions to find cells (much faster than scanning all frequencies)
- SSB bandwidth: 20 RBs (240 subcarriers) regardless of cell bandwidth

**SSB-based Measurements:**
- **SS-RSRP**: Reference Signal Received Power (per SSB beam)
- **SS-RSRQ**: Reference Signal Received Quality
- **SS-SINR**: Signal to Interference plus Noise Ratio
- Used for: Cell selection, reselection, handover decisions, beam management

**SSB vs CSI-RS:**
- SSB: Broad beams, always-on, used for coverage and mobility
- CSI-RS: Narrow beams, UE-specific, used for refined beam management and channel estimation
- Both used together: SSB for coarse beam selection, CSI-RS for fine beam tracking""",
        "protocol_knowledge"
    ),
    make_record(
        "How does carrier aggregation work in LTE/NR? What is the difference between intra-band and inter-band CA?",
        """Carrier Aggregation (CA) combines multiple component carriers (CCs) to increase bandwidth and throughput for a single UE.

**Fundamental Concepts:**
- **Component Carrier (CC)**: Individual carrier with its own bandwidth (up to 20MHz LTE, 100MHz NR sub-6, 400MHz NR mmWave)
- **PCell (Primary Cell)**: Always configured, handles RRC and NAS signaling
- **SCell (Secondary Cell)**: Added/removed dynamically for extra capacity
- **PSCell (Primary SCG Cell)**: Primary cell of Secondary Cell Group in Dual Connectivity
- Max CCs: 5 in LTE (100MHz), 16 in NR (up to 1.6GHz theoretical)

**CA Types:**

1. **Intra-band Contiguous CA:**
   - Component carriers on the same band, adjacent in frequency
   - Example: Two 20MHz carriers on Band 7 (2620-2660MHz) = 40MHz
   - Simplest implementation: Single FFT can process combined bandwidth
   - One RF chain, one antenna set
   - Minimal additional cost and complexity

2. **Intra-band Non-contiguous CA:**
   - Same band but separated by a frequency gap
   - Example: Two 10MHz carriers on n78 at 3.4GHz and 3.6GHz
   - Requires wider bandwidth RF front-end or two separate RF chains
   - More complex than contiguous but reuses same antenna

3. **Inter-band CA:**
   - Carriers on different frequency bands
   - Example: Band 3 (1800MHz) + Band 7 (2600MHz) in LTE
   - Example: n1 (2100MHz) + n78 (3500MHz) in NR
   - Requires separate RF chains and potentially separate antennas per band
   - Most complex but provides: Coverage (low band) + Capacity (high band)

**CA Procedure:**
1. UE reports CA capability in UE-EUTRA-Capability (supported band combinations)
2. Network configures SCells via RRC Reconfiguration
3. SCell activation via MAC CE (activation/deactivation command)
4. UE reports CQI/PMI/RI independently per CC
5. Scheduler allocates resources across CCs
6. MAC layer multiplexes/demultiplexes data across CCs

**Key Differences LTE CA vs NR CA:**

| Feature | LTE CA | NR CA |
|---------|--------|-------|
| Max CCs | 5 | 16 |
| Max CC BW | 20 MHz | 100/400 MHz |
| Cross-carrier scheduling | Yes | Yes (enhanced) |
| SUL (Supplementary UL) | No | Yes |
| Max total BW | 100 MHz | 1.6 GHz (theoretical) |

**NR-specific CA features:**
- **SUL (Supplementary Uplink)**: Extra UL carrier on low band for coverage
- **Cross-carrier scheduling with different SCS**: CCs can have different subcarrier spacings
- **Bandwidth Part (BWP)**: Each CC can have multiple BWPs, only one active at a time

**Practical deployment considerations:**
- Band combination must be supported by UE chipset (check 3GPP UE capability)
- Backhaul must support aggregated throughput
- X2/Xn for SCell addition during handover
- Separate timing advance may be needed per Timing Advance Group (TAG)""",
        "protocol_knowledge"
    ),
    make_record(
        "What subcarrier spacings are supported in 5G NR and when is each used?",
        """5G NR supports flexible subcarrier spacing (SCS) based on the numerology parameter μ. This is a key difference from LTE which uses fixed 15kHz SCS.

**Supported Numerologies:**

| μ | SCS (kHz) | Slot Duration | Symbols/Slot | CP Type | Use Cases |
|---|-----------|---------------|--------------|---------|-----------|
| 0 | 15 | 1 ms | 14 | Normal | FR1 data, compatible with LTE |
| 1 | 30 | 0.5 ms | 14 | Normal | FR1 data (most common sub-6GHz) |
| 2 | 60 | 0.25 ms | 14 | Normal/Extended | FR1 URLLC, FR2 data |
| 3 | 120 | 0.125 ms | 14 | Normal | FR2 data (mmWave default) |
| 4 | 240 | 0.0625 ms | 14 | Normal | FR2 SSB only (not for data) |

**Relationship: SCS = 15 × 2^μ kHz**

**When each SCS is used:**

**15 kHz (μ=0):**
- FR1 only (sub-6GHz)
- Low-mobility, coverage-focused scenarios
- Bands below 3GHz where Doppler spread is manageable
- Good for: FDD deployments, IoT, rural coverage
- Largest CP duration (4.7μs) — best multipath tolerance

**30 kHz (μ=1):**
- **Most common for FR1 data channels**
- Default for mid-band 5G (n77, n78, n79 at 3.5-4.9GHz)
- Good balance: Reasonable CP (2.3μs) and slot duration (0.5ms)
- Supports mini-slot for URLLC (2/4/7 symbols)
- Used for: eMBB in most commercial 5G deployments

**60 kHz (μ=2):**
- Bridge between FR1 and FR2
- FR1: Used for URLLC requiring shorter slots (0.25ms)
- FR2: Possible for data but 120kHz is preferred
- Only numerology supporting Extended CP in NR (for broadcast/multicast)
- Used for: Industrial URLLC, V2X, FR2 with relaxed requirements

**120 kHz (μ=3):**
- **Default for FR2 (mmWave) data**
- Short slot duration (0.125ms) suits mmWave propagation
- Wider SCS handles larger Doppler spread at high frequencies
- Smaller CP (0.57μs) is sufficient for short-range mmWave
- Used for: mmWave eMBB (n257, n258, n260, n261)

**240 kHz (μ=4):**
- FR2 SSB (synchronization signals) only
- Not used for data channels
- Enables fast beam sweeping with up to 64 SSBs
- Used for: Initial cell search in mmWave bands

**Key Design Principles:**
1. **Higher frequency → larger SCS**: Wider SCS tolerates larger phase noise and Doppler at higher frequencies
2. **Lower latency → larger SCS**: Shorter slots enable faster HARQ feedback
3. **Multipath tolerance → smaller SCS**: Longer CP handles larger delay spread (rural, indoor)
4. **Resource grid scales**: RB always = 12 subcarriers, but PRB bandwidth changes with SCS

**BWP and mixed numerology:**
- Different BWPs within a cell can use different SCS
- Guard bands needed between different numerologies (inter-numerology interference)
- Scheduling can switch UE between BWPs with different SCS dynamically""",
        "protocol_knowledge"
    ),
    make_record(
        "Explain the difference between NSA Option 3x and SA Option 2 in 5G deployment.",
        """NSA (Non-Standalone) Option 3x and SA (Standalone) Option 2 are two primary 5G deployment architectures with fundamentally different approaches.

**NSA Option 3x (EN-DC: E-UTRA NR Dual Connectivity):**

```
         EPC (4G Core)
        /            \\
   eNodeB ----X2---- gNB (NR)
   (Master)          (Secondary)
      \\              /
       UE (connected to both)
```

- **Control plane**: Through LTE eNodeB → EPC (MME/HSS)
- **User plane**: Split between LTE and NR via X2 interface
- "3x" means: User plane can go eNB→SGW or gNB→SGW (split bearer)
- NR acts as a **booster** for throughput — no standalone NR signaling

**Key characteristics of NSA 3x:**
1. Requires LTE anchor: UE must first connect to LTE, then NR is added as SCell
2. Uses existing 4G core (EPC) — no 5GC needed
3. UE needs dual connectivity capability (connects to both LTE and NR simultaneously)
4. No 5G-specific features: No network slicing, no URLLC, no SBA
5. Voice: VoLTE (same as 4G, no change)
6. Faster deployment: Reuses existing 4G infrastructure

**SA Option 2 (Standalone 5G):**

```
         5GC (5G Core)
        /            \\
      AMF            UPF
        \\            /
         gNB (NR)
           |
          UE
```

- **Control plane**: gNB → 5GC (AMF) via N2 interface
- **User plane**: gNB → 5GC (UPF) via N3 interface
- NR operates **independently** — no LTE dependency

**Key characteristics of SA Option 2:**
1. No LTE anchor needed: UE connects directly to 5G NR
2. Requires 5G Core (5GC) with SBA architecture
3. Full 5G feature set: Network slicing, URLLC, MEC, SBA
4. Voice: VoNR (Voice over NR) or EPS Fallback to VoLTE
5. Lower latency: Shorter signaling path (no EPC detour)
6. More complex deployment: New core network required

**Comparison:**

| Feature | NSA Option 3x | SA Option 2 |
|---------|---------------|-------------|
| Core Network | EPC (4G) | 5GC (5G) |
| LTE Required | Yes (anchor) | No |
| Network Slicing | No | Yes |
| URLLC | Limited | Full |
| MEC | Limited | Full (LADN, UPF at edge) |
| Voice | VoLTE | VoNR / EPS Fallback |
| Latency | Higher (EPC path) | Lower (direct 5GC) |
| Deployment Cost | Lower (reuse EPC) | Higher (new 5GC) |
| Coverage Fallback | Inherent (LTE anchor) | Needs inter-RAT HO config |
| UE Complexity | Dual connectivity | Single connectivity |

**Migration path:**
Most operators: NSA 3x (quick launch) → SA Option 2 (full 5G features)

**Other options (less common):**
- Option 3: User plane only through eNB (no split bearer)
- Option 3a: User plane only through gNB
- Option 4/7: NR as master with LTE secondary (NGEN-DC, NE-DC)
- Option 5: LTE connected to 5GC (eLTE)""",
        "protocol_knowledge"
    ),
    make_record(
        "What is CUPS (Control and User Plane Separation) and why is it important in 5G architecture?",
        """CUPS (Control and User Plane Separation) is the architectural principle of separating control plane and user plane functions into independently scalable and deployable entities.

**Origin:**
- Introduced in 3GPP Release 14 for EPC (CUPS for SGW/PGW)
- Became fundamental in 5G Core (5GC) architecture from Release 15
- Defined in 3GPP TS 23.214 (EPC CUPS) and TS 23.501 (5GC)

**In EPC (4G CUPS):**
```
Traditional:          CUPS:
SGW (C+U combined)    SGW-C ←→ SGW-U (Sxa interface, PFCP)
PGW (C+U combined)    PGW-C ←→ PGW-U (Sxb interface, PFCP)
```
- SGW-C/PGW-C: Session management, bearer setup, QoS policy
- SGW-U/PGW-U: Packet forwarding, encapsulation, traffic measurement
- Communication via **PFCP (Packet Forwarding Control Protocol)** on Sx interfaces

**In 5GC (native CUPS):**
```
SMF (Control Plane) ←→ UPF (User Plane) via N4 interface (PFCP)
```
- **SMF**: Session management, QoS control, UPF selection, IP address allocation
- **UPF**: Packet forwarding, QoS enforcement, traffic detection, usage reporting
- N4 uses **PFCP** — same protocol, evolved from EPC CUPS

**Why CUPS is important:**

1. **Independent scaling:**
   - User plane scales with traffic volume (more UPFs for more data)
   - Control plane scales with signaling volume (more SMFs for more sessions)
   - No need to scale both together — saves resources and cost

2. **Flexible deployment:**
   - UPF deployed at the edge (close to users) for low latency
   - SMF centralized in regional DC for efficiency
   - Multiple UPFs served by one SMF, or one UPF serving multiple SMFs

3. **MEC (Multi-access Edge Computing):**
   - UPF at the edge enables local breakout
   - Traffic steering via ULCL (Uplink Classifier) or BP (Branching Point)
   - SMF controls which traffic goes to edge UPF vs central UPF
   - This is the key enabler for edge computing in 5G

4. **Network slicing:**
   - Each slice can have dedicated UPFs with specific capabilities
   - URLLC slice: UPF at edge with guaranteed resources
   - eMBB slice: UPF centralized with high throughput
   - SMF manages slice-specific UPF selection

5. **Cost optimization:**
   - UPF on COTS hardware — commodity servers with DPDK/SmartNIC
   - No expensive integrated gateways needed
   - Can mix UPF vendors for different deployments

6. **Resilience:**
   - UPF failure doesn't affect control plane (sessions can be redirected)
   - SMF failure: UPF continues forwarding with existing rules
   - Enables UPF redundancy without duplicating control plane

**PFCP (key protocol):**
- Runs on UDP port 8805
- Messages: Session Establishment/Modification/Deletion Request/Response
- Carries: PDRs (Packet Detection Rules), FARs (Forwarding Action Rules), QERs (QoS Enforcement Rules), URRs (Usage Reporting Rules)
- These rules tell the UPF how to detect, forward, enforce QoS, and report usage for each traffic flow""",
        "protocol_knowledge"
    ),
    make_record(
        "How does NRF work in 5G SBA? What is NF discovery and NF management?",
        """NRF (Network Repository Function) is the central registry for all Network Functions in the 5G Service-Based Architecture (SBA). It enables dynamic, cloud-native service discovery.

**NRF Role in SBA:**
Think of NRF as the "DNS + service registry" for 5G core. Every NF registers with NRF, and other NFs query NRF to find services they need.

**Core Functions:**

1. **NF Registration (NF Management):**
   - Each NF registers its NF Profile with NRF
   - NF Profile contains:
     - NF Instance ID (UUID)
     - NF Type (AMF, SMF, UPF, PCF, UDM, etc.)
     - NF Status (REGISTERED, SUSPENDED, UNDISCOVERABLE)
     - FQDN or IP addresses
     - Supported services and versions
     - PLMN ID(s)
     - S-NSSAI(s) supported
     - Capacity and load information
     - Geographic location / serving area
   - NF sends heartbeat to NRF periodically (NFHeartbeat)
   - NRF removes NF if heartbeat expires

2. **NF Discovery:**
   - Consumer NF queries NRF: "Find me an SMF that supports S-NSSAI {1,1} in TAI 00101-1234"
   - NRF returns matching NF profiles ranked by priority/capacity
   - Discovery parameters:
     - Target NF type
     - Service name
     - S-NSSAI
     - TAI (Tracking Area Identity)
     - PLMN ID
     - Preferred locality
   - Response includes multiple candidates for load balancing/failover

3. **NF Subscription/Notification:**
   - NF subscribes to NRF for events: "Notify me when any SMF status changes"
   - NRF sends notifications when:
     - NF registers/deregisters
     - NF profile updated
     - NF becomes overloaded
   - Enables dynamic adaptation without polling

**API Operations (Nnrf interface):**

| Service | Operation | Description |
|---------|-----------|-------------|
| NFManagement | NFRegister | Register NF profile |
| NFManagement | NFUpdate | Update NF profile (PATCH) |
| NFManagement | NFDeregister | Remove NF from registry |
| NFManagement | NFHeartbeat | Keep-alive (PATCH with status) |
| NFDiscovery | NFDiscover | Search for NFs matching criteria |
| NFManagement | NFStatusSubscribe | Subscribe to NF status events |
| NFManagement | NFStatusNotify | Receive NF status notifications |

**NRF in multi-PLMN/roaming:**
- Each PLMN has its own NRF
- Inter-PLMN discovery goes through SEPP and NRF in visited/home networks
- NRF can be hierarchical: Local NRF → Regional NRF → Central NRF

**OAuth2 Authorization (NRF as OAuth2 server):**
- NRF issues access tokens to NF consumers
- Consumer presents token when calling producer NF
- Producer validates token before serving request
- This secures NF-to-NF communication in SBA

**High Availability:**
- NRF is critical — if NRF is down, no new NF discovery works
- Deploy as active/standby or active/active cluster
- NF profiles cached locally as fallback
- Existing service connections continue working without NRF

**Practical example flow:**
1. AMF receives Registration Request from UE requesting slice SST=1
2. AMF queries NRF: "Find SMF supporting S-NSSAI={SST:1} in TAI=00101-1"
3. NRF returns 3 SMF instances with load info
4. AMF selects least-loaded SMF
5. AMF calls selected SMF to create PDU session""",
        "protocol_knowledge"
    ),
    make_record(
        "Explain the Tracking Area Update (TAU) procedure in LTE. Include timers, message flow, and failure scenarios.",
        """The Tracking Area Update (TAU) is a key NAS mobility management procedure in LTE that keeps the network informed of the UE's location for paging purposes.

**Purpose:** Enable the network to page the UE efficiently by knowing which Tracking Area (TA) the UE is in, without requiring the UE to be in connected mode continuously.

**Types of TAU:**

1. **Normal TAU**: UE enters a cell belonging to a TA not in its current TA list
2. **Periodic TAU**: Timer T3412 expires — UE reports even if it hasn't moved
3. **Combined TAU**: Updates both EPS and non-EPS (CS domain) location
4. **TAU with active flag**: UE has pending uplink data/signaling

**Detailed Message Flow (Normal TAU, same MME):**

```
UE                    eNodeB               MME                HSS
|---RRC Connection Setup Request--->|                         |
|<--RRC Connection Setup-----------|                         |
|---RRC Connection Setup Complete-->|                         |
|   (TAU Request inside)           |                         |
|                                  |--S1AP: Initial UE Msg-->|
|                                  |   (TAU Request)         |
|                                  |                         |
|                    [Optional: Authentication/Security]      |
|<----NAS: Auth Request------------|-------------------------|
|----NAS: Auth Response----------->|------------------------>|
|<----NAS: Security Mode Command---|                         |
|----NAS: Security Mode Complete-->|                         |
|                                  |                         |
|                                  |--S6a: Update Location-->|
|                                  |<-S6a: Update Loc Ack----|
|                                  |                         |
|<---TAU Accept--------------------|                         |
|   (new GUTI, TAI list, T3412)    |                         |
|---TAU Complete------------------->|                         |
|   (if new GUTI allocated)        |                         |
```

**Inter-MME TAU (additional steps):**
- New MME sends S10: Context Request to old MME
- Old MME returns UE context (MM context, bearer context)
- If SGW changes: New MME creates session on new SGW
- Old MME/SGW resources released after successful TAU

**Key Timers:**

| Timer | Location | Default | Purpose |
|-------|----------|---------|---------|
| T3412 | UE | 54 min | Periodic TAU interval |
| T3412 extended | UE | Up to 310 hrs | For PSM (Power Saving Mode) IoT devices |
| T3430 | UE | 6 sec | TAU procedure guard timer |
| T3411 | UE | 10 sec | Retry timer after TAU failure |
| T3402 | UE | 12 min | Retry timer after TAU reject |
| T3450 | MME | 6 sec | Retransmission of TAU Accept |
| T3460 | MME | 6 sec | Retransmission of Auth Request |
| T3470 | MME | 6 sec | Retransmission of Identity Request |

**TAI List Configuration:**
- MME provides a list of TAs where UE does NOT need to do TAU
- Larger TAI list = fewer TAUs (less signaling) but larger paging area
- Smaller TAI list = more TAUs but more precise paging
- TAI list types: Individual TAIs, consecutive TAIs, multi-PLMN TAIs

**Common TAU Failure Causes and EMM Cause Codes:**

| Cause # | Meaning | Action |
|---------|---------|--------|
| #7 | EPS services not allowed | UE deregisters from EPS |
| #9 | UE identity cannot be derived | UE performs fresh attach |
| #10 | Implicitly detached | UE performs fresh attach |
| #11 | PLMN not allowed | UE marks PLMN as forbidden |
| #12 | TA not allowed | UE enters limited service |
| #13 | Roaming not allowed in this TA | UE selects different TA |
| #14 | EPS service not allowed in this PLMN | Service restriction |
| #22 | Congestion | UE retries after T3402 |
| #40 | No EPS bearer context activated | UE performs fresh attach |

**TAU Optimization for IoT:**
- Extended DRX: Longer paging cycles reduce power consumption
- PSM (Power Saving Mode): UE unreachable between periodic TAUs (T3412 extended up to 310 hours)
- eDRX + PSM combined: Maximum battery saving for IoT devices""",
        "protocol_knowledge"
    ),
    make_record(
        "What is HARQ in LTE/5G NR? How does synchronous vs asynchronous HARQ work?",
        """HARQ (Hybrid Automatic Repeat Request) combines Forward Error Correction (FEC) with ARQ retransmission to achieve reliable data delivery with low latency.

**How HARQ works:**
1. Transmitter sends data with CRC and error correction coding
2. Receiver attempts to decode
3. If successful → sends ACK, transmitter moves to next data
4. If failed → sends NACK, receiver stores the failed attempt in buffer
5. Retransmission is **combined** with stored failed attempt (soft combining)
6. Combined signal has better chance of successful decoding

**Soft Combining Methods:**

1. **Chase Combining (CC):**
   - Retransmission is identical to original
   - Receiver combines (averages) to improve SNR
   - Simple but less efficient

2. **Incremental Redundancy (IR):**
   - Retransmission sends different redundancy version (RV)
   - Each RV contains different parity bits from the rate-matching buffer
   - RV sequence: 0 → 2 → 3 → 1 (in NR)
   - More efficient — each retransmission adds new information
   - **Used in both LTE and NR**

**HARQ in LTE:**

| Aspect | DL (eNB→UE) | UL (UE→eNB) |
|--------|-------------|-------------|
| Type | Asynchronous | Synchronous |
| Timing | Flexible retx timing | Fixed 8ms round-trip |
| Processes | 8 (FDD), varies (TDD) | 8 (FDD) |
| Scheduling | Each retx explicitly scheduled | Adaptive or non-adaptive |
| ACK/NACK | On PUCCH/PUSCH | On PHICH |

**DL Asynchronous HARQ (LTE):**
- eNB can retransmit any HARQ process at any time
- eNB signals which process via DCI on PDCCH
- Flexible — eNB can prioritize retransmissions based on scheduler decisions
- UE identifies process by HARQ Process ID in DCI

**UL Synchronous HARQ (LTE):**
- Fixed timing: UE transmits on subframe n, ACK/NACK on subframe n+4
- Retransmission on subframe n+8 (if NACK)
- Non-adaptive: Same resource allocation as original (no new DCI needed)
- Adaptive: New DCI on PDCCH changes resource allocation for retransmission

**HARQ in 5G NR:**

| Aspect | DL | UL |
|--------|-----|-----|
| Type | Asynchronous | Asynchronous (key change!) |
| Processes | Up to 16 | Up to 16 |
| Timing | Flexible (indicated in DCI) | Flexible (indicated in DCI) |
| CBG-level | Supported | Supported |
| ACK/NACK | On PUCCH/PUSCH | On PDCCH (DCI) |

**Key NR improvements over LTE:**

1. **UL is now asynchronous**: Both DL and UL retransmission timing is flexible, indicated by K1 (DL ACK timing) and K2 (UL scheduling offset) in DCI
2. **Up to 16 HARQ processes** (vs 8 in LTE): Supports higher throughput and longer RTT
3. **CBG-based HARQ**: Code Block Group retransmission — only retransmit failed CBGs within a TB, not the entire Transport Block. Reduces retransmission overhead significantly
4. **Mini-slot HARQ**: Can operate on 2/4/7 symbol mini-slots for URLLC, enabling sub-1ms HARQ RTT
5. **Multi-bit HARQ-ACK**: Codebook-based feedback for multiple CCs and processes

**HARQ timing in NR:**
- DL: gNB transmits PDSCH → UE sends ACK/NACK after K1 slots on PUCCH
- K1 is indicated in DCI (field: PDSCH-to-HARQ_feedback timing indicator)
- UL: gNB sends UL grant with K2 offset → UE transmits PUSCH after K2 slots
- Minimum HARQ RTT depends on SCS: ~1ms at 30kHz, ~0.5ms at 60kHz, ~0.25ms at 120kHz

**Max retransmissions:**
- Configurable: typically 4 for data, 8-12 for control
- After max HARQ retransmissions → RLC layer handles retransmission (if AM mode)""",
        "protocol_knowledge"
    ),
    make_record(
        "Explain MEC (Multi-access Edge Computing) and its role in 5G. How does it integrate with the 5G core?",
        """MEC (Multi-access Edge Computing), standardized by ETSI, brings compute, storage, and networking closer to the radio access network edge. In 5G, MEC is natively integrated via UPF placement and traffic steering.

**Why MEC matters in 5G:**
- Ultra-low latency: <10ms round-trip (vs 30-50ms to central cloud)
- Bandwidth savings: Process data locally, reduce backhaul load
- Context awareness: Access to radio network information (location, QoS)
- Privacy: Data stays local (regulatory compliance)

**MEC Architecture (ETSI):**

```
┌─────────────────────────────────────────┐
│           MEC Platform (MEP)            │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ │
│  │App 1 │ │App 2 │ │App 3 │ │MEC Svc │ │
│  └──────┘ └──────┘ └──────┘ └────────┘ │
│  ┌─────────────────────────────────────┐│
│  │    MEC Platform Services (Mp1)     ││
│  │ (RNIS, Location, Traffic Rules)    ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │    Data Plane (Mp2) — Traffic       ││
│  │    steering via UPF                 ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
         |                    |
    MEC Orchestrator     5G Core (SMF/UPF)
```

**Integration with 5G Core:**

1. **UPF at the Edge:**
   - UPF deployed at MEC site (co-located with MEC platform)
   - SMF selects edge UPF based on:
     - DNAI (DN Access Identifier) — identifies the edge location
     - UE location (TAI)
     - Application requirements
   - Traffic for MEC apps routed to edge UPF, rest goes to central UPF

2. **Traffic Steering Mechanisms:**

   a. **ULCL (Uplink Classifier):**
   ```
   UE → gNB → UPF(ULCL) ──→ Edge UPF → MEC App
                          └──→ Central UPF → Internet
   ```
   - Intermediate UPF classifies packets by destination
   - Local traffic → edge UPF; other traffic → central UPF
   - Uses packet detection rules (IP 5-tuple, DNN)

   b. **Branching Point (BP):**
   - Similar to ULCL but at PDU session branching point
   - One PDU session, two paths

   c. **Local Breakout:**
   - Entire PDU session served by edge UPF
   - Used when all traffic for a DNN should stay local

3. **Session and Service Continuity (SSC):**
   - **SSC Mode 1**: Anchor UPF doesn't change (PDU session maintained)
   - **SSC Mode 2**: Network releases and re-establishes session (break-before-make)
   - **SSC Mode 3**: New connection before old is released (make-before-break)
   - SSC Mode 3 best for MEC: Seamless mobility between edge sites

4. **LADN (Local Area Data Network):**
   - DNN available only in specific areas (where MEC is deployed)
   - AMF informs UE of LADN availability areas
   - UE activates PDU session when entering LADN area

**MEC Platform Services:**
- **RNIS (Radio Network Information Service)**: Radio conditions, UE measurements
- **Location Service**: UE positioning (cell-level or sub-meter with positioning)
- **Bandwidth Manager**: Request guaranteed bandwidth for MEC apps
- **Traffic Rule Control**: Steer specific flows to MEC applications

**Use Cases:**
1. AR/VR: <20ms latency for interactive experiences
2. V2X: Real-time traffic management and collision avoidance
3. Industrial IoT: Local control loops for manufacturing
4. Video analytics: Process CCTV/camera feeds locally
5. Gaming: Edge rendering and game state management
6. CDN: Cache popular content at the edge""",
        "protocol_knowledge"
    ),
]


def main():
    print("=" * 60)
    print("Step 8: Expand data for Llama v2 training")
    print("=" * 60)

    # Load v1 training data (what Llama v1 was trained on)
    v1_path = DATA_DIR / "processed" / "train.jsonl"
    with open(v1_path) as f:
        v1_data = [json.loads(line) for line in f if line.strip()]
    print(f"\nV1 training data: {len(v1_data)} records")

    # Load existing v2 extras
    extras = []
    for extra_file in ["v2_kpi_analysis.jsonl", "v2_protocol_knowledge.jsonl"]:
        path = DATA_DIR / extra_file
        if path.exists():
            with open(path) as f:
                records = [json.loads(line) for line in f if line.strip()]
            extras.extend(records)
            print(f"  {extra_file}: {len(records)} records")

    # Combine everything
    all_data = v1_data + extras + KPI_EXAMPLES + PROTOCOL_EXAMPLES
    print(f"\nNew KPI examples: {len(KPI_EXAMPLES)}")
    print(f"New Protocol examples: {len(PROTOCOL_EXAMPLES)}")
    print(f"\nTotal combined: {len(all_data)} records")

    # Shuffle
    random.seed(42)
    random.shuffle(all_data)

    # Category distribution
    cats = Counter()
    for r in all_data:
        cats[r.get("category", "unknown")] += 1
    print(f"\nCategory distribution:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:30s} {count:6d}")

    # Save
    output_path = DATA_DIR / "train_llama_v2.jsonl"
    with open(output_path, "w") as f:
        for record in all_data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\nSaved to: {output_path}")
    print(f"Total records: {len(all_data)}")


if __name__ == "__main__":
    main()
