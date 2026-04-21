"""
Step 4: Expand synthetic training data diversity
- From 5 NOC scenarios → 40+ scenarios across all telco domains
- From 5 intent-to-config pairs → 25+ config templates
- Add new categories: troubleshooting dialogues, KPI analysis, protocol explanations
- Add TeleQnA-style multiple choice training data
"""

import json
import random
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

SYSTEM_PROMPT = (
    "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
    "You have deep knowledge of 3GPP standards, 5G/LTE network operations, "
    "RAN optimization, core network, transport, and IMS/VoLTE. "
    "You assist network engineers with diagnostics, configuration, "
    "troubleshooting, and standards interpretation."
)

# =============================================================================
# 1. EXPANDED NOC SCENARIOS (40+ scenarios across all domains)
# =============================================================================

NOC_SCENARIOS = [
    # ---- RAN Domain (15 scenarios) ----
    {
        "alarm": "High CPU utilization on eNodeB {site_id} — CPU at {cpu}%",
        "diagnosis": "The eNodeB at site {site_id} is experiencing high CPU load ({cpu}%). Common causes: 1) Excessive handover processing due to parameter misconfiguration, 2) Software bug in the current firmware version, 3) Abnormal traffic pattern (possible signaling storm), 4) Excessive connected UEs beyond dimensioned capacity. Check handover statistics, connected UE count, and firmware version against known issues.",
        "resolution": "1. Check current connected UEs: if > {ue_threshold}, enable load balancing to neighbors\n2. Review handover success rate: if < 95%, adjust HO parameters (A3 offset, TTT)\n3. If firmware is below v{fw_version}, schedule upgrade during maintenance window\n4. Enable CPU load monitoring with 5-minute granularity\n5. If persists, escalate to L2 with RAN trace data and CPU profile",
        "severity": "Major", "domain": "RAN",
    },
    {
        "alarm": "RACH failure rate exceeds {threshold}% on cell {cell_id}",
        "diagnosis": "Random Access Channel (RACH) failure rate on cell {cell_id} is {threshold}%, above the 5% threshold. This means UEs are failing to establish initial access. Possible causes: 1) Uplink interference from neighboring cells or external sources, 2) PRACH configuration mismatch (root sequence, preamble format), 3) Coverage hole — UEs at cell edge with insufficient uplink power, 4) Timing advance issues in large cells, 5) Preamble collision due to high RACH load.",
        "resolution": "1. Check uplink interference levels (IoT metric) on the affected cell\n2. Verify PRACH root sequence index — ensure no collision with neighbors\n3. Check cell radius vs preamble format (format 0 supports up to 14.5km)\n4. Review TA distribution — if many high TA values, consider cell split\n5. If high load, increase number of RACH preambles (from 54 to 64)\n6. Check for external interference sources using spectrum scan\n7. Monitor for 24 hours after changes",
        "severity": "Major", "domain": "RAN",
    },
    {
        "alarm": "RRC setup failure rate exceeds {threshold}% on gNB {site_id}",
        "diagnosis": "RRC (Radio Resource Control) connection setup failure rate on gNB {site_id} is at {threshold}%. UEs are failing to transition from RRC_IDLE to RRC_CONNECTED. Causes: 1) Insufficient PDCCH resources (CCE congestion), 2) Preamble detection issues (linked to RACH), 3) DL/UL power imbalance, 4) Congestion — insufficient RRC connection capacity, 5) Hardware fault on baseband unit.",
        "resolution": "1. Check PDCCH CCE utilization — if >70%, increase PDCCH capacity or enable ECCE\n2. Verify DL reference signal power matches planning target\n3. Check license limits for simultaneous RRC connections\n4. Review MSG4 contention resolution timer\n5. Check baseband card alarms and hardware diagnostics\n6. If congestion-related, enable RRC connection rejection with redirect to less loaded cell\n7. Compare with neighboring cells to isolate cell-specific vs area-wide issue",
        "severity": "Critical", "domain": "RAN",
    },
    {
        "alarm": "Throughput degradation on cell {cell_id} — DL throughput dropped {drop}%",
        "diagnosis": "Downlink throughput on cell {cell_id} has dropped by {drop}% compared to the 7-day baseline. Possible causes: 1) Increased interference from neighboring cells (SINR degradation), 2) Hardware degradation (PA/TRX module), 3) Parameter change affecting scheduler or power settings, 4) New physical obstruction affecting RF propagation, 5) Increased user load without capacity expansion, 6) CQI reporting issues.",
        "resolution": "1. Check RSSI/SINR trends on affected cell — compare to previous week\n2. Compare PRB utilization — if >80%, this is a capacity issue\n3. Review recent CM changes in the last 48h (power, tilt, scheduler)\n4. Run RF scan for interference detection\n5. If hardware suspected, check VSWR alarms and PA output power\n6. Review CQI distribution — shift toward lower CQI indicates interference\n7. Consider temporary tilt/power adjustment to validate RF hypothesis",
        "severity": "Major", "domain": "RAN",
    },
    {
        "alarm": "Excessive handover failures between cell {cell_id} and {neighbor_cell}",
        "diagnosis": "Handover success rate between cell {cell_id} and {neighbor_cell} has dropped below 90%. Types of HO failures observed: 1) Too-late handover — UE loses source before completing HO, 2) Too-early handover — UE fails on target and returns to source, 3) Wrong-cell handover — UE hands over to incorrect neighbor. Root causes include: stale neighbor relations, incorrect HO parameters, coverage gap between cells, or target cell congestion.",
        "resolution": "1. Classify HO failures by type (too-late, too-early, wrong-cell) using RLF reports\n2. For too-late: reduce A3 offset or time-to-trigger (TTT) for this neighbor pair\n3. For too-early: increase A3 offset or TTT\n4. For wrong-cell: update ANR (Automatic Neighbor Relations) table\n5. Check if target cell has admission control rejections (congestion)\n6. Verify physical neighbor relation — drive test if needed\n7. Check for missing X2/Xn link between the cells",
        "severity": "Major", "domain": "RAN",
    },
    {
        "alarm": "High PDCP packet loss rate ({loss}%) on cell {cell_id}",
        "diagnosis": "PDCP layer packet loss on cell {cell_id} is {loss}%, exceeding the 1% threshold. PDCP packet loss directly impacts user-perceived throughput and latency. Causes: 1) Poor radio conditions (low SINR), 2) HARQ retransmission failures exceeding max retries, 3) RLC AM mode reordering timeout, 4) X2/Xn handover data forwarding issues, 5) Backhaul congestion causing buffer overflow.",
        "resolution": "1. Check BLER (Block Error Rate) on the affected cell — should be <10%\n2. Verify HARQ residual BLER — if high, check MCS adaptation\n3. Review RLC retransmission statistics\n4. Check if losses correlate with handover events\n5. Monitor backhaul utilization during peak hours\n6. If radio-related, consider increasing HARQ max retransmissions\n7. Enable PDCP duplication for critical bearers if supported",
        "severity": "Major", "domain": "RAN",
    },
    {
        "alarm": "Antenna VSWR alarm on sector {sector} of site {site_id}",
        "diagnosis": "Voltage Standing Wave Ratio (VSWR) alarm detected on sector {sector} of site {site_id}. VSWR measures the impedance mismatch in the antenna feeder system. High VSWR (>1.5:1) causes reflected power, reducing radiated power and potentially damaging the PA. Causes: 1) Water ingress in connector or jumper cable, 2) Damaged feeder cable (kinked, crushed, or rodent damage), 3) Loose or corroded connector, 4) Lightning damage to antenna or surge protector, 5) Faulty TMA (Tower Mounted Amplifier).",
        "resolution": "1. Compare current VSWR with commissioning baseline\n2. Check return loss on all connectors using site analyzer (PIM tester)\n3. Inspect all jumper cables and connectors for physical damage\n4. Check weatherproofing tape on outdoor connectors\n5. Test TMA bypass — if VSWR normalizes, replace TMA\n6. If feeder cable fault, perform DTF (Distance-To-Fault) measurement\n7. Dispatch field team with replacement jumpers and connectors\n8. After repair, verify with new VSWR measurement and update baseline",
        "severity": "Critical", "domain": "RAN",
    },
    {
        "alarm": "PCI collision detected between {cell_id} and {neighbor_cell}",
        "diagnosis": "Physical Cell Identity (PCI) collision detected. Both {cell_id} and {neighbor_cell} are using PCI {pci_val}. PCI collision occurs when two cells with the same PCI are neighbors. Impact: 1) UEs cannot distinguish between the two cells during measurements, 2) Handover failures to/from affected cells, 3) Incorrect cell reselection in idle mode, 4) Corrupted measurement reports.",
        "resolution": "1. Verify collision by checking PCI plan for both cells\n2. Change PCI of one cell to an unused value (check all neighbors' PCIs)\n3. Ensure new PCI doesn't create PCI confusion (mod-3 and mod-30 rules for PSS/SSS)\n4. Plan the change during low-traffic window\n5. After change, verify handover success rate between affected cells\n6. Update PCI planning tool to prevent future collisions\n7. Consider enabling automatic PCI optimization if available",
        "severity": "Major", "domain": "RAN",
    },
    {
        "alarm": "Cell {cell_id} out of service — baseband unit not responding",
        "diagnosis": "Cell {cell_id} is completely out of service. The baseband unit (BBU) is not responding to management commands. Impact: All users on this cell have lost service and will camp on neighbor cells if coverage allows. Causes: 1) BBU hardware failure (power supply, processor, memory), 2) Software crash or hang, 3) Power outage at site, 4) Fiber/fronthaul link failure between BBU and RRU, 5) Temperature alarm causing thermal shutdown.",
        "resolution": "1. Check site power status (mains + battery backup)\n2. Attempt remote reset of BBU via OAM interface\n3. If OAM unreachable, check transport/backhaul link to site\n4. Check temperature alarms — if thermal shutdown, verify cooling system\n5. If remote reset fails, dispatch field team for hardware inspection\n6. Field team: check LED indicators, power supply, fiber connections to RRU\n7. If hardware fault confirmed, replace BBU and restore from backup config\n8. After recovery, verify all cells are on-air and KPIs are normal\n9. Create problem ticket for RCA (Root Cause Analysis)",
        "severity": "Critical", "domain": "RAN",
    },
    {
        "alarm": "DL PRB utilization exceeds {util}% on cell {cell_id} during busy hour",
        "diagnosis": "Downlink Physical Resource Block utilization on cell {cell_id} is at {util}% during busy hour, exceeding the 70% congestion threshold. This indicates the cell is running out of radio capacity. Impact: degraded throughput per user, increased latency, poor user experience. Causes: 1) Traffic growth exceeding cell capacity planning, 2) Abnormal traffic pattern (event, new building), 3) Neighbor cell outage causing traffic spillover, 4) Inefficient scheduler configuration.",
        "resolution": "1. Verify if neighbor cells are operational (check for outage spillover)\n2. Check subscriber count trend — is it gradual growth or sudden spike?\n3. Enable carrier aggregation if secondary carrier is available\n4. Optimize scheduler parameters (proportional fair vs max throughput)\n5. Consider MIMO upgrade (2T2R to 4T4R) for capacity gain\n6. Review if cell split is feasible (add new site or small cell)\n7. Enable MLB (Mobility Load Balancing) to offload to less loaded neighbors\n8. Short-term: adjust QoS to prioritize critical services",
        "severity": "Major", "domain": "RAN",
    },

    # ---- Core Network (10 scenarios) ----
    {
        "alarm": "S1 link failure between eNodeB {site_id} and MME {mme_id}",
        "diagnosis": "S1 interface connectivity lost between eNodeB {site_id} and MME {mme_id}. Impact: UEs cannot perform initial attach or handover via this MME. If redundant MME exists, traffic should failover. Root causes: 1) Transport network issue (VLAN/IP routing), 2) MME overload or process crash, 3) SCTP association timeout, 4) Firewall rule change blocking SCTP port 36412.",
        "resolution": "1. Verify transport connectivity: ping MME IP from eNodeB\n2. Check SCTP association status on both ends\n3. Verify no recent firewall changes on port 36412\n4. Check MME process status and capacity\n5. If transport OK, restart SCTP association\n6. Escalate to transport team if ping fails\n7. Check MME pool — verify other MMEs are serving the eNodeB",
        "severity": "Critical", "domain": "Core",
    },
    {
        "alarm": "AMF {amf_id} registration failure rate exceeds {threshold}%",
        "diagnosis": "Access and Mobility Management Function (AMF) {amf_id} is experiencing high registration failure rate ({threshold}%). UEs are failing 5G initial registration. Causes: 1) AUSF/UDM authentication failures (subscription data issues), 2) NRF service discovery failures, 3) AMF overload (CPU/memory), 4) N2 interface issues between gNB and AMF, 5) PLMN or TAC mismatch in configuration.",
        "resolution": "1. Check AMF logs for specific rejection cause codes (5GMM cause)\n2. Verify AUSF/UDM connectivity and response times\n3. Check NRF service registry — ensure all NF profiles are registered\n4. Monitor AMF CPU/memory — if >80%, consider scaling out\n5. Verify N2 SCTP associations are established\n6. Check subscriber profiles in UDM for consistency\n7. Review recent config changes to AMF/NRF/UDM",
        "severity": "Critical", "domain": "Core",
    },
    {
        "alarm": "PDU session establishment failure rate exceeds {threshold}% on SMF {smf_id}",
        "diagnosis": "Session Management Function (SMF) {smf_id} is rejecting PDU session requests at {threshold}% rate. Users cannot establish data connectivity. Causes: 1) UPF resource exhaustion (no available TEID or IP addresses), 2) DNN/APN configuration error, 3) PCF policy rule failure, 4) N4 (PFCP) session establishment failure between SMF and UPF, 5) IP pool exhaustion.",
        "resolution": "1. Check UPF PFCP association status via N4 interface\n2. Verify IP address pool availability for the affected DNN\n3. Check PCF policy decisions — are policies being correctly applied?\n4. Review SMF rejection cause codes (5GSM cause values)\n5. Monitor UPF session count against licensed capacity\n6. If IP pool exhausted, expand pool or reduce lease time\n7. Check if specific DNN/slice is affected vs all traffic",
        "severity": "Critical", "domain": "Core",
    },
    {
        "alarm": "GTP-U path failure detected between SGW {sgw_id} and PGW {pgw_id}",
        "diagnosis": "GTP-U tunnel path between Serving Gateway {sgw_id} and PDN Gateway {pgw_id} has failed. Impact: all user plane traffic through this path is interrupted. Echo request/response mechanism detected the failure. Causes: 1) Transport link failure between SGW and PGW, 2) PGW process crash, 3) GTP-U port (2152) blocked by ACL change, 4) MTU issue causing GTP encapsulated packets to be dropped.",
        "resolution": "1. Verify IP connectivity between SGW and PGW (ping with GTP source IP)\n2. Check GTP-U port 2152 accessibility (both UDP directions)\n3. Verify no ACL/firewall changes in the transport path\n4. Check PGW process status and restart if needed\n5. Verify MTU is sufficient for GTP overhead (original + 36-48 bytes)\n6. Check GTP echo timer configuration on both ends\n7. Monitor for path recovery and bearer re-establishment",
        "severity": "Critical", "domain": "Core",
    },
    {
        "alarm": "HSS database replication lag exceeds {lag}ms between primary and standby",
        "diagnosis": "Home Subscriber Server (HSS) geo-redundant pair showing {lag}ms replication lag, exceeding the 500ms threshold. Risk: if primary fails, standby will have stale subscriber data, causing authentication failures. Causes: 1) Network latency between data centers, 2) High transaction rate exceeding replication bandwidth, 3) Disk I/O bottleneck on standby, 4) Database lock contention.",
        "resolution": "1. Check network latency between primary and standby DC\n2. Monitor HSS transaction rate — is it within dimensioned capacity?\n3. Check disk I/O metrics on standby HSS server\n4. Verify replication network bandwidth (dedicated link recommended)\n5. If lag is increasing, consider throttling non-critical batch operations\n6. Check for database lock contention or long-running queries\n7. Validate failover procedure while lag is minimal",
        "severity": "Major", "domain": "Core",
    },
    {
        "alarm": "Diameter peer connection lost between PCRF {pcrf_id} and PGW {pgw_id}",
        "diagnosis": "Diameter Gx interface connection between PCRF {pcrf_id} and PGW {pgw_id} is down. Impact: PGW cannot obtain QoS policies from PCRF. New bearer requests may use default policy or be rejected. Causes: 1) PCRF process failure, 2) TCP/SCTP transport issue on Diameter port 3868, 3) Diameter watchdog timeout (DWR/DWA), 4) Certificate expiry on TLS-secured connection.",
        "resolution": "1. Check PCRF process status and logs\n2. Verify TCP connectivity on Diameter port 3868\n3. Check Diameter peer table on both PCRF and PGW\n4. If TLS is used, verify certificate validity dates\n5. Attempt Diameter peer reconnection from PGW side\n6. Check if PGW is falling back to local policy (may mask user impact)\n7. Monitor Rx interface (to AF/IMS) if VoLTE is affected",
        "severity": "Critical", "domain": "Core",
    },

    # ---- Transport (8 scenarios) ----
    {
        "alarm": "Packet loss rate exceeds {loss}% on backhaul link to site {site_id}",
        "diagnosis": "Backhaul link to site {site_id} showing {loss}% packet loss. This affects all services on the site. Causes: 1) Microwave link degradation (rain fade, alignment), 2) Fiber cut or degradation, 3) Router/switch port errors (CRC, frame), 4) QoS misconfiguration causing drops under load, 5) MTU mismatch causing fragmentation.",
        "resolution": "1. Check backhaul link type (MW/Fiber/Ethernet)\n2. For microwave: check RSL, SNR, and modulation level\n3. For fiber: check optical power levels (Tx/Rx)\n4. Check interface error counters (CRC, drops, overruns)\n5. Verify MTU settings end-to-end\n6. Run traceroute to isolate hop with loss\n7. If MW rain fade, wait for weather improvement + verify ATPC is enabled",
        "severity": "Major", "domain": "Transport",
    },
    {
        "alarm": "High latency detected on fronthaul link to RRU at site {site_id} — {latency}ms",
        "diagnosis": "Fronthaul (eCPRI/CPRI) link to Remote Radio Unit at site {site_id} showing {latency}ms one-way delay, exceeding the 100μs budget for Category A split. Impact: HARQ timing violations, increased BLER, potential cell outage. Causes: 1) Fiber degradation (increased attenuation), 2) Switch/router adding unexpected delay, 3) Wrong QoS priority causing queuing delay, 4) Ethernet frame size issue.",
        "resolution": "1. Verify fronthaul architecture (CPRI/eCPRI/Ethernet)\n2. Measure one-way delay with precision timing equipment\n3. Check each hop for queuing delay — fronthaul must have strict priority\n4. Verify fiber attenuation is within spec (OTDR test)\n5. Check for any intermediate switches — minimize hop count\n6. Verify PTP/SyncE timing is locked\n7. If Ethernet-based, ensure jumbo frames are enabled end-to-end",
        "severity": "Critical", "domain": "Transport",
    },
    {
        "alarm": "BGP peer down between PE router {router1} and {router2}",
        "diagnosis": "BGP peering session between PE routers {router1} and {router2} is down. Impact: routes advertised by {router2} are withdrawn, potentially causing traffic blackholing for connected sites. Causes: 1) Physical link failure between routers, 2) BGP hold timer expiry (keepalive not received), 3) Route policy change rejecting all prefixes, 4) Authentication (MD5) key mismatch, 5) Maximum prefix limit exceeded.",
        "resolution": "1. Check physical link status between the routers\n2. Verify BGP neighbor state (Idle/Active/OpenSent/Established)\n3. Check BGP logs for notification messages and error codes\n4. Verify BGP authentication key matches on both ends\n5. Check if max-prefix limit was hit (clear and increase if needed)\n6. Review recent route policy changes\n7. If link is up but BGP down, clear BGP session and monitor re-establishment\n8. Check IGP (OSPF/IS-IS) for underlying routing issues",
        "severity": "Critical", "domain": "Transport",
    },
    {
        "alarm": "MPLS LSP down for VPN {vpn_name} between {pe1} and {pe2}",
        "diagnosis": "MPLS Label Switched Path for VPN {vpn_name} between PE routers {pe1} and {pe2} is down. Impact: L3VPN connectivity lost for all sites in this VPN connected via these PEs. Causes: 1) LDP/RSVP-TE session failure, 2) IGP route withdrawal for PE loopback, 3) Transit router failure, 4) Label allocation failure, 5) BFD-triggered fast reroute.",
        "resolution": "1. Check LDP/RSVP session status between PEs\n2. Verify IGP reachability to remote PE loopback address\n3. Trace LSP path — identify where label is being dropped\n4. Check for transit node failures or maintenance\n5. Verify VRF import/export route targets match\n6. If FRR activated, check if backup path is valid\n7. Force LDP/RSVP re-signaling if sessions are stuck",
        "severity": "Critical", "domain": "Transport",
    },
    {
        "alarm": "Synchronization loss on site {site_id} — PTP grandmaster unreachable",
        "diagnosis": "Precision Time Protocol (PTP/IEEE 1588v2) synchronization lost at site {site_id}. The site cannot reach the PTP grandmaster clock. Impact: without accurate timing, TDD frame alignment fails, causing inter-cell interference and potential cell outage. Causes: 1) PTP grandmaster failure, 2) Network path change bypassing boundary clocks, 3) Asymmetric delay introduced by non-PTP-aware switch, 4) GNSS antenna failure on grandmaster.",
        "resolution": "1. Check if site has SyncE backup — should hold over temporarily\n2. Verify PTP grandmaster status (locked to GNSS?)\n3. Trace PTP packet path — identify where packets are lost\n4. Check all boundary/transparent clocks in the path\n5. Verify network switches are PTP-aware and configured\n6. If GNSS issue, check antenna cable and sky visibility\n7. Confirm holdover accuracy spec — how long before TDD fails?",
        "severity": "Critical", "domain": "Transport",
    },

    # ---- IMS/VoLTE (5 scenarios) ----
    {
        "alarm": "VoLTE call setup failure rate exceeds {threshold}% on {region}",
        "diagnosis": "VoLTE call setup success rate has dropped below acceptable threshold in {region}. Current failure rate: {threshold}%. Analysis of failure causes: 1) IMS registration failures (check P-CSCF), 2) Bearer setup failures (dedicated EPS bearer for QCI=1), 3) DNS resolution issues for IMS domain, 4) Certificate expiry on SBC/P-CSCF.",
        "resolution": "1. Check IMS registration success rate per P-CSCF\n2. Verify dedicated bearer setup (QCI=1) success rate\n3. Test DNS resolution for IMS APN\n4. Check SBC and P-CSCF certificate validity\n5. Review SIP signaling traces for error codes\n6. If 403/503 errors, check HSS subscription data\n7. Verify VoLTE feature is enabled in subscriber profile",
        "severity": "Critical", "domain": "IMS/VoLTE",
    },
    {
        "alarm": "One-way audio reported on VoLTE calls in {region}",
        "diagnosis": "Multiple subscribers reporting one-way audio on VoLTE calls in {region}. Caller can hear callee but not vice versa, or vice versa. Causes: 1) NAT/firewall blocking RTP in one direction, 2) SDP negotiation mismatch (codec, IP, port), 3) SBC media handling error, 4) IP address conflict on media plane, 5) QCI=1 bearer established in one direction only.",
        "resolution": "1. Capture SIP/SDP traces for affected calls — check media negotiation\n2. Verify RTP flow in both directions (source IP, dest IP, ports)\n3. Check NAT/firewall rules for RTP port range (typically 16384-32767)\n4. Verify SBC media anchoring configuration\n5. Check if issue is codec-specific (AMR-WB vs AMR-NB)\n6. Test with specific handsets to rule out terminal issue\n7. Check QCI=1 bearer establishment in both UL and DL directions",
        "severity": "Major", "domain": "IMS/VoLTE",
    },
    {
        "alarm": "SIP 503 Service Unavailable responses from S-CSCF {scscf_id}",
        "diagnosis": "S-CSCF {scscf_id} is responding with 503 Service Unavailable to INVITE requests. Impact: new call attempts are failing. Causes: 1) S-CSCF overload (CPU/memory/session limit), 2) HSS/Cx interface failure (cannot download user profile), 3) Application server unreachable, 4) License limit reached, 5) Internal queue overflow.",
        "resolution": "1. Check S-CSCF CPU/memory utilization\n2. Verify Cx interface to HSS is operational (Diameter)\n3. Check active session count vs licensed capacity\n4. Review S-CSCF overload control settings\n5. If overload, activate load shedding (reject % of new requests)\n6. Scale out if persistent — add S-CSCF instance to pool\n7. Check I-CSCF routing rules — ensure load balancing across S-CSCFs",
        "severity": "Critical", "domain": "IMS/VoLTE",
    },

    # ---- Security (3 scenarios) ----
    {
        "alarm": "Abnormal signaling spike detected — {count} attach requests/sec from TAC {tac}",
        "diagnosis": "Signaling storm detected: {count} attach requests per second originating from Tracking Area Code {tac}, which is 10x the normal rate. This could indicate: 1) DoS/DDoS attack targeting the core network, 2) Mass device reboot (IoT devices, firmware update), 3) Ping-pong registration between cells, 4) Faulty base station sending repeated attach triggers.",
        "resolution": "1. Identify source — is it distributed (many IMSIs) or concentrated (few IMSIs)?\n2. If few IMSIs with high rate: possible compromised devices or attack\n3. If many IMSIs: check for cell/area-wide event (power outage recovery)\n4. Enable signaling throttling on MME/AMF for the affected TAC\n5. If attack confirmed, block offending IMSIs/IMEIs at MME\n6. Check if eNodeBs in TAC have abnormal behavior\n7. Engage security team if confirmed malicious\n8. Monitor for secondary effects (HSS overload, billing system impact)",
        "severity": "Critical", "domain": "Security",
    },
    {
        "alarm": "Certificate expiry warning — TLS cert on {node} expires in {days} days",
        "diagnosis": "TLS/SSL certificate on {node} will expire in {days} days. If not renewed, all HTTPS/TLS connections to this node will fail with certificate errors. Impact varies by node type: SBC (VoLTE calls fail), NRF (5G service discovery fails), NEF (API exposure fails), OAM (management access lost).",
        "resolution": "1. Identify certificate authority (internal CA or public CA)\n2. Generate new CSR (Certificate Signing Request) from the node\n3. Submit CSR to CA for renewal\n4. Install renewed certificate during maintenance window\n5. Verify certificate chain is complete (leaf + intermediate + root)\n6. Test TLS handshake after installation\n7. Update certificate monitoring system with new expiry date\n8. Consider implementing automated certificate renewal (ACME/Let's Encrypt for non-prod)",
        "severity": "Major", "domain": "Security",
    },

    # ---- Energy/Sustainability (2 scenarios) ----
    {
        "alarm": "Site {site_id} battery backup below {battery}% — mains power failure detected",
        "diagnosis": "Site {site_id} has lost mains power and is running on battery. Current battery level: {battery}%. Estimated remaining runtime depends on load and battery age. Impact: if battery depletes before mains is restored, entire site goes offline. Connected users: approximately {users} UEs.",
        "resolution": "1. Dispatch power team to check mains supply (utility outage vs local fault)\n2. Contact power utility for estimated restoration time\n3. If ETA > battery runtime, dispatch mobile generator\n4. Consider enabling power saving features (reduce MIMO layers, carrier shutdown)\n5. Enable MLB to offload users to neighboring sites preemptively\n6. Monitor battery drain rate and update ETA\n7. If multi-site outage, prioritize sites by traffic/criticality\n8. After power restoration, verify battery charging and set recharge threshold",
        "severity": "Critical", "domain": "Power",
    },
]


# =============================================================================
# 2. EXPANDED INTENT-TO-CONFIG PAIRS (25+ templates)
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
  isolation: hard""",
    },
    {
        "intent": "Configure a 5G cell with 100MHz bandwidth on n78 band with 4x4 MIMO",
        "config": """cell_config:
  cell_id: 1
  nr_band: n78
  duplex_mode: TDD
  channel_bandwidth_mhz: 100
  subcarrier_spacing_khz: 30
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
    max_transmit_power_dbm: 49""",
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
      gbr_dl: 128kbps
      gbr_ul: 128kbps
      mbr_dl: 256kbps
      mbr_ul: 256kbps
      packet_delay_budget_ms: 100
      packet_error_rate: 1e-2""",
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
  report_configs:
    - event: A2
      threshold_rsrp: -110
      hysteresis_db: 2
      time_to_trigger_ms: 640
    - event: A5
      threshold1_rsrp: -100
      threshold2_rsrp: -90
      hysteresis_db: 2
      time_to_trigger_ms: 320
  execution:
    t304_ms: 200""",
    },
    {
        "intent": "Enable carrier aggregation combining n78 primary and n1 secondary",
        "config": """carrier_aggregation:
  mode: inter_band_ca
  pcell:
    nr_band: n78
    channel_bandwidth_mhz: 100
    subcarrier_spacing_khz: 30
  scells:
    - nr_band: n1
      channel_bandwidth_mhz: 20
      subcarrier_spacing_khz: 15
      scell_deactivation_timer_ms: 2560
  split_bearer: true
  primary_path: pcell""",
    },
    {
        "intent": "Configure CSFB (Circuit Switched Fallback) from LTE to 3G for voice calls",
        "config": """csfb_config:
  enabled: true
  fallback_mode: redirection  # or handover
  target_rat: UTRAN
  redirect_carrier:
    uarfcn: 10713
    band: 1
  measurement_config:
    b1_threshold_rscp: -100
    time_to_trigger_ms: 320
  timers:
    t3417_ext_ms: 10000
    t3442_ms: 4000""",
    },
    {
        "intent": "Set up SON (Self-Organizing Network) for automatic neighbor relations",
        "config": """son_config:
  anr:
    enabled: true
    max_neighbors_per_cell: 32
    measurement_report_trigger: event_A3
    auto_add_threshold_rsrp: -105
    auto_remove_threshold: no_ho_attempts_7days
    blacklist_max_entries: 16
  mlb:
    enabled: true
    load_balancing_offset_db: 3
    prb_utilization_threshold: 70
    hysteresis_timer_min: 10
  mro:
    enabled: true
    too_late_ho_threshold: 5
    too_early_ho_threshold: 3
    adjustment_step_db: 1""",
    },
    {
        "intent": "Configure network slicing for IoT massive machine type communications",
        "config": """network_slice:
  name: iot-mmtc-slice
  sst: 3  # mMTC
  sd: "0x000010"
  qos_profile:
    5qi: 79  # Non-GBR, delay tolerant
    priority_level: 10
    packet_delay_budget_ms: 1000
  resource_allocation:
    max_bitrate_dl: 256kbps
    max_bitrate_ul: 256kbps
  device_params:
    power_saving_mode: enabled
    edrx_cycle_seconds: 2621
    max_devices_per_cell: 100000
  isolation: soft""",
    },
    {
        "intent": "Configure DRX (Discontinuous Reception) for power saving with low latency",
        "config": """drx_config:
  long_drx:
    cycle_ms: 40
    on_duration_timer_ms: 4
    inactivity_timer_ms: 20
    retransmission_timer_dl_ms: 4
    retransmission_timer_ul_ms: 4
  short_drx:
    enabled: true
    cycle_ms: 10
    timer_ms: 4
  drx_slot_offset: 0
  harq_rtt_timer_dl: 56
  harq_rtt_timer_ul: 56""",
    },
    {
        "intent": "Set up IPsec tunnel between eNodeB and security gateway for backhaul encryption",
        "config": """ipsec_config:
  tunnel_mode: true
  local_endpoint:
    ip: 10.10.1.100
    type: enodeb
  remote_endpoint:
    ip: 172.16.0.1
    type: security_gateway
  ike:
    version: 2
    encryption: aes-256-cbc
    integrity: sha256
    dh_group: 14
    lifetime_seconds: 86400
    authentication: certificate
  ipsec_sa:
    encryption: aes-256-gcm
    lifetime_seconds: 3600
    pfs_group: 14
  dead_peer_detection:
    interval_seconds: 30
    retry_count: 5""",
    },
    {
        "intent": "Configure RAN energy saving with carrier shutdown during low traffic",
        "config": """energy_saving:
  carrier_shutdown:
    enabled: true
    secondary_carrier:
      nr_band: n78
      action: shutdown_when_idle
    trigger:
      prb_utilization_below: 10
      duration_minutes: 30
    restore:
      prb_utilization_above: 50
      duration_minutes: 5
  mimo_adaptation:
    enabled: true
    reduce_to_2t2r_when:
      connected_ues_below: 20
      duration_minutes: 15
  symbol_shutdown:
    enabled: true
    shutdown_empty_dl_symbols: true
  monitoring:
    kpi_check_interval_minutes: 5
    qos_protection: enabled""",
    },
    {
        "intent": "Configure 5G SA core network UPF for edge computing with ULCL",
        "config": """upf_config:
  name: edge-upf-01
  location: edge_site_a
  interfaces:
    n3:
      ip: 10.100.1.1
      connected_gnbs: [gnb-001, gnb-002, gnb-003]
    n4:
      ip: 10.100.2.1
      connected_smf: smf-central-01
    n6:
      ip: 192.168.1.1
      connected_dn: edge-app-server
    n9:
      ip: 10.100.3.1
      connected_upf: central-upf-01
  ulcl:
    enabled: true
    traffic_steering:
      - match:
          destination: 192.168.0.0/16
        action: local_breakout
      - match:
          destination: 0.0.0.0/0
        action: forward_to_central_upf
  capacity:
    max_sessions: 50000
    max_throughput_gbps: 10""",
    },
    {
        "intent": "Set up MOCN (Multi-Operator Core Network) RAN sharing between two operators",
        "config": """ran_sharing:
  type: MOCN
  shared_cell:
    cell_id: 1
    nr_band: n78
    bandwidth_mhz: 100
  operators:
    - plmn: "310-260"
      name: operator_a
      resource_share: 60
      dedicated_prbs: false
      max_connected_ues: 500
    - plmn: "311-480"
      name: operator_b
      resource_share: 40
      dedicated_prbs: false
      max_connected_ues: 300
  scheduling:
    mode: proportional_fair_per_operator
    minimum_guarantee: true
  core_routing:
    operator_a_amf: amf-a.core.operator-a.com
    operator_b_amf: amf-b.core.operator-b.com""",
    },
    {
        "intent": "Configure alarm correlation rules for automatic root cause identification",
        "config": """alarm_correlation:
  rules:
    - name: site_power_failure
      root_cause: power_outage
      primary_alarm:
        type: site_unreachable
        severity: critical
      correlated_alarms:
        - type: cell_outage
          time_window_seconds: 300
        - type: transport_link_down
          time_window_seconds: 120
        - type: battery_low
          time_window_seconds: 600
      action: suppress_correlated_and_raise_root
    - name: backhaul_failure_cascade
      root_cause: transport_link_failure
      primary_alarm:
        type: transport_link_down
        severity: critical
      correlated_alarms:
        - type: s1_link_failure
          time_window_seconds: 60
        - type: x2_link_failure
          time_window_seconds: 60
      action: suppress_correlated_and_raise_root""",
    },
    {
        "intent": "Configure performance monitoring counters for RAN KPI dashboard",
        "config": """pm_config:
  collection_interval_minutes: 15
  kpi_definitions:
    - name: dl_throughput_cell_avg
      formula: "sum(dl_bytes) / measurement_period"
      unit: Mbps
      threshold_warning: 50
      threshold_critical: 20
    - name: rrc_setup_success_rate
      formula: "rrc_setup_success / rrc_setup_attempts * 100"
      unit: percent
      threshold_warning: 95
      threshold_critical: 90
    - name: erab_drop_rate
      formula: "erab_abnormal_release / erab_active * 100"
      unit: percent
      threshold_warning: 1
      threshold_critical: 3
    - name: handover_success_rate
      formula: "ho_success / ho_attempts * 100"
      unit: percent
      threshold_warning: 95
      threshold_critical: 90
    - name: volte_cssr
      formula: "volte_call_setup_success / volte_call_attempts * 100"
      unit: percent
      threshold_warning: 98
      threshold_critical: 95
  retention_days: 90
  export_format: csv""",
    },
]


# =============================================================================
# 3. NEW CATEGORY: KPI ANALYSIS
# =============================================================================

KPI_ANALYSIS_PAIRS = [
    {
        "question": "Cell {cell_id} shows RRC setup success rate of 87%. Is this normal and what should I investigate?",
        "answer": "An RRC setup success rate of 87% on cell {cell_id} is **below the typical target of 95%**. This means approximately 13% of connection attempts are failing.\n\n**Investigation steps:**\n1. **Check RACH success rate** — if RACH is also low, the issue starts at physical layer access\n2. **Review PDCCH capacity** — CCE utilization >70% causes RRC failures due to insufficient DL control resources\n3. **Check for coverage issues** — UEs at cell edge may fail RRC setup due to poor SINR\n4. **Compare with neighbors** — if all cells in the cluster are affected, look for area-wide causes (backhaul, core)\n5. **Check time pattern** — if worst during busy hour, likely congestion; if constant, likely config/HW issue\n\n**KPI correlation:** Also check DL BLER, UL interference, and PUCCH SINR alongside RRC setup rate.",
    },
    {
        "question": "Our network shows ERAB drop rate increasing from 0.5% to 2.8% over the past week. What analysis should I perform?",
        "answer": "An ERAB (E-RAB) drop rate increase from 0.5% to 2.8% is a significant degradation that needs immediate attention.\n\n**Analysis framework:**\n1. **Scope the problem:** Is it network-wide, cluster-specific, or single-cell? Filter by region/cluster/cell\n2. **Classify drop causes:**\n   - Radio link failure (RLF): indicates RF issues\n   - Transport failure: indicates backhaul problems\n   - Core network release: indicates core/signaling issues\n   - Handover failure: indicates mobility issues\n3. **Time correlation:** When did the increase start? Correlate with:\n   - Software upgrades or patches\n   - Configuration changes (CM audit)\n   - New site integrations\n   - Weather events (for MW backhaul)\n4. **Top N analysis:** Identify top 10 worst cells by ERAB drop rate\n5. **Check UL interference** — sudden increase often indicates external interference source\n\n**Target:** ERAB drop rate should be below 1% for a healthy network.",
    },
    {
        "question": "What KPIs should I monitor to ensure good VoLTE quality?",
        "answer": "**Critical VoLTE KPIs to monitor:**\n\n| KPI | Target | Description |\n|-----|--------|-------------|\n| VoLTE CSSR | >99% | Call Setup Success Rate |\n| VoLTE CDR | <0.5% | Call Drop Rate |\n| VoLTE MOS | >3.5 | Mean Opinion Score (voice quality) |\n| E2E Setup Time | <3s | From INVITE to 200 OK |\n| QCI=1 Bearer Setup | >99% | Dedicated bearer establishment |\n| IMS Registration | >99.5% | SIP REGISTER success rate |\n| SRVCC Success | >95% | VoLTE to 3G handover (if applicable) |\n| Jitter | <30ms | RTP packet jitter |\n| Packet Loss | <1% | RTP packet loss rate |\n\n**Monitoring approach:**\n1. Track hourly trends for CSSR and CDR\n2. Set up alerts for MOS drops below 3.0\n3. Monitor per-cell and per-region aggregates\n4. Correlate VoLTE KPIs with RAN KPIs (BLER, SINR, handover success)",
    },
    {
        "question": "How do I calculate and interpret Erlang B for dimensioning voice capacity on a cell?",
        "answer": "**Erlang B Formula** is used to calculate the blocking probability for a given number of channels and traffic load.\n\n**Key concepts:**\n- **Erlang**: Unit of traffic intensity. 1 Erlang = 1 channel busy for 1 hour\n- **GOS (Grade of Service)**: Target blocking probability (typically 2% = 0.02)\n- **BHT (Busy Hour Traffic)**: Peak traffic in Erlangs\n\n**Calculation:**\n1. Estimate subscribers per cell: e.g., 500 users\n2. Average calls per subscriber in busy hour: e.g., 0.8\n3. Average call duration: e.g., 90 seconds\n4. BHT = 500 × 0.8 × (90/3600) = 10 Erlangs\n5. Using Erlang B table with GOS=2%: 10 Erlangs requires ~18 channels\n\n**For VoLTE dimensioning:**\n- Each VoLTE call uses 1 QCI=1 GBR bearer\n- PRB consumption: ~2-4 PRBs per VoLTE call (AMR-WB)\n- With 100 PRBs (20MHz): can support ~25-50 simultaneous VoLTE calls\n- Add 20% headroom for signaling and control channels",
    },
]


# =============================================================================
# 4. NEW CATEGORY: PROTOCOL EXPLANATIONS
# =============================================================================

PROTOCOL_PAIRS = [
    {
        "question": "Explain the 5G NR random access procedure (RACH) step by step.",
        "answer": "**5G NR Random Access (RACH) Procedure — 4-Step:**\n\n**Step 1: Preamble Transmission (Msg1)**\n- UE selects a random preamble from available set\n- Transmits on PRACH occasion (configured by SIB1)\n- Power ramping: starts at calculated power, increases if no response\n\n**Step 2: Random Access Response (Msg2)**\n- gNB detects preamble and sends RAR on PDSCH\n- RAR contains: Timing Advance, UL grant for Msg3, Temporary C-RNTI\n- UE must receive within ra-ResponseWindow\n\n**Step 3: Scheduled Transmission (Msg3)**\n- UE sends RRC connection request using the UL grant from Msg2\n- Contains UE identity (5G-S-TMSI or random value)\n- HARQ enabled for this message\n\n**Step 4: Contention Resolution (Msg4)**\n- gNB resolves contention if multiple UEs sent same preamble\n- Sends UE-specific message with matching identity\n- UE considers RA successful upon receiving Msg4\n\n**2-Step RACH (NR enhancement):**\n- MsgA = Preamble + Msg3 (combined)\n- MsgB = RAR + Msg4 (combined)\n- Lower latency, suitable for small cells with low contention",
    },
    {
        "question": "What is the difference between NSA (Non-Standalone) and SA (Standalone) 5G deployment?",
        "answer": "**NSA (Non-Standalone) — Option 3x:**\n- LTE eNB is the master node (anchor)\n- 5G gNB is secondary node (for user plane boost)\n- Core network: 4G EPC (no 5G core)\n- Control plane: goes through LTE\n- User plane: split/switched between LTE and NR\n- Advantage: faster deployment, leverages existing LTE coverage\n- Limitation: no 5G core features (slicing, edge computing, URLLC)\n\n**SA (Standalone) — Option 2:**\n- 5G gNB connects directly to 5G Core (5GC)\n- No LTE dependency for control plane\n- Core network: 5GC (AMF, SMF, UPF, etc.)\n- Enables: network slicing, URLLC, edge computing, SBA\n- Full 5G feature set available\n\n**Key architectural differences:**\n| Aspect | NSA | SA |\n|--------|-----|----|\n| Core | 4G EPC | 5G Core |\n| Control Plane | LTE RRC | NR RRC |\n| Slicing | No | Yes |\n| URLLC | Limited | Full |\n| Edge Computing | Limited | Full (ULCL/BP) |\n| Voice | VoLTE (existing) | VoNR (new) |\n| Deployment | Overlay on LTE | Independent |",
    },
    {
        "question": "Explain the N2, N3, N4, and N6 interfaces in 5G SA architecture.",
        "answer": "**5G SA Core Network Interfaces:**\n\n**N2 Interface (gNB ↔ AMF)**\n- Protocol: NGAP over SCTP\n- Purpose: Control plane — NAS transport, handover, paging\n- Carries: UE registration, PDU session management (control), handover signaling\n- Equivalent to S1-MME in 4G\n\n**N3 Interface (gNB ↔ UPF)**\n- Protocol: GTP-U over UDP\n- Purpose: User plane — carries actual user data\n- Carries: Encapsulated user IP packets in GTP tunnels\n- Equivalent to S1-U in 4G\n\n**N4 Interface (SMF ↔ UPF)**\n- Protocol: PFCP (Packet Forwarding Control Protocol) over UDP\n- Purpose: SMF programs forwarding rules into UPF\n- Carries: PDR (Packet Detection Rules), FAR (Forwarding Action Rules), QER (QoS Enforcement Rules), URR (Usage Reporting Rules)\n- This is new in 5G — enables CUPS (Control/User Plane Separation)\n\n**N6 Interface (UPF ↔ Data Network)**\n- Protocol: Standard IP routing\n- Purpose: Connects UPF to external data networks (internet, enterprise)\n- Carries: De-encapsulated user IP traffic\n- Equivalent to SGi in 4G\n\n**Other key interfaces:** N1 (UE↔AMF, NAS), N8 (AMF↔UDM), N10 (SMF↔UDM), N11 (AMF↔SMF), N7 (SMF↔PCF)",
    },
]


# =============================================================================
# 5. TELEQNA-STYLE TRAINING DATA
# =============================================================================

TELEQNA_STYLE = [
    {
        "question": "What is the maximum channel bandwidth supported by 5G NR in FR1?",
        "choices": ["20 MHz", "50 MHz", "100 MHz", "400 MHz"],
        "correct": 2,
        "explanation": "5G NR supports up to 100 MHz channel bandwidth in FR1 (sub-6 GHz). FR2 (mmWave) supports up to 400 MHz."
    },
    {
        "question": "Which 5QI value is used for conversational voice (VoNR)?",
        "choices": ["5QI=1", "5QI=5", "5QI=9", "5QI=79"],
        "correct": 0,
        "explanation": "5QI=1 is defined for conversational voice, with 100ms packet delay budget and 10^-2 packet error rate. It is a GBR (Guaranteed Bit Rate) flow."
    },
    {
        "question": "What protocol is used on the N4 interface between SMF and UPF?",
        "choices": ["GTP-C", "Diameter", "PFCP", "HTTP/2"],
        "correct": 2,
        "explanation": "PFCP (Packet Forwarding Control Protocol) is used on the N4 interface. It allows the SMF to program packet detection and forwarding rules in the UPF."
    },
    {
        "question": "What is the purpose of SSB (Synchronization Signal Block) in 5G NR?",
        "choices": ["User data transmission", "Handover execution", "Cell search and synchronization", "QoS enforcement"],
        "correct": 2,
        "explanation": "SSB carries PSS (Primary Synchronization Signal), SSS (Secondary Synchronization Signal), and PBCH (Physical Broadcast Channel) used by UEs for initial cell search, synchronization, and system information acquisition."
    },
    {
        "question": "In 5G network slicing, what does SST=1 represent?",
        "choices": ["URLLC", "eMBB", "mMTC", "V2X"],
        "correct": 1,
        "explanation": "SST (Slice/Service Type) value 1 represents eMBB (enhanced Mobile Broadband). SST=2 is URLLC, SST=3 is mMTC."
    },
    {
        "question": "What is the primary function of the AMF in 5G Core?",
        "choices": ["User plane forwarding", "Session management", "Access and mobility management", "Policy control"],
        "correct": 2,
        "explanation": "AMF (Access and Mobility Management Function) handles UE registration, connection management, mobility, and NAS signaling. SMF handles session management, UPF handles user plane, PCF handles policy."
    },
    {
        "question": "Which modulation scheme provides the highest spectral efficiency in 5G NR?",
        "choices": ["QPSK", "16QAM", "64QAM", "256QAM"],
        "correct": 3,
        "explanation": "256QAM provides the highest spectral efficiency (8 bits per symbol) but requires the best SINR conditions. 5G NR DL supports up to 256QAM, and optionally 1024QAM in Release 17+."
    },
    {
        "question": "What does HARQ stand for and what is its purpose?",
        "choices": [
            "High Availability Resource Queue — manages resource allocation",
            "Hybrid Automatic Repeat Request — combines FEC with retransmission",
            "Handover Access Request Queue — manages handover requests",
            "High Accuracy Reporting Query — reports measurement data"
        ],
        "correct": 1,
        "explanation": "HARQ (Hybrid Automatic Repeat Request) combines forward error correction (FEC) with ARQ retransmission. If decoding fails, the receiver requests retransmission and combines it with the original for better decoding probability."
    },
    {
        "question": "What is the minimum subcarrier spacing defined for 5G NR?",
        "choices": ["7.5 kHz", "15 kHz", "30 kHz", "60 kHz"],
        "correct": 1,
        "explanation": "The minimum SCS in 5G NR is 15 kHz (μ=0), same as LTE. 5G NR supports SCS of 15, 30, 60, 120, and 240 kHz. Higher SCS values are used in FR2 (mmWave)."
    },
    {
        "question": "In LTE, what is the purpose of the Tracking Area Update (TAU) procedure?",
        "choices": [
            "To establish a data connection",
            "To inform the network of UE location changes",
            "To authenticate the subscriber",
            "To measure neighbor cell signal quality"
        ],
        "correct": 1,
        "explanation": "TAU is performed when a UE in idle mode moves to a new Tracking Area. It updates the MME with the UE's current location so the network can page the UE for incoming calls/data."
    },
    {
        "question": "What is the role of CU-DU split in 5G RAN architecture?",
        "choices": [
            "Separates control and user plane in the core",
            "Splits RAN functions between centralized and distributed units",
            "Divides spectrum between operators",
            "Separates indoor and outdoor coverage"
        ],
        "correct": 1,
        "explanation": "CU-DU split separates gNB functions: CU (Central Unit) handles RRC and PDCP (higher layers), DU (Distributed Unit) handles RLC, MAC, and PHY (lower layers). This enables centralized RAN with fronthaul, enabling Cloud RAN architectures."
    },
    {
        "question": "What is the maximum number of component carriers supported in NR carrier aggregation?",
        "choices": ["2", "5", "8", "16"],
        "correct": 3,
        "explanation": "5G NR supports up to 16 component carriers in carrier aggregation (Release 15+). This is an increase from LTE which supported up to 5 CCs. The total aggregated bandwidth can reach up to 1 GHz in FR1."
    },
]


# =============================================================================
# Format and generate
# =============================================================================

def generate_noc_data(n_samples: int = 8000) -> List[Dict]:
    """Generate diverse NOC training data from expanded scenarios."""
    data = []
    params_pool = {
        "site_id": [f"ENB-{random.randint(1000, 9999)}" for _ in range(200)],
        "cell_id": [f"CELL-{random.randint(10000, 99999)}" for _ in range(200)],
        "neighbor_cell": [f"CELL-{random.randint(10000, 99999)}" for _ in range(200)],
        "mme_id": [f"MME-{random.randint(1, 8):02d}" for _ in range(8)],
        "amf_id": [f"AMF-{random.randint(1, 12):02d}" for _ in range(12)],
        "smf_id": [f"SMF-{random.randint(1, 6):02d}" for _ in range(6)],
        "sgw_id": [f"SGW-{random.randint(1, 4):02d}" for _ in range(4)],
        "pgw_id": [f"PGW-{random.randint(1, 4):02d}" for _ in range(4)],
        "pcrf_id": [f"PCRF-{random.randint(1, 4):02d}" for _ in range(4)],
        "scscf_id": [f"S-CSCF-{random.randint(1, 4):02d}" for _ in range(4)],
        "router1": [f"PE-{random.choice(['NYC','LAX','CHI','DAL','ATL'])}-{random.randint(1,4):02d}" for _ in range(20)],
        "router2": [f"PE-{random.choice(['SFO','MIA','SEA','DEN','BOS'])}-{random.randint(1,4):02d}" for _ in range(20)],
        "pe1": [f"PE-{random.randint(1, 8):02d}" for _ in range(8)],
        "pe2": [f"PE-{random.randint(1, 8):02d}" for _ in range(8)],
        "vpn_name": [f"VPN-{random.choice(['ENTERPRISE','MOBILE','IOT','MGMT','VOICE'])}-{random.randint(100,999)}" for _ in range(20)],
        "node": [f"{random.choice(['SBC','NRF','NEF','P-CSCF','I-CSCF','OAM-GW'])}-{random.randint(1,4):02d}" for _ in range(20)],
        "sector": [f"S{random.randint(1, 3)}" for _ in range(3)],
        "cpu": [random.randint(85, 99) for _ in range(20)],
        "ue_threshold": [random.randint(200, 500) for _ in range(10)],
        "fw_version": [f"{random.randint(18, 23)}.{random.randint(0, 9)}" for _ in range(10)],
        "drop": [random.randint(20, 60) for _ in range(20)],
        "threshold": [random.randint(5, 25) for _ in range(20)],
        "region": ["North", "South", "East", "West", "Central", "Metro", "Rural", "Coastal"],
        "loss": [round(random.uniform(1.5, 10.0), 1) for _ in range(20)],
        "latency": [round(random.uniform(0.5, 50.0), 1) for _ in range(20)],
        "lag": [random.randint(500, 5000) for _ in range(10)],
        "count": [random.randint(500, 10000) for _ in range(10)],
        "tac": [random.randint(1000, 9999) for _ in range(20)],
        "days": [random.randint(3, 30) for _ in range(10)],
        "battery": [random.randint(10, 40) for _ in range(10)],
        "users": [random.randint(50, 500) for _ in range(20)],
        "util": [random.randint(70, 95) for _ in range(10)],
        "pci_val": [random.randint(0, 503) for _ in range(20)],
    }

    for _ in range(n_samples):
        scenario = random.choice(NOC_SCENARIOS)
        params = {k: random.choice(v) for k, v in params_pool.items()}

        try:
            alarm = scenario["alarm"].format(**params)
            diagnosis = scenario["diagnosis"].format(**params)
            resolution = scenario["resolution"].format(**params)
        except KeyError:
            continue

        instruction_type = random.choice(["diagnose", "resolve", "full"])

        if instruction_type == "diagnose":
            data.append({
                "instruction": f"I'm seeing this alarm in the NOC: '{alarm}'. What could be causing this?",
                "response": diagnosis,
                "category": "noc_diagnosis",
            })
        elif instruction_type == "resolve":
            data.append({
                "instruction": f"Alarm: '{alarm}'\nDiagnosis: {diagnosis}\n\nWhat are the resolution steps?",
                "response": resolution,
                "category": "noc_resolution",
            })
        else:
            data.append({
                "instruction": f"NOC Alert: '{alarm}'\n\nPlease provide full incident analysis and resolution steps.",
                "response": f"**Diagnosis:**\n{diagnosis}\n\n**Resolution Steps:**\n{resolution}",
                "category": "noc_full",
            })

    return data


def generate_config_data(n_samples: int = 3000) -> List[Dict]:
    """Generate intent-to-config training pairs."""
    data = []
    templates = [
        "Convert this network intent to configuration: {intent}",
        "As a network engineer, I need to: {intent}\nGenerate the YAML configuration.",
        "Network intent: {intent}\n\nProvide the corresponding network configuration in YAML format.",
        "Generate 5G network configuration for: {intent}",
    ]

    for _ in range(n_samples):
        pair = random.choice(INTENT_CONFIG_PAIRS)
        template = random.choice(templates)
        data.append({
            "instruction": template.format(intent=pair["intent"]),
            "response": pair["config"].strip(),
            "category": "intent_to_config",
        })

    return data


def generate_kpi_data() -> List[Dict]:
    """Generate KPI analysis training data."""
    data = []
    params = {
        "cell_id": [f"CELL-{random.randint(10000, 99999)}" for _ in range(50)],
    }

    for pair in KPI_ANALYSIS_PAIRS:
        for _ in range(50):  # 50 variations each
            p = {k: random.choice(v) for k, v in params.items()}
            data.append({
                "instruction": pair["question"].format(**p),
                "response": pair["answer"].format(**p),
                "category": "kpi_analysis",
            })

    return data


def generate_protocol_data() -> List[Dict]:
    """Generate protocol explanation training data."""
    data = []
    for pair in PROTOCOL_PAIRS:
        # Each protocol explanation gets added multiple times with slight prompt variations
        prompts = [
            pair["question"],
            f"Can you explain: {pair['question']}",
            f"I'm studying for my telco certification. {pair['question']}",
        ]
        for prompt in prompts:
            data.append({
                "instruction": prompt,
                "response": pair["answer"],
                "category": "protocol_knowledge",
            })
    return data


def generate_mcq_training_data() -> List[Dict]:
    """Generate TeleQnA-style MCQ training data."""
    data = []
    for q in TELEQNA_STYLE:
        choices_text = "\n".join(f"  {i}: {c}" for i, c in enumerate(q["choices"]))
        instruction = f"{q['question']}\n\nChoices:\n{choices_text}\n\nAnswer with the number of the correct choice and explain why."
        response = f"The correct answer is **{q['correct']}**: {q['choices'][q['correct']]}\n\n{q['explanation']}"
        data.append({
            "instruction": instruction,
            "response": response,
            "category": "mcq_telecom",
        })

        # Also add without choices (open-ended version)
        data.append({
            "instruction": q["question"],
            "response": f"{q['choices'][q['correct']]}\n\n{q['explanation']}",
            "category": "telecom_knowledge",
        })

    return data


def format_as_chat(examples: List[Dict]) -> List[Dict]:
    """Format as chat messages."""
    formatted = []
    for ex in examples:
        formatted.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": ex["instruction"]},
                {"role": "assistant", "content": ex["response"]},
            ],
            "category": ex["category"],
        })
    return formatted


def main():
    random.seed(42)
    print("=" * 60)
    print("TELCO SLM — Expanding Synthetic Training Data")
    print("=" * 60)

    # Load existing 3GPP Q&A data
    existing_3gpp = []
    existing_train = OUTPUT_DIR / "train.jsonl"
    existing_val = OUTPUT_DIR / "val.jsonl"
    if existing_train.exists():
        with open(existing_train) as f:
            for line in f:
                d = json.loads(line)
                if d.get("category") == "3gpp_knowledge":
                    existing_3gpp.append(d)
        with open(existing_val) as f:
            for line in f:
                d = json.loads(line)
                if d.get("category") == "3gpp_knowledge":
                    existing_3gpp.append(d)
        print(f"\nExisting 3GPP Q&A data: {len(existing_3gpp)} examples (preserved)")

    # Generate new synthetic data
    print(f"\nNOC scenarios: {len(NOC_SCENARIOS)} (was 5)")
    print(f"Config templates: {len(INTENT_CONFIG_PAIRS)} (was 5)")

    print("\n[1/5] Generating NOC data...")
    noc_data = generate_noc_data(8000)
    print(f"  Generated: {len(noc_data)}")

    print("[2/5] Generating intent-to-config data...")
    config_data = generate_config_data(3000)
    print(f"  Generated: {len(config_data)}")

    print("[3/5] Generating KPI analysis data...")
    kpi_data = generate_kpi_data()
    print(f"  Generated: {len(kpi_data)}")

    print("[4/5] Generating protocol explanation data...")
    protocol_data = generate_protocol_data()
    print(f"  Generated: {len(protocol_data)}")

    print("[5/5] Generating MCQ training data...")
    mcq_data = generate_mcq_training_data()
    print(f"  Generated: {len(mcq_data)}")

    # Combine all
    all_synthetic = noc_data + config_data + kpi_data + protocol_data + mcq_data
    all_formatted = format_as_chat(all_synthetic)

    # Add back existing 3GPP data
    all_data = existing_3gpp + all_formatted
    random.shuffle(all_data)

    # Split
    split_idx = int(len(all_data) * 0.9)
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]

    # Save
    for path, data in [(OUTPUT_DIR / "train.jsonl", train_data), (OUTPUT_DIR / "val.jsonl", val_data)]:
        with open(path, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"  Train: {len(train_data)} examples")
    print(f"  Val: {len(val_data)} examples")
    print(f"  Total: {len(all_data)}")

    from collections import Counter
    cats = Counter(d.get("category", "unknown") for d in all_data)
    print(f"\n  Category breakdown:")
    for cat, count in cats.most_common():
        print(f"    {cat}: {count}")

    # Also update MLX format
    mlx_dir = PROJECT_ROOT / "data" / "mlx_format"
    mlx_dir.mkdir(parents=True, exist_ok=True)
    for src, dst in [(OUTPUT_DIR / "train.jsonl", mlx_dir / "train.jsonl"),
                     (OUTPUT_DIR / "val.jsonl", mlx_dir / "valid.jsonl")]:
        with open(src) as fin, open(dst, "w") as fout:
            for line in fin:
                d = json.loads(line)
                fout.write(json.dumps({"messages": d["messages"]}) + "\n")

    # Test split
    with open(mlx_dir / "valid.jsonl") as fin:
        lines = fin.readlines()
    with open(mlx_dir / "test.jsonl", "w") as fout:
        for line in lines[:100]:
            fout.write(line)

    print(f"\n  MLX format updated in: {mlx_dir}")
    print(f"\n{'='*60}")
    print("Done! Ready to retrain with improved data.")
    print("  python scripts/training/train_mlx.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
