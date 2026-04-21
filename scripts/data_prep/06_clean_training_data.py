"""
Step 6: Clean training data to remove conversational artifacts
- Removes trailing follow-up questions from assistant responses
- Removes leading question repetition (assistant restating the user's question)
- Removes conversational filler ("Let me know if...", "Feel free to...", etc.)
- Adds domain tags [RAN]/[Core]/[Transport]/[IMS] based on content analysis
- Writes cleaned data to data/v2_cleaned_train.jsonl
"""

import json
import re
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "train.jsonl"
OUTPUT_FILE = PROJECT_ROOT / "data" / "v2_cleaned_train.jsonl"


# =============================================================================
# 1. PATTERN DEFINITIONS
# =============================================================================

# Trailing follow-up question patterns (case-insensitive)
TRAILING_FOLLOWUP_PATTERNS = [
    r"would you like\b.*\?",
    r"do you want me to\b.*\?",
    r"shall i\b.*\?",
    r"can i help.*\?",
    r"how can i help.*\?",
    r"what would you like.*\?",
    r"would you like to know.*\?",
    r"is there anything else.*\?",
    r"do you need.*\?",
    r"want me to.*\?",
    r"should i.*\?",
    r"any other questions\??",
    r"anything else\??",
    r"need any(thing)? (more|else|further).*\?",
]

TRAILING_FOLLOWUP_RE = re.compile(
    "|".join(TRAILING_FOLLOWUP_PATTERNS), re.IGNORECASE
)

# Conversational filler patterns (to remove entire sentence)
FILLER_PATTERNS = [
    r"let me know if you (?:have|need|want|would like).*",
    r"feel free to (?:ask|reach out|contact).*",
    r"don'?t hesitate to (?:ask|reach out|contact).*",
    r"i'?m here to help.*",
    r"hope this helps.*",
    r"happy to help.*",
    r"i hope (?:this|that) (?:helps|answers|clarifies).*",
    r"please (?:let me know|feel free).*",
    r"if you (?:have any|need any) (?:more |further )?questions.*",
]

FILLER_RE = re.compile("|".join(FILLER_PATTERNS), re.IGNORECASE)

# Domain keyword mappings for tagging
DOMAIN_KEYWORDS = {
    "RAN": [
        r"\b(?:RAN|gNB|eNB|eNodeB|gNodeB|PRACH|RACH|PDSCH|PUSCH|PDCCH|PUCCH)\b",
        r"\b(?:handover|HO|cell|antenna|beamforming|beam\s*failure|MIMO|PRB)\b",
        r"\b(?:RRC|HARQ|MCS|SINR|RSRP|RSRQ|RSSI|CQI|PMI|RI|BLER)\b",
        r"\b(?:carrier aggregation|DL\s*PRB|UL\s*PRB|SSB|CSI-RS|SRS)\b",
        r"\b(?:radio\s*link|RLF|MLB|MRO|coverage|interference|scheduler)\b",
        r"\b(?:RRU|BBU|DU|CU|fronthaul|CPRI|eCPRI)\b",
        r"\b(?:energy\s*saving|carrier\s*shutdown|symbol\s*shutdown)\b",
        r"\b(?:power\s*class|output\s*power|MPR|A-MPR|EVM)\b",
        r"\b(?:NR\s*band|n\d{1,3}\b|band\s*\d{1,3})\b",
        r"\b(?:UE\s*(?:maximum|power|capability)|conformance|test\s*case)\b",
    ],
    "Core": [
        r"\b(?:AMF|SMF|UPF|NRF|NSSF|NEF|AUSF|UDM|PCF|NWDAF)\b",
        r"\b(?:MME|SGW|PGW|HSS|PCRF)\b",
        r"\b(?:PDU\s*session|bearer|EPS|QoS\s*flow|5QI|QCI)\b",
        r"\b(?:registration|authentication|NAS|N1|N2|N3|N4|N6|N11)\b",
        r"\b(?:PLMN|S-NSSAI|network\s*slice|slice\s*admission)\b",
        r"\b(?:GTP-U|GTP-C|Diameter|PFCP)\b",
        r"\b(?:roaming|SEPP|N32|charging|CHF|Nchf)\b",
        r"\b(?:subscriber|IMSI|SUPI|SUCI)\b",
        r"\b(?:5GC|EPC|core\s*network)\b",
    ],
    "Transport": [
        r"\b(?:backhaul|fronthaul|midhaul|transport)\b",
        r"\b(?:MPLS|segment\s*routing|SR-MPLS|SRv6)\b",
        r"\b(?:BGP|OSPF|IS-IS|VLAN|QinQ|Ethernet\s*OAM)\b",
        r"\b(?:DWDM|OSNR|optical|fiber|SFP|CFP|EDFA)\b",
        r"\b(?:microwave|MW|rain\s*fade|RSL)\b",
        r"\b(?:PTP|IEEE\s*1588|SyncE|synchronization|timing)\b",
        r"\b(?:IPsec|GRE|tunnel|VXLAN)\b",
        r"\b(?:router|switch|PE|CE|P\s*router)\b",
        r"\b(?:packet\s*loss.*backhaul|latency.*backhaul)\b",
        r"\b(?:MTU|CRC|interface\s*error)\b",
    ],
    "IMS": [
        r"\b(?:IMS|VoLTE|VoNR|VoWiFi)\b",
        r"\b(?:SIP|INVITE|REGISTER|BYE|PRACK|UPDATE|SUBSCRIBE|NOTIFY)\b",
        r"\b(?:P-CSCF|I-CSCF|S-CSCF|E-CSCF|BGCF|MGCF|MRFC|MRFP)\b",
        r"\b(?:SBC|session\s*border\s*controller)\b",
        r"\b(?:RTP|RTCP|SDP|codec|AMR|EVS)\b",
        r"\b(?:emergency\s*call|911|112|PSAP)\b",
        r"\b(?:Cx|Dx|Sh|Mw|Mg|Mi|Mn)\s*interface\b",
        r"\b(?:registration\s*storm|503\s*Service)\b",
        r"\b(?:Erlang|voice\s*capacity|call\s*setup)\b",
    ],
}

# Compile domain patterns
DOMAIN_COMPILED = {}
for domain, patterns in DOMAIN_KEYWORDS.items():
    DOMAIN_COMPILED[domain] = [re.compile(p, re.IGNORECASE) for p in patterns]


# =============================================================================
# 2. CLEANING FUNCTIONS
# =============================================================================


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, handling numbered lists and abbreviations."""
    # Split on sentence-ending punctuation followed by space or newline
    # But not on abbreviations like e.g., i.e., vs., etc.
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\d\*\-\(\"\\])', text)
    # Also split on newlines that separate content blocks
    result = []
    for s in sentences:
        parts = s.split("\n")
        result.extend([p.strip() for p in parts if p.strip()])
    return result


def remove_trailing_followup(text: str) -> tuple[str, bool]:
    """Remove trailing follow-up questions from assistant response.

    Returns (cleaned_text, was_modified).
    """
    if not text:
        return text, False

    # Split into lines/sentences from the end
    lines = text.rstrip().split("\n")

    modified = False
    # Check last few lines for follow-up patterns
    while lines:
        last_line = lines[-1].strip()
        if not last_line:
            lines.pop()
            continue

        # Check if last line is a follow-up question
        if TRAILING_FOLLOWUP_RE.search(last_line):
            lines.pop()
            modified = True
            continue

        # Check if last line is conversational filler
        if FILLER_RE.match(last_line):
            lines.pop()
            modified = True
            continue

        break

    if modified:
        cleaned = "\n".join(lines).rstrip()
        # Don't return empty
        if cleaned.strip():
            return cleaned, True
        else:
            return text, False

    return text, False


def remove_leading_repetition(user_msg: str, asst_msg: str) -> tuple[str, bool]:
    """Remove leading sentence if it restates the user's question.

    Returns (cleaned_text, was_modified).
    """
    if not user_msg or not asst_msg:
        return asst_msg, False

    # Get first sentence of assistant response
    first_break = None
    for i, ch in enumerate(asst_msg):
        if i > 0 and ch == "\n":
            first_break = i
            break

    if first_break is None:
        # Single-line response, check first sentence via period
        period_match = re.search(r'[.!]\s', asst_msg[:300])
        if period_match:
            first_break = period_match.end()
        else:
            return asst_msg, False

    first_sentence = asst_msg[:first_break].strip().lower()
    user_lower = user_msg.strip().lower()

    # Extract significant words (>3 chars) from both
    user_words = set(
        w for w in re.findall(r'\b\w{4,}\b', user_lower)
    )
    first_words = set(
        w for w in re.findall(r'\b\w{4,}\b', first_sentence)
    )

    if not user_words or not first_words:
        return asst_msg, False

    # Calculate overlap ratio
    overlap = len(user_words & first_words)
    ratio = overlap / len(user_words) if user_words else 0

    # If more than 60% of user's significant words appear in first sentence,
    # and the first sentence looks like a restatement (not technical content)
    restatement_indicators = [
        r"^(?:great |good )?question",
        r"^you (?:asked|want|mentioned|are asking)",
        r"^(?:so |basically )?(?:you're|you are) (?:asking|wondering)",
        r"^(?:regarding|about|concerning) ",
        r"^the question (?:is|about)",
        r"^to answer your question",
    ]

    is_restatement = any(
        re.search(p, first_sentence) for p in restatement_indicators
    )

    if ratio >= 0.7 or is_restatement:
        remainder = asst_msg[first_break:].lstrip("\n").lstrip()
        if remainder and len(remainder) > 50:
            return remainder, True

    return asst_msg, False


def remove_inline_filler(text: str) -> tuple[str, bool]:
    """Remove conversational filler sentences from anywhere in the response."""
    lines = text.split("\n")
    cleaned_lines = []
    modified = False

    for line in lines:
        stripped = line.strip()
        if stripped and FILLER_RE.match(stripped):
            modified = True
            continue
        cleaned_lines.append(line)

    if modified:
        result = "\n".join(cleaned_lines).strip()
        if result:
            return result, True
        return text, False

    return text, False


def infer_domain(user_msg: str, asst_msg: str, category: str) -> str | None:
    """Infer the telco domain from message content and category.

    Returns domain tag string or None if uncertain.
    """
    combined = f"{user_msg} {asst_msg}"

    # Score each domain
    scores = {}
    for domain, patterns in DOMAIN_COMPILED.items():
        score = 0
        for p in patterns:
            matches = p.findall(combined)
            score += len(matches)
        scores[domain] = score

    if not any(scores.values()):
        return None

    # Use category hints to boost domain scores
    category_lower = category.lower() if category else ""
    if "ran" in category_lower:
        scores["RAN"] = scores.get("RAN", 0) + 5
    if "core" in category_lower:
        scores["Core"] = scores.get("Core", 0) + 5
    if "transport" in category_lower:
        scores["Transport"] = scores.get("Transport", 0) + 5
    if "ims" in category_lower or "volte" in category_lower:
        scores["IMS"] = scores.get("IMS", 0) + 5

    # Return the top domain if it has a meaningful score
    top_domain = max(scores, key=scores.get)
    if scores[top_domain] >= 2:
        return top_domain

    return None


def has_domain_tag(text: str) -> bool:
    """Check if response already starts with a domain tag."""
    return bool(re.match(r"^\[(RAN|Core|Transport|IMS)\]", text.strip()))


# =============================================================================
# 3. MAIN CLEANING PIPELINE
# =============================================================================


def clean_dataset():
    """Main cleaning pipeline."""
    print(f"Reading: {INPUT_FILE}")

    records = []
    with open(INPUT_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Total records loaded: {len(records)}")

    # Stats tracking
    stats = {
        "trailing_followup_removed": 0,
        "leading_repetition_removed": 0,
        "inline_filler_removed": 0,
        "domain_tag_added": 0,
        "already_had_tag": 0,
        "no_domain_inferred": 0,
        "total_modified": 0,
    }
    domain_tag_counts = Counter()
    category_counts = Counter()

    cleaned_records = []

    for record in records:
        msgs = record["messages"]
        category = record.get("category", "")
        category_counts[category] += 1

        # Find user and assistant messages
        user_msg = ""
        asst_idx = None
        for i, m in enumerate(msgs):
            if m["role"] == "user":
                user_msg = m["content"]
            if m["role"] == "assistant":
                asst_idx = i

        if asst_idx is None:
            cleaned_records.append(record)
            continue

        original_text = msgs[asst_idx]["content"]
        text = original_text
        modified = False

        # Step 1: Remove trailing follow-up questions
        text, changed = remove_trailing_followup(text)
        if changed:
            stats["trailing_followup_removed"] += 1
            modified = True

        # Step 2: Remove leading question repetition
        text, changed = remove_leading_repetition(user_msg, text)
        if changed:
            stats["leading_repetition_removed"] += 1
            modified = True

        # Step 3: Remove inline conversational filler
        text, changed = remove_inline_filler(text)
        if changed:
            stats["inline_filler_removed"] += 1
            modified = True

        # Step 4: Add domain tag if not present
        if has_domain_tag(text):
            stats["already_had_tag"] += 1
        else:
            domain = infer_domain(user_msg, text, category)
            if domain:
                text = f"[{domain}] {text}"
                stats["domain_tag_added"] += 1
                domain_tag_counts[domain] += 1
                modified = True
            else:
                stats["no_domain_inferred"] += 1

        if modified:
            stats["total_modified"] += 1

        # Update the record
        msgs[asst_idx]["content"] = text
        record["messages"] = msgs
        cleaned_records.append(record)

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for record in cleaned_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Print report
    print("\n" + "=" * 60)
    print("CLEANING REPORT")
    print("=" * 60)
    print(f"Total records:                 {len(records)}")
    print(f"Total records modified:        {stats['total_modified']}")
    print(f"  - Trailing follow-up removed:  {stats['trailing_followup_removed']}")
    print(f"  - Leading repetition removed:  {stats['leading_repetition_removed']}")
    print(f"  - Inline filler removed:       {stats['inline_filler_removed']}")
    print(f"  - Domain tag added:            {stats['domain_tag_added']}")
    print(f"  - Already had domain tag:      {stats['already_had_tag']}")
    print(f"  - No domain inferred:          {stats['no_domain_inferred']}")
    print()
    print("Domain tags added:")
    for domain, count in domain_tag_counts.most_common():
        print(f"  [{domain}]: {count}")
    print()
    print("Category distribution:")
    for cat, count in category_counts.most_common():
        print(f"  {cat}: {count}")
    print()
    print(f"Output written to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    clean_dataset()
