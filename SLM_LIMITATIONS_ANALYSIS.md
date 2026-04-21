# TelcoGPT SLM — Limitations Analysis
## Date: 2026-03-19
## Based on: Phase 1 Agent Testing

---

## 1. Executive Summary

The fine-tuned Qwen 2.5 1.5B model (TelcoGPT v3) **learned the output format** (structured severity/domain/causes/steps) but **did not learn accurate telco knowledge**. It produces responses that look professional but contain factually incorrect content — which is arguably **worse than no answer at all** because it creates false confidence.

This document analyzes why, with specific evidence.

---

## 2. Evidence: What Went Wrong

### Test Case 1: VoLTE Call Setup Failure

**Query:** "VoLTE call setup failure rate exceeds 10% in North region"

| What SLM Said | What's Actually Correct | Verdict |
|---------------|------------------------|---------|
| Domain: **Transport** | Domain: **IMS/VoLTE** | ❌ Wrong |
| "WAP Gateway processing too slow" | WAP is a 2002 technology, irrelevant to VoLTE | ❌ Hallucination |
| "voice-to-video conversion" | Question is about voice, not video | ❌ Nonsense |
| "SBC (VoLTE Core)" | SBC is Session Border Controller, not "VoLTE Core" | ❌ Incorrect |
| "QoS policy failing on voice-to-video conversion" | Should be: QCI=1 bearer setup failure | ❌ Wrong |
| "MTU issue causing fragmentation" | Possible but unlikely for VoLTE setup failures | ⚠️ Misleading |
| Missing: P-CSCF, IMS registration, QCI=1 bearer, SIP signaling | These are the actual top causes | ❌ Critical omission |

**Correct answer should have included:**
1. Check IMS registration success rate (P-CSCF/I-CSCF/S-CSCF)
2. Verify dedicated bearer setup for QCI=1 (GBR voice bearer)
3. Test DNS resolution for IMS APN
4. Check SBC and P-CSCF certificate validity
5. Review SIP signaling traces for error codes (403, 503, 408)
6. If 403 errors, check HSS subscription data for VoLTE entitlement

### Test Case 2: RACH Failure

**Query:** "RACH failure rate exceeds 15% on cell CELL-45678"

| What SLM Said | Verdict |
|---------------|---------|
| Severity: Critical, Domain: RAN | ✅ Correct |
| "PRACH configuration mismatch" | ✅ Correct cause |
| "Coverage hole" | ✅ Correct cause |
| "consider PRACH vs PUCCH vs SRS vs CSI-RS vs DMRS vs RLM vs L1-CSI" | ❌ Acronym soup — lists everything it knows |
| "PRACH offset — ensure it covers cell center" | ❌ Not a real concept |
| "TDD to FDD or vice versa" | ❌ Unrelated to RACH |
| "increasing MIMO from 2 to 4 layers should improve BLER" | ❌ MIMO layers don't fix RACH failures |

**Pattern:** Gets ~30% of content right, ~70% is wrong or irrelevant.

### Test Case 3: Follow-up Question

**Query:** "if I have to contextualise to my network what is needed?"

| What Happened | Problem |
|---------------|---------|
| Supervisor classified as "config" | ❌ Wrong — this is a follow-up, not a config request |
| ConfigAgent generated fake YAML with invented node names | ❌ Complete hallucination |
| No memory of previous RACH question | ❌ No conversation context |

---

## 3. Root Cause Analysis: Why the SLM Fails

### 3.1 Model Size (FUNDAMENTAL)

| Parameter Count | What It Can Do | What It Can't Do |
|----------------|----------------|-------------------|
| **1.5B** (our model) | Learn patterns, formats, simple associations | Reason, correlate, distinguish similar concepts, avoid hallucination |
| **3B** | Better associations, less hallucination | Complex multi-step reasoning |
| **7B** | Good reasoning, can synthesize context | May still hallucinate on niche topics |
| **70B+** (GPT-4, Claude) | Strong reasoning, rarely hallucinates | Nothing relevant — these work well |

**The core issue:** 1.5B parameters is simply not enough capacity to store and correctly recall the complex relationships in telecom. The model has ~1.5 billion weights to encode ALL of language understanding PLUS telco domain knowledge. By comparison:
- The 3GPP specification library alone is 535 million words
- A human telco engineer has decades of experience and can reason about novel situations
- GPT-4 has ~1.8 trillion parameters (1,200x more)

**Analogy:** It's like trying to compress an entire library into a small notebook. You can write down some key facts, but when asked a question, you'll often mix up details or fill in gaps with guesses.

### 3.2 Training Data Quality (SIGNIFICANT)

| Problem | Detail | Impact |
|---------|--------|--------|
| **Template-based, not real** | 47 NOC scenarios are hand-written templates with parameter substitution (e.g., {site_id}, {threshold}) | Model learns the fill-in-the-blank pattern, not the underlying telco logic |
| **Limited variation** | Each scenario has 1 diagnosis and 1 resolution — real incidents have many possible causes depending on context | Model always gives the same answer for similar alarms |
| **No wrong-answer training** | Model never sees examples of incorrect reasoning and why it's wrong | Can't distinguish correct from incorrect conclusions |
| **No multi-step reasoning** | Training examples are single Q→A, not Q→Think→Investigate→Conclude | Model jumps to answers without reasoning through the problem |
| **Short context (512 tokens)** | Truncated during training — model never saw full-length technical discussions | Responses often trail off or become repetitive after ~200 tokens |

**Example of the problem:**
Our training data for VoLTE failure says:
```
Causes: 1) IMS registration failures (check P-CSCF),
        2) Bearer setup failures (dedicated EPS bearer for QCI=1),
        3) DNS resolution issues for IMS domain,
        4) Certificate expiry on SBC/P-CSCF
```

But when the model generates a response for a VoLTE query, it:
- Sometimes reproduces this correctly (if the input closely matches the template)
- Often mixes in causes from OTHER scenarios (transport, RAN) because it can't reliably distinguish domains
- Invents plausible-sounding but wrong causes ("WAP Gateway") because it's pattern-completing

### 3.3 Knowledge Confusion (INHERENT TO SMALL MODELS)

The model has been trained on data from multiple telco domains (RAN, Core, Transport, IMS, Security, Power). With only 1.5B parameters, these domains **bleed into each other**:

```
Query about VoLTE → Model activates "telecom failure" patterns
                  → Mixes in Transport concepts (MTU, backhaul)
                  → Mixes in RAN concepts (BLER, MIMO)
                  → Mixes in archaic concepts (WAP)
                  → Some IMS concepts come through correctly
                  → Result: ~30% correct, ~70% cross-domain contamination
```

A larger model (7B+) has enough capacity to keep these domains **separated in its internal representations**. A 1.5B model doesn't — everything blurs together.

### 3.4 No Conversation Memory (ARCHITECTURAL)

| What User Expects | What System Does |
|-------------------|-----------------|
| "VoLTE failure in North" → "how to fix for my network?" | Each query processed independently — no context |
| Follow-up questions build on previous answers | Every query starts from scratch |
| "Can you elaborate on point 3?" | Model has no idea what "point 3" refers to |

This isn't a model limitation — it's an architecture limitation that needs Phase 2 implementation.

### 3.5 Hallucination Patterns (SPECIFIC TO 1.5B)

| Pattern | Example | Why It Happens |
|---------|---------|---------------|
| **Acronym soup** | "consider PRACH vs PUCCH vs SRS vs CSI-RS vs DMRS vs RLM vs L1-CSI" | Model lists all related terms it knows instead of selecting the relevant one |
| **Plausible fiction** | "WAP Gateway processing too slow" | Model generates text that follows grammatical/structural patterns of real telco content but the specific claim is false |
| **Domain bleeding** | VoLTE question → Transport domain, MTU causes | Cross-domain contamination in small parameter space |
| **Repetition loops** | Config agent generating connected_xxx: xxx-01, connected_xxx2: xxx-02... | Model gets stuck in a generation pattern and can't break out |
| **Invented concepts** | "PRACH offset — ensure it covers cell center" | Combines real terms (PRACH, cell) into a concept that doesn't exist |
| **Confident wrongness** | States "Domain: Transport" for VoLTE issue with no uncertainty | Training format (always assert severity/domain) teaches the model to be confident even when wrong |

---

## 4. What the SLM CAN and CANNOT Do

### 4.1 What It Does Well

| Capability | Why It Works | Example |
|-----------|-------------|---------|
| **Output format** | Trained extensively on structured format | Always produces Severity/Domain/Causes/Steps structure |
| **Config YAML for trained templates** | Direct pattern match with training data | "Generate URLLC slice" → produces correct YAML (if template exists) |
| **Domain detection** (sometimes) | RAN/Core/Transport are in the training data | Often gets the right domain for clear-cut alarms |
| **Listing common causes** | Memorized from training templates | Can list 3-5 plausible causes (even if not all correct) |
| **Fast inference** | 1.5B is small → fast | 3-6 seconds on M4 Pro |

### 4.2 What It Cannot Do

| Limitation | Why It Fails | Impact |
|-----------|-------------|--------|
| **Accurate domain classification** | Not enough parameters to reliably separate 6 domains | VoLTE → "Transport" (wrong) |
| **Correct cause-effect reasoning** | Can't reason about protocol interactions | Invents causes like "WAP Gateway" |
| **Distinguish similar concepts** | Small parameter space → concepts blur | Mixes RAN, Core, IMS causes freely |
| **Handle novel queries** | Only knows template patterns | Any query that doesn't match training → hallucination |
| **Conversation context** | Architectural limitation (no memory) | Follow-ups are meaningless |
| **Avoid confident hallucination** | Trained to always assert confidently | States wrong answers with same confidence as correct ones |
| **Long coherent responses** | 512 token training limit | Degrades after ~200 tokens, repetition loops |

---

## 5. Comparison: 1.5B vs 7B vs ChatGPT

For the query "Our ERAB drop rate is at 2.8%, what should I investigate?":

| Aspect | TelcoGPT 1.5B (SLM) | Qwen 7B (Ollama) | ChatGPT |
|--------|---------------------|-------------------|---------|
| **Structure** | Good format | Good format | Excellent (AIOps flow) |
| **Accuracy** | ~30% correct | ~70% correct | ~95% correct |
| **Domain classification** | Sometimes wrong | Usually correct | Always correct |
| **Cause identification** | Mixes domains | Mostly correct | Precise, with correlation logic |
| **Actionable steps** | Generic ("check X") | Specific per cause | Detailed with thresholds + tools |
| **Reasoning** | None — pattern match | Basic reasoning | Multi-step (classify → drilldown → correlate → act) |
| **Hallucination** | Frequent | Occasional | Rare |
| **Speed** | 4-6s | 15-30s | 3-5s (API) |
| **Cost** | $0 | $0 | ~$0.02/query |
| **Privacy** | Fully local | Fully local | Data goes to cloud |

---

## 6. What Would Fix These Problems

### 6.1 Ordered by Impact

| Fix | Impact | Effort | Expected Improvement |
|-----|--------|--------|---------------------|
| **1. Upgrade to 7B model** (train on Google Colab) | Very High | Medium (few hours on Colab) | Eliminates domain bleeding, much less hallucination, actual reasoning capability |
| **2. Knowledge distillation** (train on 500+ ChatGPT expert responses) | High | Medium (generate data + retrain) | Model learns correct reasoning patterns from larger model |
| **3. Add conversation memory** | High | Low (Phase 2 feature) | Fixes follow-up question problem completely |
| **4. Chain-of-thought training** | High | Medium | Model learns to think step-by-step before answering |
| **5. Real NOC data** (anonymized real incidents instead of templates) | Very High | Hard (need access to real data) | Model sees real-world complexity, not just templates |
| **6. Negative examples** (train on what NOT to do) | Medium | Medium | Reduces confident hallucination |
| **7. DPO/preference training** | High | Medium | Model learns to prefer accurate over plausible |
| **8. Retrieval-augmented generation for incidents** | Medium | Low | Even for incidents, pull relevant procedures from RAG before answering |

### 6.2 Minimum Viable Improvement Path

```
Step 1: Generate 500 expert responses using ChatGPT/Claude
        (covering all 47 scenarios with correct, detailed answers)
        Impact: Model learns what "good" looks like

Step 2: Add chain-of-thought format to training data
        Instead of: Q → Answer
        Train on:   Q → "Let me analyze this step by step..." → Answer
        Impact: Model reasons before answering

Step 3: Add conversation memory (Phase 2 architecture)
        Impact: Follow-ups work correctly

Step 4: Train Qwen 3B or 7B on Google Colab (free T4 GPU)
        Impact: Dramatically better reasoning, less hallucination

Step 5: Collect real NOC data (even 100 real incidents)
        Impact: Model sees real complexity, not just templates
```

---

## 7. The Fundamental Truth

**A 1.5B parameter model cannot reliably perform expert-level telecom diagnosis.**

This is not a failure of our approach — it's a physics constraint. The model doesn't have enough capacity to:
1. Store all the telco knowledge (3GPP is 535M words)
2. Keep domains separated (RAN vs Core vs IMS vs Transport)
3. Reason about cause-effect relationships
4. Avoid hallucination under uncertainty

**What a 1.5B model CAN do in this architecture:**
- Fast classification/routing (is this an incident? config? knowledge question?)
- Simple pattern matching for well-trained templates
- YAML generation for known config types
- Pre-processing before a larger model handles the hard work

**What a 1.5B model CANNOT do:**
- Be the primary reasoning engine for expert diagnosis
- Replace a telecom engineer's judgment
- Handle novel situations not in its training data
- Maintain accuracy across multiple domains

---

## 8. Impact on Architecture

### Current Architecture (Phase 1)
```
Supervisor (7B) → routes to → SLM (1.5B) for incidents/configs
                             → 7B for knowledge/general
```

### What Testing Revealed
- SLM handles routing format well but content is unreliable
- 7B (GenericAgent) gave more sensible answers than SLM (IncidentAgent)
- The value of fine-tuning is in format/structure, not in knowledge

### Recommended Revised Architecture
```
Supervisor (7B) → classifies + plans approach
                → SLM (1.5B) for: fast classification, config template match
                → 7B + RAG for: diagnosis, knowledge, reasoning
                → SLM for: final output formatting
```

In this model, the SLM becomes a **formatting/classification assistant**, not the primary reasoning engine. The 7B model (or eventually API) handles the actual thinking.

---

## 9. Key Takeaway

**We built the right architecture but overestimated what a 1.5B model can do as the reasoning engine.**

The agentic framework (Supervisor → specialized agents → tools) is correct. The routing works. The RAG pipeline works. The infrastructure is solid.

The gap is in the **specialist agent quality** — and that's fundamentally a model size problem. The path forward is:
1. Short-term: Use 7B for all reasoning, SLM for classification/formatting only
2. Medium-term: Train 7B on our data (Google Colab) → get the best of both worlds
3. Long-term: Continuous improvement with real data + expert responses + larger models

**The framework we built will serve us well regardless of which model we plug in.** That's the real value of the agentic architecture — the agents, tools, and routing are model-agnostic.
