# Fine-tuned 7B — Testing Checklist
## To be run when Colab training completes and model is imported to Mac

---

## 1. Operational Benchmark (100 Questions)

Run the full benchmark and compare against all previous models:

```bash
python scripts/evaluation/operational_benchmark.py --model 7b-finetuned
```

**Target: 85-90% overall (currently: v3=61.4%, base 7B=76.1%, Agent System=83.4%)**

| Category | v3 (1.5B FT) | Base 7B | Agent System | FT-7B Target |
|----------|-------------|---------|--------------|-------------|
| Config Generation | 86.0% | 91.5% | 96.1% | 95%+ |
| Incident Diagnosis | 67.6% | 71.6% | 78.3% | 85%+ |
| Protocol Knowledge | 40.0% | 85.2% | 83.8% | 88%+ |
| KPI Analysis | 44.6% | 52.4% | 59.5% | 65%+ |
| Routing | — | — | 100% | 100% |
| **Overall** | **61.4%** | **76.1%** | **83.4%** | **85-90%** |

---

## 2. Known 1.5B Failures — Re-test with 7B

These specific queries produced wrong/broken responses from the 1.5B SLM. Re-test each one.

### 2.1 VoLTE Call Setup Failure (Wrong Domain + Hallucination)
```
Query: "VoLTE call setup failure rate exceeds 10% in North region"
```
**1.5B got wrong:**
- Domain: said "Transport" → should be "IMS/VoLTE"
- Invented "WAP Gateway" cause (2002 technology, irrelevant)
- Invented "voice-to-video conversion" (question is about voice only)
- Missing: P-CSCF, QCI=1 bearer, IMS registration, SIP error codes

**7B should get right:**
- [ ] Domain: IMS/VoLTE
- [ ] Mentions P-CSCF / S-CSCF / I-CSCF
- [ ] Mentions QCI=1 dedicated bearer setup
- [ ] Mentions SIP signaling / error codes (403, 503)
- [ ] Mentions IMS registration check
- [ ] Does NOT mention WAP, voice-to-video, or Transport domain

### 2.2 RACH Failure (Acronym Soup)
```
Query: "RACH failure rate exceeds 15% on cell CELL-45678"
```
**1.5B got wrong:**
- Listed "PRACH vs PUCCH vs SRS vs CSI-RS vs DMRS vs RLM vs L1-CSI" — dumped every acronym
- Invented "PRACH offset — ensure it covers cell center" (not a real concept)
- Said "TDD to FDD or vice versa" (unrelated)

**7B should get right:**
- [ ] Focused on PRACH configuration (root sequence, preamble format)
- [ ] Mentions uplink interference as a cause
- [ ] Mentions coverage hole / cell edge as a cause
- [ ] Gives specific, actionable resolution steps (not acronym lists)
- [ ] Does NOT invent concepts

### 2.3 Follow-up Question (No Context)
```
Query 1: "VoLTE call setup failure rate exceeds 10% in North region"
Query 2: "what are the resolution steps for this?"
```
**1.5B got wrong:**
- Query 2 had no context of Query 1
- Generated generic S1/Core diagnosis instead of VoLTE resolution

**7B should get right:**
- [ ] Query 2 references VoLTE from Query 1
- [ ] Resolution steps are specific to VoLTE (not generic)
- [ ] Mentions IMS-specific resolution (P-CSCF, bearer, DNS, SIP traces)

### 2.4 Multi-Agent Chain — Diagnose + Config (Hallucinated Config)
```
Query: "Diagnose high CPU on ENB-5432 and suggest config changes to prevent it"
```
**1.5B got wrong:**
- IncidentAgent: Domain "Transport" (should be RAN)
- ConfigAgent: Generated repetition loop of "n3x, n3x10, n3x16...n3x5760" — complete hallucination

**7B should get right:**
- [ ] IncidentAgent: Domain RAN
- [ ] IncidentAgent: Causes include handover load, connected UE count, software bug
- [ ] ConfigAgent: Generates actual MLB / load balancing YAML config
- [ ] ConfigAgent: Config is relevant to the diagnosis (not random numbers)
- [ ] No repetition loops

### 2.5 ERAB Drop Rate (Generic vs Expert)
```
Query: "Our ERAB drop rate is at 2.8%, what should I investigate?"
```
**1.5B produced:**
- Template-like response, ~30% accurate content

**7B should produce:**
- [ ] Classifies into buckets (Radio / Mobility / Transport / Congestion)
- [ ] Provides specific KPIs to check per bucket
- [ ] Mentions correlation analysis approach
- [ ] Gives actionable first steps (Top N worst cells, pattern clustering)

### 2.6 Contextualise to My Network
```
Query 1: "RACH failure rate exceeds 15% on cell CELL-45678"
Query 2: "if I have to contextualise to my network what is needed?"
```
**1.5B got wrong:**
- Classified as "config" (wrong — it's a follow-up)
- Generated completely hallucinated YAML with fake node names

**7B should get right:**
- [ ] Detects as follow-up to RACH question
- [ ] Explains what network-specific data is needed (cell parameters, neighbor list, interference scans, drive test data)
- [ ] Does NOT generate random YAML

### 2.7 RAN Interference Question via RAG
```
Query: "how to find what's interference in RAN?"
```
**1.5B + RAG got wrong:**
- Dumped a raw table from a 2008 femtocell study
- Repetition loop after row 5

**7B + RAG should get right:**
- [ ] Explains practical interference hunting methods
- [ ] Mentions: spectrum scan, PIM testing, SINR/RSSI analysis
- [ ] Mentions: co-channel, adjacent channel, external interference types
- [ ] Does NOT dump raw tables from retrieved documents
- [ ] Synthesizes information in own words

---

## 3. Quality Characteristics to Evaluate

For each response, assess:

| Criterion | What to Check |
|-----------|--------------|
| **Domain accuracy** | Does it correctly identify RAN/Core/Transport/IMS? |
| **Cause accuracy** | Are the listed causes actually correct for this alarm? |
| **Hallucination** | Does it invent concepts, protocols, or node names? |
| **Actionable steps** | Can an engineer actually follow these steps? |
| **Specificity** | Does it give specific values/thresholds or just "check X"? |
| **No repetition** | Does the response avoid loops and acronym dumping? |
| **RAG synthesis** | Does it explain retrieved context in own words (not copy tables)? |
| **Follow-up context** | Does it remember previous conversation? |
| **Multi-agent chain** | Do chained agents produce coherent, connected output? |

---

## 4. Agent System Re-benchmark

After importing 7B fine-tuned model, re-run:

```bash
# Step 1: Run FT-7B standalone
python scripts/evaluation/operational_benchmark.py --model 7b-finetuned

# Step 2: Update agent system to use FT-7B instead of 1.5B for Incident/Config
# Then run agent benchmark
python scripts/evaluation/operational_benchmark.py --agents
```

**Expected Agent System with FT-7B: 90%+**

---

## 5. TeleQnA Re-benchmark

```bash
# Run TeleQnA on FT-7B
python scripts/evaluation/eval_teleqna.py  # (update to use 7B model)
```

| Model | Expected TeleQnA Score |
|-------|----------------------|
| Base 1.5B | 57% |
| TelcoGPT v3 (1.5B FT) | 56% |
| Base 7B | ~70% (estimate) |
| **FT-7B** | **75%+** |

---

## 6. Import Steps (When Colab Finishes)

1. Download `telco-slm-7b-adapter.zip` from Colab
2. Unzip to `models/telco-slm-7b-colab/adapter/`
3. For Ollama (GGUF): Download `telco-slm-7b-gguf.zip`, create Modelfile
4. For MLX: Convert HF adapter to MLX format
5. Update `agents/telco_agents.py` to point to new adapter
6. Run all tests above

---

## 7. Domain Correction Layer — Remove If 7B Gets It Right

A post-processing domain correction layer was added to `IncidentAgent` in Phase 2 to fix 1.5B misclassifications (e.g., VoLTE → "Transport" corrected to → "IMS/VoLTE"). This is a **workaround, not a fix**.

**Location:** `agents/telco_agents.py` → `IncidentAgent._correct_domain()`

**Test with FT-7B:**
- [ ] Run "VoLTE call setup failure rate exceeds 12%" — does FT-7B output `**Domain**: IMS` or `IMS/VoLTE` without the correction layer?
- [ ] Run "High CPU on eNodeB" — does FT-7B output `**Domain**: RAN` correctly?
- [ ] Run "BGP peer down" — does FT-7B output `**Domain**: Transport` correctly?
- [ ] Run "S1 link failure" — does FT-7B output `**Domain**: Core` correctly?

**If FT-7B classifies all domains correctly:**
→ Remove `_correct_domain()` method and `DOMAIN_KEYWORDS` dict from IncidentAgent
→ Remove the `response = self._correct_domain(description, response)` call in `diagnose()`
→ The correction layer should NOT be needed with a properly trained 7B model

**If FT-7B still misclassifies some domains:**
→ Keep the correction layer as a safety net
→ Improve training data for those specific domains

---

## 8. Decision After Testing

Based on results, decide:

| Result | Action |
|--------|--------|
| FT-7B scores 85%+ on benchmark | Ship it — replace 1.5B in all agents |
| FT-7B scores 75-85% | Good improvement, continue with more training data |
| FT-7B scores <75% | Need more training iterations (resume on Colab) or better data |
| RAG+FT-7B stops table dumping | Enable RAG for Knowledge Agent in production |
| Follow-ups work with context | Phase 2 conversation memory is validated |
| Multi-agent chain produces coherent output | Phase 2 chaining is validated |
