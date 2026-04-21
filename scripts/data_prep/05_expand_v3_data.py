"""
Step 5: Expand training data for v3 training
- Loads existing v2 data from data/processed/train.jsonl and val.jsonl
- Adds 20 NEW NOC scenarios (Transport: 7, Core: 8, IMS/VoLTE: 5)
- Adds 10 NEW intent-to-config templates
- Merges with existing data, shuffles, splits 90/10
- Saves to data/processed/ and data/mlx_format/
"""

import json
import random
from pathlib import Path
from typing import List, Dict
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MLX_DIR = PROJECT_ROOT / "data" / "mlx_format"

SYSTEM_PROMPT = (
    "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
    "You have deep knowledge of 3GPP standards, 5G/LTE network operations, "
    "RAN optimization, core network, transport, and IMS/VoLTE. "
    "You assist network engineers with diagnostics, configuration, "
    "troubleshooting, and standards interpretation."
)


# =============================================================================
# 1. NEW NOC SCENARIOS FOR V3 (20 new scenarios)
# =============================================================================

V3_NOC_SCENARIOS = [
    # ---- Transport Domain (7 new scenarios, bringing total from 5 to 12) ----
    {
        "alarm": "DWDM optical power degradation on span {span_id} — OSNR dropped to {osnr_val}dB",
        "diagnosis": "DWDM optical signal-to-noise ratio on span {span_id} has degraded to {osnr_val}dB, below the 18dB minimum threshold. This indicates progressive signal degradation in the optical domain. Root causes: 1) Optical amplifier (EDFA) gain flatness degradation or pump laser aging, 2) Fiber splice loss increase due to environmental stress or mechanical shift, 3) Lambda drift on the transmitter laser causing filter misalignment, 4) Connector contamination or micro-bend loss, 5) Accumulated ASE noise from cascaded amplifiers. Check OTDR traces for new loss events and compare amplifier output power against commissioning baselines.",
        "resolution": "1. Run OTDR test on the affected span to identify new loss events or reflections\n2. Compare current EDFA gain and output power against commissioning baseline\n3. Check individual lambda power levels at each ROADM/OXC node along the path\n4. Verify transmitter laser wavelength — if drifted, recalibrate or replace SFP/CFP\n5. Inspect and clean all fiber connectors on the affected span\n6. If splice loss has increased, dispatch fiber team for splice repair using fusion splicer\n7. If amplifier degradation confirmed, replace EDFA pump module\n8. After repair, run full span power equalization and verify OSNR at receiver\n9. Update optical link budget documentation",
        "severity": "Major", "domain": "Transport",
    },
    {
        "alarm": "Ethernet OAM CFM fault detected on backhaul ring {ring_id} — CCM loss from MEP {mep_id}",
        "diagnosis": "Ethernet OAM Connectivity Fault Management (IEEE 802.1ag) has detected a fault on backhaul ring {ring_id}. Continuity Check Messages (CCM) from MEP {mep_id} are no longer being received. This indicates a connectivity break in the Ethernet backhaul ring. Root causes: 1) Physical link failure on one segment of the ring, 2) SFP module failure or degradation on an intermediate switch, 3) VLAN tagging mismatch causing CFM frames to be dropped, 4) Ethernet OAM misconfiguration (wrong MD level, MA name), 5) Switch/router port failure or software bug. Link trace and loopback tests should be used to isolate the faulty segment.",
        "resolution": "1. Run Ethernet OAM link trace (LTM/LTR) from the reporting MEP to locate the fault point\n2. Execute loopback test (LBM/LBR) at each intermediate MIP to isolate the faulty segment\n3. Check SFP module status and optical power (Tx/Rx) on all ring nodes\n4. Verify VLAN tagging is consistent — CFM frames must traverse the same VLAN as service\n5. Check for CRC errors and interface counters on all ring ports\n6. If SFP failure, replace with compatible module and verify link\n7. Verify CFM configuration: MD level, MA name, MEP ID, CCM interval\n8. If ring protection (G.8032/ERPS) activated, verify traffic is on backup path\n9. After repair, confirm CCM restoration and clear the fault alarm",
        "severity": "Critical", "domain": "Transport",
    },
    {
        "alarm": "Microwave link RSL below threshold on hop {hop_id} — RSL at {rsl_val}dBm (threshold: {rsl_threshold}dBm)",
        "diagnosis": "Received Signal Level (RSL) on microwave hop {hop_id} has dropped to {rsl_val}dBm, below the configured threshold of {rsl_threshold}dBm. The link may be operating at reduced modulation (adaptive modulation fallback) or experiencing bit errors. Root causes: 1) Rain fade — atmospheric attenuation due to precipitation (especially on links >15GHz), 2) Antenna misalignment caused by wind, tower movement, or mounting hardware loosening, 3) Equipment aging — transmitter power amplifier degradation or receiver LNA noise figure increase, 4) Co-channel or adjacent channel interference from a newly activated link, 5) Obstruction in the Fresnel zone (new building, vegetation growth). Check ATPC (Automatic Transmit Power Control) status and weather conditions.",
        "resolution": "1. Check current weather conditions — if heavy rain, monitor for recovery as rain subsides\n2. Verify ATPC is enabled and transmitter has reached maximum power\n3. Check if adaptive modulation has downshifted — note current vs nominal modulation\n4. Review antenna alignment records and compare current RSL with clear-sky baseline\n5. If misalignment suspected, dispatch tower crew for alignment verification using alignment tool\n6. Check for new obstructions in the Fresnel zone (construction, vegetation)\n7. Verify no new microwave links have been activated on same/adjacent frequency\n8. If equipment aging, compare Tx power output against spec — replace if degraded\n9. Run frequency coordination check with regulator database\n10. After resolution, update link budget documentation",
        "severity": "Major", "domain": "Transport",
    },
    {
        "alarm": "VLAN mismatch causing service isolation on interface {interface_id} — expected VLAN {vlan_expected}, received VLAN {vlan_received}",
        "diagnosis": "A VLAN mismatch has been detected on interface {interface_id}. Expected VLAN tag {vlan_expected} but receiving frames with VLAN {vlan_received}. This is causing service isolation — affected subscribers or network elements cannot communicate. Root causes: 1) Tagged/untagged VLAN mismatch — one end configured as access port, other as trunk, 2) QinQ (802.1ad) outer VLAN misconfiguration in carrier Ethernet network, 3) Native VLAN conflict — different native VLAN configured on trunk link ends, 4) VLAN database inconsistency after switch replacement or config restore, 5) VLAN pruning or allowed VLAN list filtering the required VLAN. This commonly occurs after network changes or equipment replacement.",
        "resolution": "1. Verify VLAN configuration end-to-end — check both ends of the affected link\n2. Check trunk port allowed VLAN list — ensure required VLAN is permitted\n3. Verify native VLAN matches on both ends of trunk links\n4. For QinQ deployments, check S-VLAN (outer) and C-VLAN (inner) mapping\n5. Compare VLAN database across all switches in the path (show vlan brief)\n6. Check if VLAN is created in the VLAN database on all intermediate switches\n7. Verify switchport mode (access/trunk/hybrid) matches the design\n8. If recently replaced equipment, compare running config against design document\n9. Test with packet capture to confirm VLAN tags in both directions\n10. Update network documentation with correct VLAN assignments",
        "severity": "Major", "domain": "Transport",
    },
    {
        "alarm": "SD-WAN overlay tunnel flapping on circuit {circuit_id} — {flap_count} state changes in {time_period}",
        "diagnosis": "SD-WAN overlay tunnel on circuit {circuit_id} is experiencing instability with {flap_count} up/down transitions in {time_period}. This is disrupting application-aware routing and causing traffic rerouting. Root causes: 1) IPsec tunnel instability due to IKE/DPD timer misconfiguration or rekeying failures, 2) Underlay WAN quality degradation — packet loss, latency, or jitter exceeding SLA thresholds, 3) MTU issues causing fragmentation of IPsec-encapsulated packets (overhead ~60-80 bytes), 4) NAT/firewall on underlay path causing UDP port 4500 or ESP blocking, 5) Asymmetric routing on underlay causing DPD failures, 6) Underlap path flapping (BGP/OSPF instability on MPLS underlay).",
        "resolution": "1. Check underlay WAN path quality — measure loss, latency, jitter on the affected circuit\n2. Verify DPD (Dead Peer Detection) timer settings — increase interval if too aggressive\n3. Check MTU end-to-end — set tunnel MTU to account for IPsec overhead (recommend 1400)\n4. Enable DF-bit clear and PMTUD on the tunnel interface\n5. Verify NAT traversal (NAT-T) is enabled if NAT exists in the path\n6. Check IKE SA and IPsec SA rekey statistics for failures\n7. Review SD-WAN controller logs for policy changes affecting the tunnel\n8. If underlay is MPLS, check with carrier for CE-PE link stability\n9. Consider adjusting SLA probe thresholds if too sensitive\n10. Enable tunnel keepalive dampening to prevent rapid oscillation",
        "severity": "Major", "domain": "Transport",
    },
    {
        "alarm": "Segment routing path computation failure — SR-TE policy {policy_name} not computed on headend {router_id}",
        "diagnosis": "Segment Routing Traffic Engineering (SR-TE) policy {policy_name} cannot be computed on headend router {router_id}. The preferred path is not being installed in the forwarding table. Root causes: 1) PCE (Path Computation Element) unreachable — PCEP session down between PCC and PCE, 2) Missing SID (Segment Identifier) labels on intermediate nodes — prefix-SID or adjacency-SID not allocated, 3) SRGB (Segment Routing Global Block) or SRLB (Segment Routing Local Block) range mismatch between nodes, 4) SR topology database incomplete — missing links or nodes in the TED, 5) Bandwidth constraints cannot be satisfied on any valid path, 6) Affinity/color constraints excluding all possible paths.",
        "resolution": "1. Check PCEP session status between headend (PCC) and PCE — verify TCP port 4189\n2. Verify PCE has complete topology view — check TED (Traffic Engineering Database)\n3. Validate SRGB range is consistent across all nodes in the SR domain (default: 16000-23999)\n4. Verify SRLB range does not overlap with SRGB on any node\n5. Check that prefix-SIDs are allocated on all nodes in the intended path\n6. Verify adjacency-SIDs are allocated for any explicit-path segments\n7. Check SR-TE policy constraints — relax affinity/metric constraints if too restrictive\n8. Verify IS-IS/OSPF SR extensions are enabled and advertising SIDs\n9. If PCE-initiated, check PCE policy configuration and delegation status\n10. Use SR-TE path verification command to debug computation step by step",
        "severity": "Critical", "domain": "Transport",
    },
    {
        "alarm": "QoS policy causing packet drops on {interface_type} interface {interface_id} — {drop_count} drops/sec in queue {queue_name}",
        "diagnosis": "Quality of Service policy on {interface_type} interface {interface_id} is causing {drop_count} packet drops per second in queue {queue_name}. This is impacting service quality on the S1/N3 bearer path. Root causes: 1) Traffic shaping rate configured too low for actual traffic volume, 2) Policer (single-rate or two-rate) dropping traffic exceeding committed/peak rate, 3) Incorrect DSCP marking causing traffic to be classified into wrong queue (e.g., GBR traffic in best-effort queue), 4) Queue depth (buffer) too small for bursty traffic patterns, 5) Scheduling weight misconfiguration — low-priority queue starving, 6) Aggregate traffic exceeding interface bandwidth after QoS overhead.",
        "resolution": "1. Identify which QoS class/queue is experiencing drops — check queue statistics\n2. Verify DSCP marking on ingress — ensure GTP-encapsulated traffic has correct DSCP\n3. Check QoS classification rules — verify 5QI-to-DSCP mapping matches transport policy\n4. Review policer rates — CIR/PIR should match provisioned bandwidth for the service\n5. Increase queue depth (buffer size) for bursty traffic classes if hardware supports it\n6. Verify scheduling weights — WFQ/DWRR weights should reflect service priority\n7. Check interface utilization — if near capacity, consider bandwidth upgrade\n8. For S1/N3 interface, ensure QCI=1 (voice) traffic has strict priority queuing\n9. Verify DSCP is preserved across all hops (no re-marking by intermediate devices)\n10. Run packet capture to confirm marking and classification at each hop",
        "severity": "Major", "domain": "Transport",
    },

    # ---- Core Network Domain (8 new scenarios, bringing total from 6 to 14) ----
    {
        "alarm": "UPF {upf_id} throughput degradation — N3 interface utilization at {util}%, packet processing latency {latency}ms",
        "diagnosis": "User Plane Function {upf_id} is experiencing throughput degradation. N3 interface utilization is at {util}% and packet processing latency has increased to {latency}ms (normal <1ms). Root causes: 1) CPU bottleneck on UPF — packet processing threads saturated, 2) N3 (gNB-to-UPF) or N6 (UPF-to-DN) interface congestion, 3) GTP-U tunnel encapsulation/decapsulation overhead consuming excessive resources, 4) FAR (Forwarding Action Rules) table too large causing slow lookups, 5) Memory exhaustion from excessive PDR (Packet Detection Rules) entries, 6) NIC hardware offload failure causing software fallback processing.",
        "resolution": "1. Check UPF CPU utilization per core — identify if specific packet processing threads are saturated\n2. Monitor N3 and N6 interface utilization — if >80%, consider adding interfaces or increasing bandwidth\n3. Review FAR/PDR/QER rule counts — if excessive, optimize or consolidate rules\n4. Check if NIC hardware offload (RSS, GRO, GSO) is enabled and functioning\n5. Verify NUMA alignment — ensure packet processing cores are on same NUMA node as NIC\n6. Check for memory leaks — monitor UPF memory usage trend\n7. Review GTP-U tunnel count vs dimensioned capacity\n8. If DPDK-based UPF, check hugepage allocation and ring buffer sizes\n9. Consider horizontal scaling — add UPF instance and redistribute sessions via SMF\n10. Collect UPF performance metrics and escalate to vendor if hardware limits reached",
        "severity": "Critical", "domain": "Core",
    },
    {
        "alarm": "NRF {nrf_id} NF discovery failure — {nf_type} profile query returning empty results",
        "diagnosis": "Network Repository Function {nrf_id} is failing to return NF profiles for {nf_type} discovery queries. Other NFs cannot discover and select the requested service. Root causes: 1) NF instance not registered with NRF — registration failed or deregistered due to heartbeat timeout, 2) NRF overload — too many discovery requests causing query timeouts, 3) OAuth2 access token expired — requesting NF cannot authenticate to NRF, 4) NF profile query parameters mismatch (PLMN, S-NSSAI, DNN filters too restrictive), 5) NRF database corruption or replication lag in geo-redundant deployment.",
        "resolution": "1. Check NF registration status — verify {nf_type} instances are registered with NRF\n2. Query NRF API directly: GET /nnrf-nfm/v1/nf-instances?nf-type={nf_type}\n3. If NF not registered, check NF heartbeat/subscription — re-register if needed\n4. Verify OAuth2 token validity — check token expiry and refresh mechanism\n5. Check NRF CPU/memory — if overloaded, scale out or enable request throttling\n6. Review NF discovery query parameters — relax filters if too restrictive\n7. Verify NRF database replication status in geo-redundant setup\n8. Check SBI (Service Based Interface) connectivity — NF must reach NRF via HTTP/2\n9. Review NRF access logs for 401/403/429 error responses\n10. If persistent, restart NRF service and verify all NF re-registration",
        "severity": "Critical", "domain": "Core",
    },
    {
        "alarm": "NSSF network slice selection failure — S-NSSAI {snssai} not available in TAI {tai}",
        "diagnosis": "Network Slice Selection Function (NSSF) is failing to select a network slice for S-NSSAI {snssai} in Tracking Area Identity {tai}. UEs requesting this slice are being rejected. Root causes: 1) S-NSSAI {snssai} not configured in the NSSF for the requested TAI, 2) NSSF policy mismatch — slice availability differs by location/time, 3) TAI-to-slice mapping error in NSSF configuration, 4) NSI (Network Slice Instance) for the requested S-NSSAI is not deployed or is in maintenance, 5) AMF did not include Requested NSSAI correctly in Nssf_NSSelection request, 6) Allowed NSSAI for the UE subscription does not include the requested S-NSSAI.",
        "resolution": "1. Verify NSSF configuration — check that S-NSSAI {snssai} is defined for TAI {tai}\n2. Check allowed NSSAI in UE subscription data (UDM) — verify slice is in subscription\n3. Validate TAI-to-NSI mapping table in NSSF\n4. Check NSI deployment status — verify the slice instance is active and healthy\n5. Review AMF Nssf_NSSelection request parameters for correctness\n6. Check NSSF policy rules — verify time/location-based restrictions\n7. Verify configured NSSAI vs subscribed NSSAI vs requested NSSAI alignment\n8. If new slice, ensure end-to-end provisioning is complete (NSSF, AMF, SMF, UPF)\n9. Test with known-good UE subscription to isolate NSSF vs subscription issue\n10. Review 3GPP TS 29.531 for correct NSSF API usage",
        "severity": "Major", "domain": "Core",
    },
    {
        "alarm": "5G roaming failure via SEPP — N32 interface down between home PLMN {hplmn} and visited PLMN {vplmn}",
        "diagnosis": "Security Edge Protection Proxy (SEPP) is reporting N32 interface failure between home PLMN {hplmn} and visited PLMN {vplmn}. Inbound roamers from {vplmn} cannot register, and outbound roamers to {vplmn} lose service. Root causes: 1) N32-c (control) or N32-f (forwarding) TLS connection failure, 2) PRINS (Protocol for N32 Interconnect Security) negotiation failure, 3) TLS certificate expiry or CA trust chain issue, 4) PLMN-level filtering policy rejecting the partner PLMN, 5) IP connectivity issue between SEPPs (firewall, DNS, routing), 6) SEPP capacity exhaustion or software fault.",
        "resolution": "1. Check SEPP N32-c and N32-f connection status to partner PLMN {vplmn}\n2. Verify TLS certificate validity — check expiry dates for both local and remote certificates\n3. Validate CA trust chain — ensure partner SEPP certificate is signed by a trusted CA\n4. Check PRINS security policy negotiation — verify both sides agree on protection policy\n5. Test IP connectivity to partner SEPP (ping, traceroute, TCP port check)\n6. Review PLMN filtering rules — ensure {vplmn} is in the allowed roaming partner list\n7. Check DNS resolution for partner SEPP FQDN\n8. Verify roaming agreement parameters match between both PLMNs\n9. Review SEPP logs for specific TLS/PRINS error codes\n10. Coordinate with partner PLMN NOC for joint troubleshooting if needed",
        "severity": "Critical", "domain": "Core",
    },
    {
        "alarm": "N3IWF authentication failure for non-3GPP access — IKEv2/EAP-AKA failure rate {threshold}% from WiFi AP group {ap_group}",
        "diagnosis": "Non-3GPP Interworking Function (N3IWF) is reporting {threshold}% authentication failure rate for UEs accessing 5G core via WiFi through AP group {ap_group}. Users cannot complete WiFi-to-5G handover or initial WiFi offload. Root causes: 1) IKEv2 SA establishment failure between UE and N3IWF, 2) EAP-AKA/EAP-AKA' authentication failure — AUSF/UDM returning authentication reject, 3) UE credentials mismatch — IMSI/SUPI not provisioned for non-3GPP access, 4) WiFi AP configuration error — incorrect N3IWF address or certificate, 5) NAS signaling failure over the IKEv2 tunnel, 6) IPsec child SA negotiation failure (cipher suite mismatch).",
        "resolution": "1. Check N3IWF logs for IKEv2 error codes (AUTHENTICATION_FAILED, NO_PROPOSAL_CHOSEN)\n2. Verify EAP-AKA/EAP-AKA' exchange — check AUSF logs for authentication vectors\n3. Confirm UE subscription includes non-3GPP access authorization in UDM\n4. Verify WiFi AP SSID is correctly configured with N3IWF discovery (ANQP/HS2.0)\n5. Check N3IWF certificate validity and trust chain on UE side\n6. Verify IPsec cipher suite proposals match between UE and N3IWF\n7. Test with specific UEs to isolate device-specific vs network-wide issue\n8. Check N3IWF to AMF (N2) and N3IWF to UPF (N3) connectivity\n9. Verify NAS security algorithm negotiation over the IKEv2 tunnel\n10. Review 3GPP TS 24.502 for correct non-3GPP access procedure",
        "severity": "Major", "domain": "Core",
    },
    {
        "alarm": "CHF offline charging CDR loss detected — {cdr_count} CDRs missing from batch transfer on CHF {chf_id}",
        "diagnosis": "Charging Function {chf_id} has detected loss of {cdr_count} offline charging CDRs (Call Detail Records) during batch file transfer. Revenue assurance is impacted — untallied usage means unbilled traffic. Root causes: 1) CDR file transfer failure via SFTP/FTPS to billing mediation system, 2) CHF local storage disk full — new CDRs overwriting unsent batches, 3) SFTP connectivity issue between CHF and billing mediation (firewall, credential, network), 4) CDR file corruption during generation or transfer, 5) UPF usage reporting (URR) failure causing missing input to CHF, 6) CHF process crash during CDR generation losing in-memory records.",
        "resolution": "1. Check CHF local storage — verify disk space and CDR file integrity\n2. Verify SFTP/FTPS connectivity to billing mediation system\n3. Check SFTP credentials (SSH keys or password) — renew if expired\n4. Review CDR batch transfer logs for failed transfers and retry them\n5. Check for CDR files stuck in pending/failed directory on CHF\n6. Verify UPF usage reporting (URR) is sending reports to CHF correctly\n7. Recover lost CDRs from UPF if URR data is still available\n8. Check CHF process health — restart if memory leak or crash detected\n9. Implement CDR reconciliation between CHF and billing mediation\n10. Enable CDR backup/replication to prevent future losses\n11. Report to revenue assurance team with affected time period and estimated impact",
        "severity": "Critical", "domain": "Core",
    },
    {
        "alarm": "NEF API exposure throttling — AF {af_id} rate limited at {rate_limit} req/sec on capability {capability}",
        "diagnosis": "Network Exposure Function (NEF) is throttling API requests from Application Function {af_id}. The AF is being rate-limited at {rate_limit} requests per second for capability {capability}. Third-party applications depending on this exposure are experiencing failures. Root causes: 1) AF exceeding configured API quota — sending requests above the agreed rate, 2) NEF global rate limit reached due to cumulative load from multiple AFs, 3) Capability exposure policy misconfigured — rate limit set too low for the use case, 4) AF registration in NRF has incorrect service level/priority, 5) Backend NF (PCF, AMF, UDM) responding slowly causing NEF queue buildup.",
        "resolution": "1. Review NEF rate limiting policy for AF {af_id} — check configured quota vs actual usage\n2. Check API request logs — verify AF is not sending duplicate or unnecessary requests\n3. If legitimate traffic growth, increase API quota for the AF in NEF policy\n4. Verify AF registration status in NRF — check service level and priority\n5. Monitor NEF backend NF response times — if slow, investigate backend bottleneck\n6. Check NEF CPU/memory — if near capacity, scale out NEF instances\n7. Review API SLA agreement with AF provider\n8. Enable API response caching on NEF for read-heavy queries\n9. Consider implementing API batching for bulk operations\n10. Update NEF monitoring to alert before quota exhaustion",
        "severity": "Major", "domain": "Core",
    },
    {
        "alarm": "EPC-5GC interworking failure — N26 interface down between MME {mme_id} and AMF {amf_id}",
        "diagnosis": "N26 interface between MME {mme_id} (4G EPC) and AMF {amf_id} (5G Core) is down. UEs cannot perform seamless handover between 4G and 5G networks. Impact: 4G-to-5G and 5G-to-4G handovers fail, UEs must re-attach when moving between RATs. Root causes: 1) N26 SCTP association failure between MME and AMF, 2) Interworking Function (IWF) configuration mismatch, 3) Security context transfer failure (mapped security context), 4) EPS bearer to QoS flow mapping error, 5) UE does not support N1 mode in 5G — capability mismatch, 6) TAI/TAC mapping between EPC tracking areas and 5GC tracking areas incorrect.",
        "resolution": "1. Check N26 interface SCTP association status on both MME and AMF\n2. Verify interworking function configuration — EPS bearer to QoS flow mapping\n3. Check UE 5G capability — verify UE supports N1 mode and inter-RAT handover\n4. Validate security context mapping between EPS and 5G NAS security\n5. Verify TAI mapping between 4G tracking areas and 5G registration areas\n6. Check S10/N26 protocol message traces for specific error codes\n7. Test with specific UE models to isolate device vs network issue\n8. Verify MME and AMF are configured as interworking peers\n9. Check that both MME and AMF have consistent subscriber data from HSS/UDM\n10. Review 3GPP TS 23.502 Section 4.11 for interworking procedure requirements",
        "severity": "Critical", "domain": "Core",
    },

    # ---- IMS/VoLTE Domain (5 new scenarios, bringing total from 3 to 8) ----
    {
        "alarm": "SRVCC handover failure rate {threshold}% from VoLTE to 3G in region {region}",
        "diagnosis": "Single Radio Voice Call Continuity (SRVCC) handover from VoLTE (4G) to circuit-switched voice (3G/2G) is failing at {threshold}% rate in {region}. Active VoLTE calls are being dropped when UEs move to areas without LTE coverage. Root causes: 1) Sv interface failure between MME and MSC server, 2) Target MSC server unreachable or overloaded, 3) Bearer downgrade failure — IMS-to-CS voice bearer transition issue, 4) STN-SR (Session Transfer Number for SRVCC) routing error in IMS, 5) ATCF (Access Transfer Control Function) unable to anchor media transfer, 6) UE SRVCC capability not correctly indicated in attach.",
        "resolution": "1. Check Sv interface connectivity between MME and MSC server (GTPv2-C)\n2. Verify MSC server is operational and has available CS voice channels\n3. Test SRVCC procedure with specific UEs in controlled conditions\n4. Verify STN-SR is correctly configured in HSS subscriber profile\n5. Check ATCF/ATGW configuration in IMS for media transfer\n6. Verify UE indicates SRVCC capability in Attach Request (UE Network Capability IE)\n7. Review MME SRVCC handover preparation/execution traces\n8. Check if 3G coverage exists in the area where SRVCC is triggered\n9. Verify CS fallback target cell configuration and neighbor relations\n10. If MSC overload, redistribute SRVCC target assignments",
        "severity": "Critical", "domain": "IMS/VoLTE",
    },
    {
        "alarm": "Emergency call (VoLTE 911/112) failure in region {region} — PSAP routing error from E-CSCF {ecscf_id}",
        "diagnosis": "VoLTE emergency calls (911/112) are failing in {region}. The Emergency CSCF (E-CSCF) {ecscf_id} is unable to route calls to the correct PSAP (Public Safety Answering Point). This is a critical safety issue requiring immediate attention. Root causes: 1) PSAP routing table error or outdated civic address mapping, 2) Location information missing — GMLC (Gateway Mobile Location Centre) not providing UE location, 3) E-CSCF failure or misconfiguration, 4) LRF (Location Retrieval Function) database outdated, 5) Emergency bearer (QCI=1 with ARP=1) not being established, 6) ESRP (Emergency Services Routing Proxy) connectivity failure.",
        "resolution": "1. IMMEDIATE: Verify E-CSCF {ecscf_id} process status and restart if needed\n2. Check PSAP routing table — verify civic address to PSAP mapping is current\n3. Verify GMLC is providing location information (cell-ID, GPS coordinates)\n4. Test emergency call routing with known location to validate path\n5. Check LRF database for completeness and recent updates\n6. Verify emergency PDU session/bearer establishment (QCI=1, ARP priority=1)\n7. Check ESRP connectivity and SIP routing rules for emergency URN (urn:service:sos)\n8. Verify P-CSCF is correctly identifying emergency calls and routing to E-CSCF\n9. Coordinate with PSAP operators to confirm their receiving equipment is operational\n10. Document incident and notify regulatory authority as required by local regulations\n11. IMPORTANT: Maintain CS fallback for 911 until VoLTE emergency routing is verified",
        "severity": "Critical", "domain": "IMS/VoLTE",
    },
    {
        "alarm": "RCS messaging delivery failure — message store error on RCS AS {rcs_as_id}, {failure_count} undelivered messages",
        "diagnosis": "Rich Communication Services (RCS) messaging is experiencing delivery failures on Application Server {rcs_as_id}. {failure_count} messages are stuck undelivered. Root causes: 1) Message store backend (database/object storage) failure or full, 2) Group chat session timeout — MSRP sessions expiring before message delivery, 3) Content server unreachable — multimedia attachments cannot be uploaded/downloaded, 4) SIP MESSAGE or MSRP relay failure, 5) RCS auto-configuration server returning incorrect settings to clients, 6) Push notification service failure preventing message delivery notification.",
        "resolution": "1. Check RCS application server {rcs_as_id} health — CPU, memory, process status\n2. Verify message store backend — check database connectivity and disk space\n3. Check content/media server accessibility — test upload/download of attachments\n4. Review MSRP relay logs for session timeouts or connection failures\n5. Verify group chat session state — check for orphaned or stuck sessions\n6. Test RCS auto-configuration (HTTP config server) for correct client settings\n7. Check push notification service integration (FCM/APNs) for delivery confirmations\n8. Retry delivery of stuck messages after resolving backend issues\n9. If message store full, archive old messages and expand storage\n10. Monitor delivery success rate after resolution for 24 hours",
        "severity": "Major", "domain": "IMS/VoLTE",
    },
    {
        "alarm": "IMS conference call bridge failure — MRFC {mrfc_id} resource exhaustion, {active_conf} active conferences at capacity",
        "diagnosis": "IMS conference call bridge on MRFC (Media Resource Function Controller) {mrfc_id} has reached capacity with {active_conf} active conferences. New conference requests are being rejected and existing conferences may experience quality degradation. Root causes: 1) MRFC/MRFP (Media Resource Function Processor) resource exhaustion — DSP/CPU/memory at capacity, 2) SDP (Session Description Protocol) negotiation failure with multiple parties — codec mismatch, 3) Overbooking of conference resources — more simultaneous conferences than dimensioned, 4) MRFP media processing failure — transcoding or mixing engine crash, 5) Overbooking due to missing conference resource reservation.",
        "resolution": "1. Check MRFC {mrfc_id} resource utilization — DSP, CPU, memory, active sessions\n2. Check MRFP media processing status — verify transcoding engines are operational\n3. Review active conference count vs licensed/dimensioned capacity\n4. If at capacity, enable graceful rejection with user-friendly announcement\n5. Check SDP offers from conference participants — verify codec compatibility\n6. Verify media resource allocation between MRFC and MRFP (Mp interface)\n7. Consider load balancing conferences across multiple MRFC/MRFP pairs\n8. Review conference scheduling to identify peak usage patterns\n9. If MRFP crash, collect core dumps and escalate to vendor\n10. Plan capacity expansion based on conference usage trend analysis",
        "severity": "Major", "domain": "IMS/VoLTE",
    },
    {
        "alarm": "SBC registration storm after network recovery — {reg_rate} REGISTER/sec on SBC {sbc_id} (normal: {normal_rate}/sec)",
        "diagnosis": "Session Border Controller {sbc_id} is experiencing a registration storm with {reg_rate} SIP REGISTER requests per second (normal baseline: {normal_rate}/sec). This is occurring after a network recovery event and is at risk of overwhelming the SBC and downstream IMS components. Root causes: 1) Mass simultaneous IMS re-registration after network outage recovery, 2) TCP/TLS connection exhaustion on SBC due to high concurrent connection count, 3) SBC CPU/memory overload from processing excessive REGISTER requests, 4) Downstream P-CSCF/I-CSCF unable to handle the registration burst, 5) Registration timer (Expires header) synchronized across all UEs causing thundering herd, 6) SBC connection table full — new TCP connections being rejected.",
        "resolution": "1. Enable SBC rate limiting — cap REGISTER processing to sustainable rate\n2. Implement registration throttling with 503 + Retry-After header (randomized backoff)\n3. Increase SBC TCP connection pool size if possible\n4. Stagger re-registration timers — configure randomized Expires offset in 200 OK response\n5. Monitor SBC CPU/memory — enable overload protection mode if thresholds exceeded\n6. Check downstream P-CSCF capacity — enable cascaded overload control\n7. Temporarily increase SBC worker threads/processes\n8. If persistent, enable registration caching on SBC to reduce load on I-CSCF/S-CSCF\n9. After storm subsides, verify all UEs successfully re-registered\n10. Post-incident: configure registration randomization to prevent future storms\n11. Review SBC dimensioning for post-outage recovery scenarios",
        "severity": "Critical", "domain": "IMS/VoLTE",
    },
]


# =============================================================================
# 2. NEW INTENT-TO-CONFIG PAIRS FOR V3 (10 new templates)
# =============================================================================

V3_INTENT_CONFIG_PAIRS = [
    {
        "intent": "Create a network slice for video surveillance requiring eMBB with high uplink throughput",
        "config": """network_slice:
  name: video-surveillance-slice
  sst: 1  # eMBB
  sd: "0x000020"
  description: "eMBB slice optimized for high uplink video surveillance traffic"
  qos_profile:
    5qi: 7  # Non-GBR, video
    priority_level: 3
    packet_delay_budget_ms: 100
    packet_error_rate: 1e-3
  resource_allocation:
    guaranteed_bitrate_dl: 5Mbps
    guaranteed_bitrate_ul: 50Mbps   # High uplink for video upload
    max_bitrate_dl: 20Mbps
    max_bitrate_ul: 100Mbps
  uplink_optimization:
    ul_scheduling_priority: high
    ul_grant_type: configured_grant  # Semi-persistent for stable UL streams
    ul_mimo_layers: 2
    pusch_aggregation_factor: 1
  device_params:
    max_devices_per_cell: 200
    always_on_pdu_session: true
  isolation: soft
  monitoring:
    kpis: [ul_throughput, ul_packet_loss, e2e_latency]
    reporting_interval_sec: 60""",
    },
    {
        "intent": "Configure CUPS (Control/User Plane Separation) for distributed UPF deployment",
        "config": """cups_deployment:
  description: "Control/User Plane Separation with central SMF and distributed UPFs"
  control_plane:
    smf:
      name: smf-central-01
      location: central_dc
      interfaces:
        n11:
          ip: 10.0.1.10
          connected_amf: amf-central-01
        n7:
          ip: 10.0.1.11
          connected_pcf: pcf-central-01
      pfcp_endpoints:  # N4 to multiple UPFs
        - upf: edge-upf-01
          ip: 10.100.1.1
          heartbeat_interval_sec: 10
        - upf: edge-upf-02
          ip: 10.100.2.1
          heartbeat_interval_sec: 10
        - upf: regional-upf-01
          ip: 10.200.1.1
          heartbeat_interval_sec: 10
  user_plane:
    edge_upfs:
      - name: edge-upf-01
        location: edge_site_a
        n3_ip: 10.100.1.2
        n6_ip: 192.168.1.1
        n9_ip: 10.100.1.3
        capacity:
          max_sessions: 20000
          max_throughput_gbps: 5
        local_breakout: true
        dnns: [internet, edge-apps]
      - name: edge-upf-02
        location: edge_site_b
        n3_ip: 10.100.2.2
        n6_ip: 192.168.2.1
        n9_ip: 10.100.2.3
        capacity:
          max_sessions: 20000
          max_throughput_gbps: 5
        local_breakout: true
        dnns: [internet, edge-apps]
    regional_upf:
      name: regional-upf-01
      location: regional_dc
      n3_ip: 10.200.1.2
      n6_ip: 172.16.0.1
      n9_ip: 10.200.1.3
      capacity:
        max_sessions: 200000
        max_throughput_gbps: 40
      dnns: [internet, ims, enterprise]
  selection_policy:
    criteria: [dnn, location, load]
    prefer_local_breakout: true
    fallback_to_regional: true""",
    },
    {
        "intent": "Set up N3IWF for WiFi-to-5G non-3GPP access integration",
        "config": """n3iwf_config:
  name: n3iwf-01
  description: "Non-3GPP Interworking Function for WiFi offload to 5G Core"
  interfaces:
    n2:
      ip: 10.50.1.10
      connected_amf: amf-01
      sctp_port: 38412
    n3:
      ip: 10.50.2.10
      connected_upf: upf-01
      gtp_port: 2152
    nwu:  # UE-facing IPsec tunnel endpoint
      ip: 203.0.113.50
      ikev2_port: 500
      nat_traversal_port: 4500
  ipsec:
    ike_version: 2
    authentication: eap-aka-prime
    encryption: [aes-256-gcm, aes-128-gcm]
    integrity: [sha256, sha384]
    dh_groups: [14, 19, 20]
    ike_lifetime_sec: 86400
    child_sa_lifetime_sec: 3600
    dpd_interval_sec: 30
    dpd_retry_count: 5
  eap:
    method: eap-aka-prime  # 5G authentication
    identity_request: permanent  # SUPI
    realm: "nai.5gc.mnc001.mcc310.3gppnetwork.org"
  nas_over_ikev2:
    enabled: true
    security_algorithms:
      encryption: [nea1, nea2]
      integrity: [nia1, nia2]
  wifi_integration:
    discovery: anqp  # Access Network Query Protocol
    hotspot20: true
    ssid_list: ["5G-WiFi-Offload", "Carrier-WiFi"]
  capacity:
    max_ipsec_tunnels: 50000
    max_throughput_gbps: 10""",
    },
    {
        "intent": "Configure SBA (Service Based Architecture) NF registration in NRF",
        "config": """nrf_registration:
  nrf:
    name: nrf-01
    api_endpoint: "https://nrf.5gc.mnc001.mcc310.3gppnetwork.org"
    api_version: v1
    oauth2:
      enabled: true
      token_endpoint: "/oauth2/token"
      grant_type: client_credentials
      token_validity_sec: 3600
  nf_profiles:
    - nf_type: AMF
      nf_instance_id: "amf-01-uuid"
      nf_status: REGISTERED
      plmn_list:
        - mcc: "310"
          mnc: "001"
      amf_info:
        amf_set_id: "001"
        amf_region_id: "01"
        guami_list:
          - plmn_id: {mcc: "310", mnc: "001"}
            amf_id: "010001"
        tai_list:
          - plmn_id: {mcc: "310", mnc: "001"}
            tac: "000001"
      sbi_endpoint: "https://amf-01.5gc.local:8443"
      services:
        - name: namf-comm
          versions: [{api_version: v1, expiry: "2027-12-31"}]
          scheme: https
          fqdn: "amf-01.5gc.local"
        - name: namf-evts
          versions: [{api_version: v1, expiry: "2027-12-31"}]
          scheme: https
          fqdn: "amf-01.5gc.local"
      heartbeat_timer_sec: 30
      priority: 1
      capacity: 1000
    - nf_type: SMF
      nf_instance_id: "smf-01-uuid"
      nf_status: REGISTERED
      smf_info:
        s_nssai_smf_info:
          - s_nssai: {sst: 1}
            dnn_list: [internet, ims]
          - s_nssai: {sst: 2}
            dnn_list: [urllc-service]
      sbi_endpoint: "https://smf-01.5gc.local:8443"
      services:
        - name: nsmf-pdusession
          versions: [{api_version: v1}]
          scheme: https
      heartbeat_timer_sec: 30
  discovery_config:
    cache_ttl_sec: 300
    preferred_locality: same_dc
    failover_to_remote: true""",
    },
    {
        "intent": "Set up 5G LAA (License Assisted Access) on n46 band for supplemental downlink",
        "config": """laa_config:
  description: "License Assisted Access on n46 band (5GHz unlicensed) as supplemental DL carrier"
  primary_cell:
    nr_band: n78
    channel_bandwidth_mhz: 100
    subcarrier_spacing_khz: 30
    duplex_mode: TDD
    role: pcell
  laa_secondary_cell:
    nr_band: n46
    channel_bandwidth_mhz: 20
    center_frequency_mhz: 5190  # UNII-1 channel
    subcarrier_spacing_khz: 15
    duplex_mode: TDD
    role: scell
  lbt:  # Listen Before Talk (mandatory for unlicensed)
    enabled: true
    type: cat4  # Category 4 LBT with random backoff
    energy_detection_threshold_dbm: -72
    defer_period_us: 25  # DIFS equivalent
    contention_window:
      min: 15
      max: 1023
    max_channel_occupancy_time_ms: 8
  coexistence:
    wifi_friendly: true
    cca_threshold_dbm: -62
    transmission_burst_max_ms: 4
    duty_cycle_limit_percent: 50
  carrier_aggregation:
    activation: event_triggered
    activation_threshold_prb_util: 60
    deactivation_threshold_prb_util: 20
    scell_deactivation_timer_ms: 5120
  power:
    max_eirp_dbm: 23  # Regulatory limit for 5GHz indoor
    power_control: open_loop
  deployment: indoor_small_cell""",
    },
    {
        "intent": "Configure NWDAF (Network Data Analytics Function) for anomaly detection",
        "config": """nwdaf_config:
  name: nwdaf-01
  description: "Network Data Analytics Function for real-time anomaly detection"
  nf_registration:
    nrf_endpoint: "https://nrf.5gc.local"
    analytics_info:
      supported_events:
        - abnormal_behaviour
        - ue_mobility
        - nf_load
        - network_performance
        - service_experience
        - user_data_congestion
  data_collection:
    sources:
      - nf_type: AMF
        events: [ue_registration, ue_mobility, ue_communication]
        collection_mode: streaming
        kafka_topic: amf-events
      - nf_type: SMF
        events: [pdu_session, qos_monitoring]
        collection_mode: streaming
        kafka_topic: smf-events
      - nf_type: UPF
        events: [usage_report, qos_report]
        collection_mode: batch
        collection_interval_sec: 60
      - nf_type: NRF
        events: [nf_status_change, nf_load]
        collection_mode: notification
    data_pipeline:
      message_broker: kafka
      kafka_bootstrap: "kafka.analytics.local:9092"
      schema_registry: "http://schema-registry.analytics.local:8081"
  anomaly_detection:
    models:
      - name: signaling_storm_detector
        type: time_series_anomaly
        input: registration_request_rate
        algorithm: isolation_forest
        training_window_hours: 168  # 1 week
        detection_threshold: 3_sigma
        alert_action: notify_noc
      - name: throughput_degradation
        type: change_point_detection
        input: cell_throughput
        algorithm: bayesian_online_changepoint
        sensitivity: medium
        alert_action: create_ticket
      - name: slice_sla_violation
        type: threshold_with_prediction
        input: slice_kpi_metrics
        prediction_horizon_min: 30
        alert_action: auto_scale
  output:
    analytics_exposure:
      api_endpoint: "/nnwdaf-analyticsinfo/v1"
      consumers: [pcf-01, nssf-01, oam-server]
    dashboard:
      grafana_endpoint: "http://grafana.analytics.local:3000"
    alerting:
      webhook: "https://noc-alerts.local/api/v1/alerts"
      severity_mapping:
        3_sigma: warning
        4_sigma: major
        5_sigma: critical""",
    },
    {
        "intent": "Set up MEC (Multi-access Edge Computing) application deployment rules",
        "config": """mec_deployment:
  description: "Multi-access Edge Computing platform with application lifecycle management"
  mec_platform:
    name: mec-platform-01
    location: edge_site_a
    coordinates:
      latitude: 40.7128
      longitude: -74.0060
    serving_area:
      tracking_areas: [1001, 1002, 1003]
      coverage_radius_km: 5
  infrastructure:
    compute:
      total_vcpus: 128
      total_memory_gb: 512
      total_storage_gb: 4096
      gpu_available: true
      gpu_type: nvidia_t4
      gpu_count: 4
    networking:
      n6_interface:
        ip: 192.168.10.1
        bandwidth_gbps: 10
      application_network:
        subnet: 10.10.0.0/16
        vlan_range: [100, 200]
  application_rules:
    - app_name: ar-navigation
      app_id: "app-ar-001"
      dns_rule:
        domain: "ar-service.edge.local"
        ip: 10.10.1.10
        ttl: 300
      traffic_rule:
        match:
          source: any_ue
          destination: "ar-service.cloud.example.com"
        action: redirect_to_local
        local_endpoint: 10.10.1.10
      requirements:
        vcpus: 8
        memory_gb: 32
        gpu: 1
        latency_budget_ms: 10
      scaling:
        min_instances: 2
        max_instances: 10
        cpu_threshold_percent: 70
    - app_name: video-analytics
      app_id: "app-video-001"
      dns_rule:
        domain: "video-ai.edge.local"
        ip: 10.10.2.10
        ttl: 300
      traffic_rule:
        match:
          source: video_surveillance_slice
          destination: "video-ai.cloud.example.com"
        action: redirect_to_local
        local_endpoint: 10.10.2.10
      requirements:
        vcpus: 16
        memory_gb: 64
        gpu: 2
        latency_budget_ms: 50
      scaling:
        min_instances: 1
        max_instances: 5
        cpu_threshold_percent: 60
  upf_integration:
    ulcl_rules:
      - match_dnn: internet
        match_destination: 10.10.0.0/16
        action: local_breakout
      - match_dnn: internet
        match_destination: 0.0.0.0/0
        action: forward_to_central
  lifecycle:
    deployment_mode: containerized  # Kubernetes
    registry: "registry.edge.local:5000"
    health_check_interval_sec: 10
    auto_restart: true""",
    },
    {
        "intent": "Configure network slice admission control and SLA monitoring",
        "config": """slice_admission_control:
  description: "Network slice admission control with SLA monitoring and enforcement"
  slices:
    - s_nssai:
        sst: 1
        sd: "0x000001"
      name: embb-premium
      admission:
        max_ue_count: 10000
        max_pdu_sessions: 15000
        max_aggregate_bitrate_dl_gbps: 50
        max_aggregate_bitrate_ul_gbps: 20
        admission_priority: 1
        preemption: enabled
        reservation_percent: 80  # Reserve 80% of max, allow burst to 100%
      sla:
        availability_percent: 99.99
        dl_throughput_per_ue_mbps: 100
        ul_throughput_per_ue_mbps: 50
        latency_ms: 20
        packet_loss_rate: 0.001
      monitoring:
        kpi_collection_interval_sec: 30
        kpis:
          - name: slice_throughput_dl
            threshold_warning_gbps: 40
            threshold_critical_gbps: 48
          - name: slice_throughput_ul
            threshold_warning_gbps: 16
            threshold_critical_gbps: 19
          - name: active_ue_count
            threshold_warning: 8000
            threshold_critical: 9500
          - name: avg_latency_ms
            threshold_warning: 15
            threshold_critical: 19
      enforcement:
        on_sla_violation:
          - action: alert_noc
            severity: major
          - action: increase_resource_allocation
            max_scale_percent: 120
          - action: enable_traffic_shaping
            target: non_premium_traffic
    - s_nssai:
        sst: 2
        sd: "0x000002"
      name: urllc-industrial
      admission:
        max_ue_count: 1000
        max_pdu_sessions: 1000
        max_aggregate_bitrate_dl_gbps: 5
        max_aggregate_bitrate_ul_gbps: 5
        admission_priority: 0  # Highest priority
        preemption: enabled
        reservation_percent: 100  # Hard reservation
      sla:
        availability_percent: 99.999
        latency_ms: 5
        jitter_ms: 1
        packet_loss_rate: 0.000001
      monitoring:
        kpi_collection_interval_sec: 5
        kpis:
          - name: avg_latency_ms
            threshold_warning: 3
            threshold_critical: 4.5
          - name: max_jitter_ms
            threshold_warning: 0.5
            threshold_critical: 0.9
      enforcement:
        on_sla_violation:
          - action: alert_noc
            severity: critical
          - action: isolate_slice_resources
          - action: reroute_traffic_to_backup_path
  global_policy:
    total_capacity_dl_gbps: 100
    total_capacity_ul_gbps: 50
    oversubscription_allowed: false
    inter_slice_priority: [urllc-industrial, embb-premium]""",
    },
    {
        "intent": "Set up inter-PLMN roaming with SEPP N32 interface",
        "config": """sepp_roaming_config:
  description: "SEPP configuration for inter-PLMN roaming via N32 interface"
  local_sepp:
    name: sepp-01
    plmn:
      mcc: "310"
      mnc: "001"
    fqdn: "sepp.5gc.mnc001.mcc310.3gppnetwork.org"
    sbi_endpoint: "https://sepp-01.5gc.local:8443"
    ip: 203.0.113.100
  n32_connections:
    - remote_plmn:
        mcc: "234"
        mnc: "015"
        operator_name: "Partner Operator UK"
      remote_sepp_fqdn: "sepp.5gc.mnc015.mcc234.3gppnetwork.org"
      remote_sepp_ip: 198.51.100.50
      n32c:  # Control plane
        port: 443
        tls:
          version: "1.3"
          cipher_suites: [TLS_AES_256_GCM_SHA384, TLS_AES_128_GCM_SHA256]
          local_cert: "/etc/sepp/certs/sepp-local.pem"
          local_key: "/etc/sepp/certs/sepp-local-key.pem"
          ca_bundle: "/etc/sepp/certs/roaming-ca-bundle.pem"
          verify_peer: true
      n32f:  # Forwarding plane
        port: 8443
        security_policy: PRINS  # Protocol for N32 Interconnect Security
        prins:
          protection_policy:
            - api_name: nausf-auth
              http_method: POST
              protection_level: confidentiality_integrity
            - api_name: nudm-sdm
              http_method: GET
              protection_level: integrity_only
          cipher_suite: aes-256-gcm
      roaming_agreement:
        effective_date: "2026-01-01"
        expiry_date: "2028-12-31"
        allowed_services: [registration, pdu_session, sms]
        data_roaming: enabled
        volte_roaming: enabled
  plmn_filtering:
    mode: allowlist
    allowed_plmns:
      - {mcc: "234", mnc: "015"}
      - {mcc: "262", mnc: "001"}
      - {mcc: "440", mnc: "010"}
    blocked_plmns: []
  topology_hiding:
    enabled: true
    hide_nf_fqdns: true
    hide_nf_ips: true
    replacement_fqdn_pattern: "nf-{uuid}.sepp.{plmn}.3gppnetwork.org"
  rate_limiting:
    per_plmn_rps: 10000
    burst_size: 1000
    action_on_limit: reject_with_429""",
    },
    {
        "intent": "Configure O-RAN near-RT RIC xApp for cell load balancing",
        "config": """oran_ric_xapp:
  description: "O-RAN near-RT RIC xApp for intelligent cell load balancing"
  ric_platform:
    name: near-rt-ric-01
    e2_nodes:
      - gnb_id: gnb-001
        e2_connection: established
        ran_functions: [KPM, RC, CCC]
      - gnb_id: gnb-002
        e2_connection: established
        ran_functions: [KPM, RC, CCC]
  xapp:
    name: cell-load-balancer
    version: "1.2.0"
    image: "registry.oran.local:5000/xapps/load-balancer:1.2.0"
    replicas: 2
  e2_subscriptions:
    - ran_function: KPM  # KPI Monitoring
      event_trigger:
        reporting_period_ms: 1000
      action:
        type: report
        kpis:
          - prb_utilization_dl
          - prb_utilization_ul
          - active_ue_count
          - average_ue_throughput
          - rrc_connected_ue_count
    - ran_function: RC   # RAN Control
      action:
        type: control
        control_actions:
          - handover_trigger
          - cell_parameter_update
  load_balancing_policy:
    algorithm: weighted_proportional_fair
    evaluation_interval_sec: 10
    thresholds:
      overload_prb_util_percent: 80
      underload_prb_util_percent: 30
      max_imbalance_percent: 20
    actions:
      - type: handover_optimization
        description: "Adjust A3 offset to steer UEs from overloaded to underloaded cells"
        a3_offset_range_db: [-3, 6]
        adjustment_step_db: 1
        cooldown_sec: 30
      - type: cio_adjustment
        description: "Adjust Cell Individual Offset for load balancing"
        cio_range_db: [-6, 6]
        adjustment_step_db: 1
      - type: ssb_power_adjustment
        description: "Reduce SSB power on overloaded cells to shrink coverage"
        power_reduction_max_db: 3
    constraints:
      min_handover_success_rate: 95
      max_ue_throughput_degradation_percent: 10
      protected_slices: [urllc-industrial]  # Never offload URLLC UEs
  a1_policy:
    policy_type: load_balancing
    scope:
      cells: all
      slices: [embb-default]
    goals:
      target_prb_balance_percent: 10
      optimization_objective: max_network_throughput
  ric_message_bus:
    type: rmr  # RIC Message Router
    port: 4560""",
    },
]


# =============================================================================
# Generation functions
# =============================================================================

def generate_v3_noc_data(n_samples: int = 6000) -> List[Dict]:
    """Generate NOC training data from the new v3 scenarios."""
    data = []
    params_pool = {
        "site_id": [f"ENB-{random.randint(1000, 9999)}" for _ in range(200)],
        "cell_id": [f"CELL-{random.randint(10000, 99999)}" for _ in range(200)],
        "span_id": [f"SPAN-{random.choice(['NYC-NJ','LAX-SD','CHI-DET','DAL-HOU','ATL-MIA'])}-{random.randint(1,20):02d}" for _ in range(30)],
        "ring_id": [f"RING-{random.choice(['METRO','REGIONAL','BACKBONE'])}-{random.randint(100,999)}" for _ in range(30)],
        "mep_id": [f"MEP-{random.randint(1, 64):03d}" for _ in range(30)],
        "hop_id": [f"MW-HOP-{random.choice(['ALPHA','BRAVO','CHARLIE','DELTA'])}-{random.randint(1,50):02d}" for _ in range(30)],
        "interface_id": [f"{random.choice(['GE','TenGE','HundredGE'])}-{random.randint(0,3)}/{random.randint(0,3)}/{random.randint(0,47)}" for _ in range(50)],
        "interface_type": ["S1-U", "N3", "N6", "N9", "S1-MME", "N2", "Backhaul", "Fronthaul"],
        "router_id": [f"PE-{random.choice(['NYC','LAX','CHI','DAL','ATL','SFO'])}-{random.randint(1,8):02d}" for _ in range(20)],
        "policy_name": [f"SRTE-POLICY-{random.choice(['VOICE','VIDEO','ENTERPRISE','CRITICAL'])}-{random.randint(100,999)}" for _ in range(20)],
        "circuit_id": [f"CKT-{random.choice(['MPLS','INET','LTE-BH','5G-BH'])}-{random.randint(10000,99999)}" for _ in range(30)],
        "upf_id": [f"UPF-{random.choice(['EDGE','REGIONAL','CENTRAL'])}-{random.randint(1,12):02d}" for _ in range(12)],
        "nrf_id": [f"NRF-{random.randint(1, 4):02d}" for _ in range(4)],
        "nf_type": ["AMF", "SMF", "UPF", "PCF", "UDM", "AUSF", "NSSF", "NEF", "CHF"],
        "snssai": ["1-000001", "1-000002", "2-000001", "3-000010", "1-0x00FF01"],
        "tai": [f"310-001-{random.randint(1000,9999):04X}" for _ in range(20)],
        "hplmn": ["310-001", "310-260", "311-480"],
        "vplmn": ["234-015", "262-001", "440-010", "208-001", "234-030"],
        "ap_group": [f"WIFI-AP-{random.choice(['CAMPUS','OFFICE','MALL','STADIUM','AIRPORT'])}-{random.randint(1,20):02d}" for _ in range(20)],
        "chf_id": [f"CHF-{random.randint(1, 4):02d}" for _ in range(4)],
        "cdr_count": [random.randint(100, 50000) for _ in range(20)],
        "af_id": [f"AF-{random.choice(['MAPS','VIDEO','IOT','ANALYTICS','GAMING'])}-{random.randint(1,10):02d}" for _ in range(20)],
        "capability": ["MonitoringEvent", "AsSessionWithQoS", "DeviceTriggering", "AnalyticsExposure", "TrafficInfluence"],
        "rate_limit": [random.randint(10, 1000) for _ in range(10)],
        "mme_id": [f"MME-{random.randint(1, 8):02d}" for _ in range(8)],
        "amf_id": [f"AMF-{random.randint(1, 12):02d}" for _ in range(12)],
        "ecscf_id": [f"E-CSCF-{random.randint(1, 4):02d}" for _ in range(4)],
        "rcs_as_id": [f"RCS-AS-{random.randint(1, 6):02d}" for _ in range(6)],
        "failure_count": [random.randint(50, 10000) for _ in range(20)],
        "mrfc_id": [f"MRFC-{random.randint(1, 4):02d}" for _ in range(4)],
        "active_conf": [random.randint(50, 500) for _ in range(10)],
        "sbc_id": [f"SBC-{random.choice(['EDGE','CORE','PEERING'])}-{random.randint(1,6):02d}" for _ in range(10)],
        "reg_rate": [random.randint(5000, 50000) for _ in range(10)],
        "normal_rate": [random.randint(100, 500) for _ in range(10)],
        "region": ["North", "South", "East", "West", "Central", "Metro", "Rural", "Coastal"],
        "threshold": [random.randint(5, 25) for _ in range(20)],
        "osnr_val": [round(random.uniform(10.0, 17.5), 1) for _ in range(20)],
        "rsl_val": [round(random.uniform(-85.0, -70.0), 1) for _ in range(20)],
        "rsl_threshold": [round(random.uniform(-65.0, -60.0), 1) for _ in range(10)],
        "vlan_expected": [random.randint(100, 4000) for _ in range(20)],
        "vlan_received": [random.randint(100, 4000) for _ in range(20)],
        "flap_count": [random.randint(10, 200) for _ in range(10)],
        "time_period": ["1 hour", "30 minutes", "2 hours", "4 hours", "15 minutes"],
        "drop_count": [random.randint(100, 50000) for _ in range(20)],
        "queue_name": ["EF", "AF41", "AF31", "AF21", "BE", "CS6", "CS7"],
        "util": [random.randint(70, 99) for _ in range(20)],
        "latency": [round(random.uniform(2.0, 50.0), 1) for _ in range(20)],
    }

    for _ in range(n_samples):
        scenario = random.choice(V3_NOC_SCENARIOS)
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


def generate_v3_config_data(n_samples: int = 2000) -> List[Dict]:
    """Generate intent-to-config training pairs from new v3 templates."""
    data = []
    templates = [
        "Convert this network intent to configuration: {intent}",
        "As a network engineer, I need to: {intent}\nGenerate the YAML configuration.",
        "Network intent: {intent}\n\nProvide the corresponding network configuration in YAML format.",
        "Generate 5G network configuration for: {intent}",
    ]

    for _ in range(n_samples):
        pair = random.choice(V3_INTENT_CONFIG_PAIRS)
        template = random.choice(templates)
        data.append({
            "instruction": template.format(intent=pair["intent"]),
            "response": pair["config"].strip(),
            "category": "intent_to_config",
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
    random.seed(43)  # Different seed from v2
    print("=" * 70)
    print("TELCO SLM v3 — Expanding Training Data with New Scenarios")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Load existing v2 data
    # -------------------------------------------------------------------------
    existing_train = []
    existing_val = []
    train_path = PROCESSED_DIR / "train.jsonl"
    val_path = PROCESSED_DIR / "val.jsonl"

    if train_path.exists():
        with open(train_path) as f:
            for line in f:
                existing_train.append(json.loads(line))
        print(f"\nLoaded existing train.jsonl: {len(existing_train)} examples")
    else:
        print(f"\nWARNING: {train_path} not found — starting fresh")

    if val_path.exists():
        with open(val_path) as f:
            for line in f:
                existing_val.append(json.loads(line))
        print(f"Loaded existing val.jsonl:   {len(existing_val)} examples")
    else:
        print(f"WARNING: {val_path} not found — starting fresh")

    old_total = len(existing_train) + len(existing_val)
    old_all = existing_train + existing_val

    # Count old categories
    old_cats = Counter(d.get("category", "unknown") for d in old_all)

    print(f"\nTotal existing (v2) data: {old_total}")
    print(f"\n  Old category breakdown:")
    for cat, count in old_cats.most_common():
        print(f"    {cat}: {count}")

    # -------------------------------------------------------------------------
    # Generate new v3 data
    # -------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("Generating NEW v3 scenarios...")
    print(f"{'='*70}")
    print(f"\n  New NOC scenarios:    {len(V3_NOC_SCENARIOS)} (Transport: 7, Core: 8, IMS/VoLTE: 5)")
    print(f"  New config templates: {len(V3_INTENT_CONFIG_PAIRS)}")

    print("\n[1/2] Generating v3 NOC data...")
    v3_noc_data = generate_v3_noc_data(6000)
    print(f"  Generated: {len(v3_noc_data)} NOC examples")

    print("[2/2] Generating v3 intent-to-config data...")
    v3_config_data = generate_v3_config_data(2000)
    print(f"  Generated: {len(v3_config_data)} config examples")

    # Format new data as chat
    v3_all_raw = v3_noc_data + v3_config_data
    v3_formatted = format_as_chat(v3_all_raw)

    # -------------------------------------------------------------------------
    # Merge, shuffle, split
    # -------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("Merging and splitting...")
    print(f"{'='*70}")

    all_data = old_all + v3_formatted
    random.shuffle(all_data)

    split_idx = int(len(all_data) * 0.9)
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]

    # -------------------------------------------------------------------------
    # Save to data/processed/
    # -------------------------------------------------------------------------
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for path, data in [(PROCESSED_DIR / "train.jsonl", train_data),
                       (PROCESSED_DIR / "val.jsonl", val_data)]:
        with open(path, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    # -------------------------------------------------------------------------
    # Save to data/mlx_format/
    # -------------------------------------------------------------------------
    MLX_DIR.mkdir(parents=True, exist_ok=True)
    for src, dst in [(PROCESSED_DIR / "train.jsonl", MLX_DIR / "train.jsonl"),
                     (PROCESSED_DIR / "val.jsonl", MLX_DIR / "valid.jsonl")]:
        with open(src) as fin, open(dst, "w") as fout:
            for line in fin:
                d = json.loads(line)
                fout.write(json.dumps({"messages": d["messages"]}) + "\n")

    # Test split (first 100 from validation)
    with open(MLX_DIR / "valid.jsonl") as fin:
        lines = fin.readlines()
    with open(MLX_DIR / "test.jsonl", "w") as fout:
        for line in lines[:100]:
            fout.write(line)

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    new_cats = Counter(d.get("category", "unknown") for d in all_data)

    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"\n  Old data (v2):     {old_total} examples")
    print(f"  New data (v3):     {len(v3_formatted)} examples")
    print(f"  Combined total:    {len(all_data)} examples")
    print(f"\n  Train split (90%): {len(train_data)} examples")
    print(f"  Val split (10%):   {len(val_data)} examples")

    print(f"\n  --- Category comparison (old -> new) ---")
    all_cat_names = sorted(set(list(old_cats.keys()) + list(new_cats.keys())))
    for cat in all_cat_names:
        old_c = old_cats.get(cat, 0)
        new_c = new_cats.get(cat, 0)
        delta = new_c - old_c
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        print(f"    {cat:25s}: {old_c:6d} -> {new_c:6d}  ({delta_str})")

    print(f"\n  --- Scenario count comparison ---")
    # Count approximate unique scenario types from v2 script
    print(f"    Transport NOC scenarios:  5 (v2) -> 12 (v3)  [+7 new]")
    print(f"    Core Network scenarios:   6 (v2) -> 14 (v3)  [+8 new]")
    print(f"    IMS/VoLTE scenarios:      3 (v2) ->  8 (v3)  [+5 new]")
    print(f"    Intent-to-config:        15 (v2) -> 25 (v3)  [+10 new]")
    print(f"    Total NOC scenarios:     ~38 (v2) -> 58 (v3) [+20 new]")

    print(f"\n  Output files:")
    print(f"    {PROCESSED_DIR / 'train.jsonl'}")
    print(f"    {PROCESSED_DIR / 'val.jsonl'}")
    print(f"    {MLX_DIR / 'train.jsonl'}")
    print(f"    {MLX_DIR / 'valid.jsonl'}")
    print(f"    {MLX_DIR / 'test.jsonl'}")

    print(f"\n{'='*70}")
    print("Done! Ready to retrain with v3 expanded data.")
    print("  python scripts/training/train_mlx.py")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
