"""
v3 Corrective Data Generation Script
=====================================
Generates 4,500 high-quality training rows for v3 patch-tune using Claude API.
Uses the scenario bank as seed material for diverse, realistic questions.

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  python scripts/generate_v3_corrective.py --category kpi_quantitative --count 500 --output data/v3_corrective/kpi_quantitative.jsonl

Or generate all categories:
  python scripts/generate_v3_corrective.py --all --output-dir data/v3_corrective/

Categories and targets:
  kpi_quantitative:   2000 rows
  kpi_contradictions:  600 rows (200 dedicated + 400 woven)
  regional_temporal:   500 rows
  cause_code:          350 rows
  cross_domain:        350 rows
  incident_anchor:     700 rows (style-corrective, based on regression diagnosis)

Total: 4,500 rows
"""

import argparse
import json
import os
import sys
import time
import csv
import random
from pathlib import Path

random.seed(42)

# ============================================================
# CATEGORY DEFINITIONS
# ============================================================

CATEGORIES = {
    "kpi_quantitative": {
        "count": 2000,
        "description": "KPI analysis with quantitative reasoning",
        "system_prompt": """You are a senior telco RAN/Core optimization engineer generating training data for a telecom AI assistant.

Generate a realistic telco KPI analysis question and expert answer pair.

ANSWER STYLE RULES (CRITICAL):
1. First: interpret what the numbers/pattern actually means
2. Name ONE primary likely cause class (maybe one secondary)
3. Explain WHY that cause fits the specific evidence given
4. State what to CHECK FIRST (specific, actionable)
5. State what ACTION to take first (specific, actionable)

FORBIDDEN patterns:
- NO probability percentages ("70% likely", "40% probability")
- NO "Root Causes (Ranked by Probability):" headers
- NO CLI command dumps
- NO generic "possible causes include X, Y, Z" lists
- NO "Troubleshooting Steps: 1. SSH into..."

REQUIRED:
- Name specific NFs/protocols (AMF, SMF, UPF, SCTP, GTP, PFCP, HARQ, BLER, CQI, OLLA, etc.)
- Use realistic numbers (dB, %, ms, Mbps)
- Be decisive, not hedging
- 150-300 words per answer
- Vary question phrasing (not all "I'm seeing X")

KPI DOMAINS to cover:
ERAB, RRC, CSSR, HOSR, VoLTE MOS, paging, energy efficiency, attach rate,
PRB utilization, BLER, CQI, throughput, retainability, accessibility, latency,
DL/UL throughput, handover, scheduling, PDCCH, MIMO rank, MCS, RSRP, RSRQ, SINR""",
        "subcategories": [
            "trend_analysis", "threshold_reasoning", "before_after",
            "ratio_comparison", "benchmark_delta", "distribution_analysis",
            "regional_comparison", "capacity_analysis"
        ]
    },
    "kpi_contradictions": {
        "count": 600,
        "description": "Contradictory KPI patterns requiring layer isolation",
        "system_prompt": """You are a senior telco engineer generating training data for contradiction reasoning.

Generate a question where two or more metrics CONTRADICT each other, and an expert answer that explains WHY.

CONTRADICTION TYPES:
- Good signal + poor performance (SINR ok but throughput low)
- High success rate + user complaints
- Low congestion + poor experience
- One layer healthy + another degraded
- Average looks fine + percentiles are terrible
- Uplink vs downlink asymmetry
- KPI says ok + real users suffer

ANSWER MUST:
1. Identify which metric is misleading and why
2. Explain the layer/domain where the real issue lives
3. Name the specific mechanism causing the contradiction
4. First check + first action

FORBIDDEN: probability percentages, generic cause lists, CLI dumps.
Use specific NFs, protocols, metrics. 150-300 words.""",
        "subcategories": [
            "sinr_vs_throughput", "prb_vs_users", "cpu_vs_latency",
            "rrc_vs_cssr", "kpi_vs_complaints", "avg_vs_percentile",
            "ul_vs_dl", "bler_vs_throughput", "ho_success_vs_drops",
            "scheduling_vs_throughput", "transport_vs_experience"
        ]
    },
    "regional_temporal": {
        "count": 500,
        "description": "Region/time-specific KPI patterns",
        "system_prompt": """You are a senior telco engineer generating training data for regional and temporal KPI analysis.

Generate a question about a KPI pattern that is specific to:
- A particular geographic area (cluster, region, site type)
- A particular time window (peak hour, seasonal, weekly, post-maintenance)
- A particular vendor/software version
- A comparison between areas or time periods

ANSWER MUST explain WHY the pattern is region/time-specific and what environmental,
configuration, or infrastructure factor causes it. Be decisive. Name specific causes.
First check + first action. 150-300 words.

COVER: peak hour congestion, seasonal propagation, post-maintenance regression,
vendor-specific software issues, terrain/building effects, event-driven spikes,
industrial interference, weather correlation, highway/airport/stadium patterns.""",
        "subcategories": [
            "time_specific", "seasonal", "post_change_regional",
            "vendor_software", "geographic", "event_driven", "periodic"
        ]
    },
    "cause_code": {
        "count": 350,
        "description": "Cause code and reject code interpretation",
        "system_prompt": """You are a senior telco core network engineer generating training data for cause code reasoning.

Generate a question about interpreting a specific rejection cause code, error code, or failure classification.

CODES TO COVER:
- EMM causes: #3 Illegal UE, #5 PLMN not allowed, #6 Illegal ME, #7 EPS not allowed,
  #11 PLMN not allowed, #13 Roaming not allowed in TA, #14 EPS not allowed in PLMN, #15 No suitable cells
- ESM causes: #26 Insufficient resources, #27 Missing/unknown APN, #33 Not subscribed
- 5GMM causes: #62 Insufficient resources for slice, #72 Insufficient resources for slice+DNN
- SIP codes: 403 Forbidden, 408 Timeout, 486 Busy, 503 Service Unavailable, 504 Gateway Timeout
- HO causes: too-late, too-early, wrong-cell, T304 expired, T310 expired, preparation failure
- Timer expirations: T311, T304, T310, T300, DRX timers

ANSWER MUST: explain what the code specifically means, what causes it in this context,
first check, first action. Be precise about which NF/interface is involved.
150-300 words. No probability percentages.""",
        "subcategories": [
            "emm_cause", "esm_cause", "5g_nas_cause", "sip_error",
            "ho_failure_cause", "ho_timer", "registration_reject"
        ]
    },
    "cross_domain": {
        "count": 350,
        "description": "Cross-domain fault correlation (transport/core/RAN/IMS)",
        "system_prompt": """You are a senior telco engineer generating training data for cross-domain fault analysis.

Generate a question where a fault in one domain (transport, core, optical, sync, IP)
causes symptoms in another domain (RAN KPIs, user experience, IMS voice quality).

CROSS-DOMAIN SCENARIOS:
- Transport degradation -> RAN KPI impact
- DWDM/optical issues -> service correlation
- CUPS control/user plane split issues
- Synchronization loss -> scheduling/interference
- IP routing changes -> cell performance
- DNS/signaling path -> user experience
- Slice resource isolation -> per-slice SLA
- Fiber/microwave -> backhaul bottleneck

ANSWER MUST: clearly link the root-domain fault to the symptom-domain impact,
explain the mechanism of propagation between domains, and give cross-domain
first check + first action. Name specific interfaces (N2, N3, N4, S1, X2, F1, PFCP, GTP-U).
150-300 words.""",
        "subcategories": [
            "transport_to_ran", "optical_to_ran", "sync_to_ran",
            "cups_split", "routing_to_ran", "dns_to_experience",
            "slice_isolation", "transport_topology"
        ]
    },
    "incident_anchor": {
        "count": 700,
        "description": "Incident diagnosis with specific NF naming and decisive style",
        "system_prompt": """You are a senior telco NOC engineer generating training data for incident diagnosis.

Generate a realistic incident scenario and expert triage response.

STYLE RULES (CRITICAL - this corrects a known style drift problem):
1. LEAD with the diagnosis, not with investigation steps
2. NAME the specific network function, interface, or protocol FIRST
3. Be DECISIVE - state the most likely cause, don't list 5 possibilities
4. State what the IMPACT is (how many users, what services)
5. First validation check, then first corrective action

DOMAINS TO COVER:
- Core: AMF, SMF, UPF, NSSF, NRF, HSS, MME, SGW, PGW faults
- RAN: BBU, RRU, antenna, scheduling, RACH, PRACH faults
- IMS: P-CSCF, S-CSCF, SBC, SRVCC, codec, Diameter Rx/Gx
- Transport: DWDM, microwave, MPLS, ERPS, fiber, synchronization
- Alarm correlation: multi-alarm floods, cascading failures

FORBIDDEN:
- "Probability 70%" style rankings
- Generic "possible causes include" lists
- "Troubleshooting steps: Step 1: SSH into..."
- Leading with CLI commands before stating the diagnosis

REQUIRED:
- Specific NF names (not "the core network" but "AMF-02")
- Specific protocol names (SCTP, GTP-C, PFCP, S1AP, NGAP, Diameter)
- Specific error codes where relevant
- 150-300 words per answer""",
        "subcategories": [
            "core_fault", "ran_fault", "ims_voice", "transport_fault",
            "alarm_correlation", "post_change", "shared_infra"
        ]
    }
}

# ============================================================
# SCENARIO BANK LOADER
# ============================================================

def load_scenario_bank(bank_path="data/v3_scenario_bank.csv"):
    """Load scenario bank and organize by archetype."""
    bank = {}
    with open(bank_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            arch = row['archetype']
            if arch not in bank:
                bank[arch] = []
            bank[arch].append(row['question_preview'])
    return bank

# Map category -> relevant archetypes from scenario bank
CATEGORY_ARCHETYPES = {
    "kpi_quantitative": ["quantitative_kpi", "capacity", "mobility", "energy"],
    "kpi_contradictions": ["contradiction", "quantitative_kpi"],
    "regional_temporal": ["regional_temporal", "post_change"],
    "cause_code": ["cause_code", "5g_core", "ims_voice"],
    "cross_domain": ["cross_domain", "capacity", "5g_core"],
    "incident_anchor": ["5g_core", "ims_voice", "mobility", "shared_infra", "cross_domain"]
}

# ============================================================
# GENERATION FUNCTIONS
# ============================================================

def build_generation_prompt(category, subcategory, seed_scenarios, batch_size=10):
    """Build a prompt for generating a batch of training rows."""
    cat_def = CATEGORIES[category]

    # Sample seed scenarios for context
    seed_text = "\n".join(f"- {s}" for s in seed_scenarios[:15])

    prompt = f"""Generate exactly {batch_size} diverse, high-quality telco Q&A training pairs.

Category: {category}
Subcategory focus: {subcategory}

Here are some scenario patterns to draw from (use as inspiration, create new variations):
{seed_text}

OUTPUT FORMAT: Return a JSON array of objects, each with:
- "question": the user's question (realistic, diverse wording)
- "answer": the expert answer (following the style rules below)
- "subcategory": "{subcategory}"

{cat_def['system_prompt']}

CRITICAL ANSWER STRUCTURE (every answer MUST have these explicit phrases):
- End with a sentence starting with "First check:" followed by the specific validation step
- Then a sentence starting with "First action:" followed by the specific corrective action
If these two phrases are missing, the answer is WRONG. They must be explicit.

IMPORTANT:
- Each question must be DIFFERENT from the others
- Vary the wording style (mix "What explains...", "Diagnose...", "How should I...", scenario descriptions)
- Use different KPIs, NFs, and numbers in each question
- Make scenarios realistic and specific (use cell IDs, site names, real metric values)

Return ONLY the JSON array, no other text."""

    return prompt


def generate_batch_api(category, subcategory, seed_scenarios, batch_size=10, client=None):
    """Generate a batch using Claude API."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    prompt = build_generation_prompt(category, subcategory, seed_scenarios, batch_size)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        temperature=0.9,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse JSON from response
    text = response.content[0].text
    # Find JSON array in response
    start = text.find('[')
    end = text.rfind(']') + 1
    if start == -1 or end == 0:
        print(f"WARNING: Could not find JSON array in response for {category}/{subcategory}")
        return []

    try:
        items = json.loads(text[start:end])
    except json.JSONDecodeError as e:
        print(f"WARNING: JSON parse error for {category}/{subcategory}: {e}")
        return []

    # Format into training format
    results = []
    for item in items:
        if 'question' in item and 'answer' in item:
            results.append({
                "messages": [
                    {"role": "system", "content": "You are Consilium, a telecom network intelligence assistant. Analyze network data, diagnose issues, and provide actionable recommendations."},
                    {"role": "user", "content": item['question']},
                    {"role": "assistant", "content": item['answer']}
                ],
                "category": category,
                "subcategory": item.get('subcategory', subcategory),
                "source": "v3_corrective"
            })

    return results


def generate_category(category, output_path, scenario_bank):
    """Generate all rows for a category."""
    cat_def = CATEGORIES[category]
    target = cat_def['count']
    subcategories = cat_def['subcategories']

    # Get relevant scenarios from bank
    relevant_archetypes = CATEGORY_ARCHETYPES.get(category, [])
    all_scenarios = []
    for arch in relevant_archetypes:
        all_scenarios.extend(scenario_bank.get(arch, []))
    random.shuffle(all_scenarios)

    print(f"\n{'='*60}", flush=True)
    print(f"Generating: {category} ({target} rows)", flush=True)
    print(f"Scenario seeds available: {len(all_scenarios)}", flush=True)
    print(f"Subcategories: {subcategories}", flush=True)
    print(f"{'='*60}", flush=True)

    # Create client once, reuse for all batches
    import anthropic
    client = anthropic.Anthropic()

    # Write incrementally to output file
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    total_written = 0

    with open(output_path, 'w') as outf:
        rows_per_sub = target // len(subcategories)
        remainder = target % len(subcategories)

        for i, sub in enumerate(subcategories):
            sub_target = rows_per_sub + (1 if i < remainder else 0)
            batches_needed = (sub_target + 9) // 10

            print(f"\n  [{sub}] target: {sub_target} rows ({batches_needed} batches)", flush=True)

            sub_count = 0
            for batch_num in range(batches_needed):
                remaining = sub_target - sub_count
                batch_size = min(10, remaining)
                if batch_size <= 0:
                    break

                offset = (batch_num * 15) % max(1, len(all_scenarios) - 15)
                seed_slice = all_scenarios[offset:offset+15]

                retries = 0
                while retries < 3:
                    try:
                        batch = generate_batch_api(category, sub, seed_slice, batch_size, client=client)
                        # Write immediately
                        for row in batch:
                            outf.write(json.dumps(row, ensure_ascii=False) + '\n')
                        outf.flush()
                        sub_count += len(batch)
                        total_written += len(batch)
                        print(f"    batch {batch_num+1}/{batches_needed}: +{len(batch)} rows (total: {total_written})", flush=True)
                        time.sleep(0.5)
                        break
                    except Exception as e:
                        retries += 1
                        print(f"    batch {batch_num+1} FAILED (attempt {retries}): {e}", flush=True)
                        time.sleep(5 * retries)

            print(f"  [{sub}] done: {sub_count} rows", flush=True)

    print(f"\n  TOTAL {category}: {total_written} rows -> {output_path}", flush=True)
    return total_written


# ============================================================
# QUALITY CHECK
# ============================================================

def quality_check(filepath):
    """Run basic quality checks on generated data."""
    with open(filepath) as f:
        rows = [json.loads(l) for l in f]

    issues = {
        'probability_pct': 0,
        'generic_rca': 0,
        'too_short': 0,
        'too_long': 0,
        'no_first_check': 0,
        'cli_heavy': 0,
    }

    import re
    for row in rows:
        answer = row['messages'][-1]['content']
        a_lower = answer.lower()

        if re.search(r'\d+%\s*(probability|likely|likelihood|chance)', a_lower):
            issues['probability_pct'] += 1
        if re.search(r'root causes?\s*\(ranked', a_lower):
            issues['generic_rca'] += 1
        if len(answer) < 100:
            issues['too_short'] += 1
        if len(answer) > 2000:
            issues['too_long'] += 1
        if not re.search(r'first (check|action|step|thing to)', a_lower):
            issues['no_first_check'] += 1
        if len(re.findall(r'`[^`]{5,}`', answer)) > 4:
            issues['cli_heavy'] += 1

    print(f"\nQuality check for {filepath}:")
    print(f"  Total rows: {len(rows)}")
    for issue, count in issues.items():
        pct = count / len(rows) * 100 if rows else 0
        flag = " !!!" if pct > 10 else ""
        print(f"  {issue}: {count} ({pct:.1f}%){flag}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="v3 Corrective Data Generator")
    parser.add_argument('--category', choices=list(CATEGORIES.keys()), help='Generate one category')
    parser.add_argument('--all', action='store_true', help='Generate all categories')
    parser.add_argument('--output', help='Output file path (for single category)')
    parser.add_argument('--output-dir', default='data/v3_corrective', help='Output directory (for --all)')
    parser.add_argument('--count', type=int, help='Override row count')
    parser.add_argument('--check', help='Run quality check on a file')
    parser.add_argument('--dry-run', action='store_true', help='Print prompts without calling API')
    args = parser.parse_args()

    if args.check:
        quality_check(args.check)
        return

    # Load scenario bank
    bank_path = Path(__file__).parent.parent / "data" / "v3_scenario_bank.csv"
    scenario_bank = load_scenario_bank(str(bank_path))
    print(f"Loaded scenario bank: {sum(len(v) for v in scenario_bank.values())} scenarios across {len(scenario_bank)} archetypes")

    if args.dry_run:
        # Print sample prompts
        for cat in (CATEGORIES.keys() if args.all else [args.category]):
            cat_def = CATEGORIES[cat]
            archs = CATEGORY_ARCHETYPES.get(cat, [])
            seeds = []
            for a in archs:
                seeds.extend(scenario_bank.get(a, [])[:5])
            prompt = build_generation_prompt(cat, cat_def['subcategories'][0], seeds, 10)
            print(f"\n{'='*60}")
            print(f"CATEGORY: {cat}")
            print(f"{'='*60}")
            print(prompt[:2000])
            print("...\n")
        return

    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("ERROR: ANTHROPIC_API_KEY not set")
        print("Run: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    if args.all:
        total = 0
        for cat in CATEGORIES:
            if args.count:
                CATEGORIES[cat]['count'] = args.count
            output = os.path.join(args.output_dir, f"{cat}.jsonl")
            total += generate_category(cat, output, scenario_bank)

        print(f"\n{'='*60}")
        print(f"ALL DONE: {total} total rows")
        print(f"Output directory: {args.output_dir}")

        # Run quality check on all
        for cat in CATEGORIES:
            filepath = os.path.join(args.output_dir, f"{cat}.jsonl")
            if os.path.exists(filepath):
                quality_check(filepath)

    elif args.category:
        if args.count:
            CATEGORIES[args.category]['count'] = args.count
        output = args.output or os.path.join(args.output_dir, f"{args.category}.jsonl")
        generate_category(args.category, output, scenario_bank)
        quality_check(output)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
