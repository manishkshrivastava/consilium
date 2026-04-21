"""
Consilium — Agentic Framework
==============================
Multi-agent system for telecommunications operations powered by Consilium v4.1
(Llama 3.1 8B fine-tuned via QLoRA, served by Ollama), with optional RAG grounding
from 3GPP specifications stored in ChromaDB.

Architecture:
    User Query
        |
    SupervisorAgent  (Consilium v4.1 — classification + routing)
        |
    +---+---+--------+-----------+------------+--------+
    |       |        |           |            |        |
 Incident Config Knowledge  Investigator  Factory  Generic
  (v4.1) (v4.1) (RAG+v4.1) (Tools+v4.1) (dynamic) (v4.1)

Author : Manish Kumar Shrivastava
Created: 2026-03-19
Updated: 2026-04-08 (Phase 3C — Agent Factory, guardrails, Consilium rebrand)
"""

import json
import os
import time
import logging
import textwrap
from dataclasses import dataclass, field
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Prevent tokenizers fork-safety warning
# ---------------------------------------------------------------------------
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("telco_agents")

# ---------------------------------------------------------------------------
# Project paths (resolved relative to this file)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "rag", "vector_db", "chroma_3gpp")
MLX_MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"  # Legacy — MLX retired, all agents use Ollama v4.1
MLX_ADAPTER_PATH = os.path.join(PROJECT_ROOT, "models", "telco-slm-v3-mlx", "adapter")

# ---------------------------------------------------------------------------
# Shared system prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are Consilium, an intelligent telecom network assistant specialized in telecommunications. "
    "You have deep knowledge of 3GPP standards, network architecture (RAN, Core, "
    "Transport, IMS/VoLTE), alarm management, configuration, optimization, and fault diagnosis. "
    "Provide accurate, concise, and actionable answers."
)


# =========================================================================
# Data classes
# =========================================================================
@dataclass
class AgentResponse:
    """Standardised response returned by every agent and the orchestrator."""
    answer: str
    agent: str
    category: str
    sources: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    elapsed_seconds: float = 0.0


# =========================================================================
# ConversationMemory — Phase 2: multi-turn context
# =========================================================================
class ConversationMemory:
    """
    Maintains conversation history for multi-turn interactions.
    Stores the last N exchanges and provides context summary for agents.
    """

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.history: list[dict] = []  # [{role, content, agent, category}]

    def add_user_message(self, message: str):
        self.history.append({
            "role": "user",
            "content": message,
        })
        self._trim()

    def add_assistant_response(self, response: AgentResponse):
        self.history.append({
            "role": "assistant",
            "content": response.answer,
            "agent": response.agent,
            "category": response.category,
        })
        self._trim()

    def _trim(self):
        """Keep only the last max_turns * 2 entries (user + assistant pairs)."""
        max_entries = self.max_turns * 2
        if len(self.history) > max_entries:
            self.history = self.history[-max_entries:]

    def get_context_summary(self) -> str:
        """Return a condensed summary of recent conversation for the Supervisor."""
        if not self.history:
            return ""

        lines = []
        for entry in self.history[-6:]:  # Last 3 turns
            role = entry["role"].upper()
            content = entry["content"][:150]
            if entry.get("agent"):
                lines.append(f"[{role} via {entry['agent']}]: {content}")
            else:
                lines.append(f"[{role}]: {content}")

        return "Recent conversation:\n" + "\n".join(lines)

    def get_last_response(self) -> Optional[AgentResponse]:
        """Return the last assistant response, if any."""
        for entry in reversed(self.history):
            if entry["role"] == "assistant":
                return AgentResponse(
                    answer=entry["content"],
                    agent=entry.get("agent", ""),
                    category=entry.get("category", ""),
                )
        return None

    def clear(self):
        self.history = []

    def __len__(self):
        return len(self.history)


# =========================================================================
# OllamaClient — lightweight wrapper for the Ollama HTTP API
# =========================================================================
class OllamaClient:
    """Call any model served by a local Ollama instance."""

    BASE_URL = "http://localhost:11434"

    def __init__(self, model: str = "llama-telco-v41", timeout: int = 120):
        self.model = model
        self.timeout = timeout
        logger.info("OllamaClient initialised  model=%s", self.model)

    # ----- low-level helpers -----
    def generate(self, prompt: str, system: str = SYSTEM_PROMPT) -> str:
        """Single-turn generation via /api/generate."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        try:
            resp = requests.post(
                f"{self.BASE_URL}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except requests.RequestException as exc:
            logger.error("Ollama /api/generate failed: %s", exc)
            return f"[Error communicating with Ollama: {exc}]"

    def chat(self, messages: list[dict], system: str = SYSTEM_PROMPT) -> str:
        """Multi-turn chat via /api/chat."""
        full_messages = [{"role": "system", "content": system}] + messages
        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": False,
        }
        try:
            resp = requests.post(
                f"{self.BASE_URL}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
        except requests.RequestException as exc:
            logger.error("Ollama /api/chat failed: %s", exc)
            return f"[Error communicating with Ollama: {exc}]"


# =========================================================================
# MLXClient — local fine-tuned SLM via mlx-lm
# =========================================================================
class MLXClient:
    """Load the fine-tuned TelcoGPT v3 model once and serve generations."""

    def __init__(
        self,
        model_name: str = MLX_MODEL_NAME,
        adapter_path: str = MLX_ADAPTER_PATH,
        max_tokens: int = 512,
    ):
        self.model_name = model_name
        self.adapter_path = adapter_path
        self.max_tokens = max_tokens
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load the MLX model + adapter once at init time."""
        try:
            from mlx_lm import load  # type: ignore

            logger.info(
                "Loading MLX model=%s  adapter=%s ...",
                self.model_name,
                self.adapter_path,
            )
            self.model, self.tokenizer = load(
                self.model_name, adapter_path=self.adapter_path
            )
            logger.info("MLX model loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load MLX model: %s", exc)
            self.model = None
            self.tokenizer = None

    def generate(self, prompt: str, system: str = SYSTEM_PROMPT) -> str:
        """Generate a response using the local fine-tuned SLM."""
        if self.model is None or self.tokenizer is None:
            return "[Error: MLX model not loaded]"

        try:
            from mlx_lm import generate as mlx_generate  # type: ignore

            # Build a chat-style prompt via the tokenizer's chat template
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            formatted_prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            response = mlx_generate(
                self.model,
                self.tokenizer,
                prompt=formatted_prompt,
                max_tokens=self.max_tokens,
            )
            return response.strip()
        except Exception as exc:
            logger.error("MLX generation failed: %s", exc)
            return f"[Error during MLX generation: {exc}]"


# =========================================================================
# RAGRetriever — ChromaDB + sentence-transformers
# =========================================================================
class RAGRetriever:
    """Retrieve relevant 3GPP specification chunks from ChromaDB."""

    def __init__(
        self,
        db_path: str = CHROMA_DB_PATH,
        collection_name: str = "telco_3gpp",
        top_k: int = 5,
    ):
        self.db_path = db_path
        self.collection_name = collection_name
        self.top_k = top_k
        self.collection = None
        self._init_collection()

    def _init_collection(self):
        """Connect to the persistent ChromaDB and load the collection."""
        try:
            import chromadb  # type: ignore
            from chromadb.utils import embedding_functions  # type: ignore

            client = chromadb.PersistentClient(path=self.db_path)
            # Load collection without specifying embedding function to avoid
            # conflict with the one persisted during index build.
            self.collection = client.get_collection(
                name=self.collection_name,
            )
            # We'll use LlamaIndex's HuggingFaceEmbedding for query embedding
            # instead of ChromaDB's built-in embedding function.
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            self._embed_model = HuggingFaceEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device="mps",
            )
            logger.info(
                "RAG collection '%s' loaded  (%d documents)",
                self.collection_name,
                self.collection.count(),
            )
        except Exception as exc:
            logger.error("Failed to load ChromaDB collection: %s", exc)
            self.collection = None

    def retrieve(self, query: str) -> list[dict]:
        """Return top-k chunks as a list of dicts with 'text' and 'metadata'."""
        if self.collection is None:
            logger.warning("RAG collection not available — returning empty results.")
            return []

        try:
            # Generate embedding for the query using our model
            query_embedding = self._embed_model.get_text_embedding(query)
            results = self.collection.query(
                query_embeddings=[query_embedding], n_results=self.top_k
            )
            chunks = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            for doc, meta in zip(documents, metadatas):
                chunks.append({"text": doc, "metadata": meta})
            return chunks
        except Exception as exc:
            logger.error("RAG retrieval failed: %s", exc)
            return []


# =========================================================================
# Agent implementations
# =========================================================================

class SupervisorAgent:
    """
    Classifies incoming queries and plans agent execution.
    Phase 2: Supports conversation context and multi-agent chaining.
    """

    CATEGORIES = ("incident", "investigate", "knowledge", "config", "general")

    CLASSIFICATION_PROMPT = textwrap.dedent("""\
        Classify the following user query into EXACTLY ONE category.
        Reply with ONLY the category name, nothing else.

        Categories:
        - incident : active alarms, current faults, live outages, ongoing degradation, "failure rate is X%"
        - investigate : root cause analysis, "why was", "identify the cause", "what happened at", "investigate why", "diagnose why", needs data lookup, "check performance", "check if performing", "is performing normally", "check status of SITE-", "compare performance", "compare SITE-", "which site needs attention"
        - knowledge : explaining concepts, architecture, topology, "what is", "how does", "explain", protocol details, "what nodes", "what are the components"
        - config : generate configuration, parameter changes, YAML commands, "configure", "set up", "create config"
        - general : greetings, off-topic, opinions, comparisons
        - followup : references previous answer ("this", "that", "the above", "more details", "elaborate", "what about", "can you explain point")

        IMPORTANT RULES:
        - Questions asking "why" something happened or "root cause" or "identify the cause" are INVESTIGATE
        - Questions asking "what nodes" or "what topology" or "explain the architecture" are KNOWLEDGE, not incident
        - Questions asking to "elaborate" or "tell me more" about a previous answer are FOLLOWUP
        - Only classify as "incident" if there is a CURRENT active alarm or degradation being reported
        - "investigate" means the user wants data-driven analysis, not just a textbook answer
        - Questions asking to "check" a specific site/cell performance are INVESTIGATE (they need real data lookup)
        - Questions asking to "compare" two sites or cells are INVESTIGATE (they need real data from both sites)

        {context}

        User query: {query}

        Category:""")

    MULTI_AGENT_PROMPT = textwrap.dedent("""\
        You are a telecom operations supervisor. Analyze the user's query and determine
        if it needs multiple agents to handle. Reply with a JSON array of agent steps.

        Available agents:
        - incident: diagnoses alarms, faults, KPI issues
        - knowledge: looks up 3GPP specs and standards
        - config: generates network configuration YAML

        If the query needs just one agent, return a single-element array.
        If it needs multiple agents in sequence, return them in order.

        Examples:
        - "High CPU on eNodeB" → ["incident"]
        - "What is 5QI?" → ["knowledge"]
        - "Diagnose this alarm and suggest config fix" → ["incident", "config"]
        - "What does 3GPP say about HARQ and generate DRX config" → ["knowledge", "config"]

        {context}

        User query: {query}

        Reply with ONLY a JSON array like ["incident"] or ["incident", "config"]:""")

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def classify(self, query: str, context: str = "") -> str:
        """Return one of the category strings. Supports conversation context."""
        prompt = self.CLASSIFICATION_PROMPT.format(query=query, context=context)
        raw = self.ollama.generate(prompt, system="You are a query classifier.")
        category = raw.strip().lower().rstrip(".").strip()
        for cat in self.CATEGORIES:
            if cat in category:
                return cat
        if "followup" in category or "follow" in category:
            return "followup"
        logger.warning("Supervisor returned unknown category '%s' — defaulting to 'general'.", raw)
        return "general"

    def plan_agents(self, query: str, context: str = "") -> list[str]:
        """
        Phase 2: Determine if query needs multiple agents.
        Returns list of agent categories to execute in sequence.
        """
        prompt = self.MULTI_AGENT_PROMPT.format(query=query, context=context)
        raw = self.ollama.generate(prompt, system="You are a task planner. Reply only with a JSON array.")
        raw = raw.strip()

        # Try to parse JSON array
        try:
            # Find the array in the response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                plan = json.loads(raw[start:end])
                # Validate
                valid_plan = [step for step in plan if step in self.CATEGORIES]
                if valid_plan:
                    return valid_plan
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback to single classification
        category = self.classify(query, context)
        return [category]


class IncidentAgent:
    """Diagnoses alarms / incidents using the fine-tuned 7B model (v4.1)."""

    PROMPT_TEMPLATE = textwrap.dedent("""\
        You are a telecom incident diagnosis expert.
        Analyse the following alarm or incident description and provide a structured diagnosis.

        Alarm / Incident:
        {description}

        Respond in this format:
        **Severity**: Critical / Major / Minor / Warning
        **Domain**: RAN / Core / Transport / VAS / Platform
        **Probable Causes**:
        1. ...
        2. ...
        **Resolution Steps**:
        1. ...
        2. ...
        **Additional Notes**: ...""")

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def diagnose(self, description: str) -> str:
        prompt = self.PROMPT_TEMPLATE.format(description=description)
        return self.ollama.generate(prompt)


class ConfigAgent:
    """Generates YAML network configuration from natural-language intent."""

    PROMPT_TEMPLATE = textwrap.dedent("""\
        You are a telecom network configuration expert.
        Convert the following natural language intent into a valid YAML network configuration.
        Include all relevant parameters and add inline comments.

        Intent:
        {intent}

        YAML Configuration:""")

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def configure(self, intent: str) -> str:
        prompt = self.PROMPT_TEMPLATE.format(intent=intent)
        return self.ollama.generate(prompt)


class KnowledgeAgent:
    """Answers 3GPP / standards questions with RAG-grounded synthesis."""

    SYNTHESIS_PROMPT = textwrap.dedent("""\
        You are Consilium, an expert in 3GPP telecommunications standards.
        Use ONLY the reference material below to answer the user's question.
        NEVER copy raw tables. ALWAYS explain in your own words.
        Give practical actionable answers.
        If the references do not contain enough information, say so.
        Cite the source document where possible.

        --- REFERENCE MATERIAL ---
        {context}
        --- END REFERENCE MATERIAL ---

        User question: {query}

        Answer:""")

    def __init__(self, rag: RAGRetriever, ollama: OllamaClient):
        self.rag = rag
        self.ollama = ollama

    def answer(self, query: str) -> tuple[str, list[dict]]:
        """Return (answer_text, list_of_source_chunks)."""
        chunks = self.rag.retrieve(query)
        if not chunks:
            return (
                "I could not find relevant 3GPP references for your question. "
                "Please try rephrasing or ask a general question.",
                [],
            )

        # Build context block from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_label = chunk.get("metadata", {}).get("source", "unknown")
            context_parts.append(f"[Source {i}: {source_label}]\n{chunk['text']}")
        context = "\n\n".join(context_parts)

        prompt = self.SYNTHESIS_PROMPT.format(context=context, query=query)
        answer = self.ollama.generate(prompt)
        return answer, chunks


class GenericAgent:
    """Handles general / off-topic queries with Consilium v4.1."""

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def answer(self, query: str) -> str:
        return self.ollama.chat(
            messages=[{"role": "user", "content": query}],
            system=SYSTEM_PROMPT,
        )


# =========================================================================
# AgentOrchestrator — ties everything together
# =========================================================================
class AgentOrchestrator:
    """
    Main entry-point for the agentic framework.

    Usage:
        orchestrator = AgentOrchestrator()
        response = orchestrator.run("High VSWR alarm on cell sector 2")
        print(response.answer)
    """

    def __init__(self, skip_mlx: bool = False, skip_rag: bool = False):
        """
        Initialise all agents and their backing models.

        Parameters
        ----------
        skip_mlx : bool
            If True, skip loading the MLX model (useful for quick testing
            with only Ollama-backed agents).
        skip_rag : bool
            If True, skip loading the ChromaDB collection.
        """
        logger.info("=" * 60)
        logger.info("Initialising AgentOrchestrator ...")
        logger.info("=" * 60)

        # -- SLM client (Consilium v4.1 via Ollama) --
        self.ollama = OllamaClient(model="llama-telco-v41")

        # MLX no longer needed — all agents use Ollama v4.1
        self.mlx = None
        logger.info("MLX retired — all agents use Consilium v4.1 via Ollama.")

        # -- RAG retriever --
        self.rag: Optional[RAGRetriever] = None
        if not skip_rag:
            self.rag = RAGRetriever()
        else:
            logger.info("RAG retriever loading skipped (skip_rag=True).")

        # -- Agents (all use v4.1 via Ollama now — no MLX dependency) --
        self.supervisor = SupervisorAgent(self.ollama)
        self.incident_agent = IncidentAgent(self.ollama)
        self.config_agent = ConfigAgent(self.ollama)
        self.knowledge_agent = (
            KnowledgeAgent(self.rag, self.ollama) if self.rag else None
        )
        self.generic_agent = GenericAgent(self.ollama)

        # -- Investigator Agent (Phase 3 — tool-using agentic) --
        try:
            from agents.investigator import InvestigatorAgent
            self.investigator = InvestigatorAgent(self.ollama, rag_retriever=self.rag)
            logger.info("InvestigatorAgent loaded (tools + RAG, truly agentic).")
        except Exception as exc:
            logger.warning("InvestigatorAgent not available: %s", exc)
            self.investigator = None

        # -- Agent Registry + Factory (Phase 3C — self-evolving agents) --
        try:
            from agents.agent_registry import AgentRegistry
            from agents.agent_factory import AgentFactory
            self.registry = AgentRegistry()
            self.factory = AgentFactory(self.ollama, self.registry)
            stats = self.registry.get_stats()
            logger.info("AgentRegistry loaded: %d agents (%d active, %d candidates)",
                        stats["total_agents"], stats["active"], stats["candidates"])
        except Exception as exc:
            logger.warning("AgentFactory not available: %s", exc)
            self.registry = None
            self.factory = None

        # -- Conversation memory (Phase 2) --
        self.memory = ConversationMemory(max_turns=10)

        logger.info("AgentOrchestrator ready (Phase 3C: memory + multi-agent + agent factory).")

    # -----------------------------------------------------------------
    def _run_single_agent(self, category: str, query: str) -> tuple[str, str, list]:
        """Execute a single agent and return (answer, agent_name, sources)."""
        sources = []

        if category == "investigate" and self.investigator:
            agent_name = "InvestigatorAgent (Tools + RAG, Agentic)"
            result = self.investigator.investigate(query)
            answer = result["answer"]
            tools_used = result.get("tools_used", [])
            rag_sources = result.get("rag_sources", [])

            header = f"**Investigation completed** — used: {', '.join(tools_used)}\n"
            header += f"**Steps taken:** {result.get('findings_count', 0)} data lookups"
            if rag_sources:
                header += f"\n**3GPP references:** {', '.join(rag_sources[:3])}"
            header += "\n\n---\n\n"
            answer = header + answer

            # Add RAG sources to the response sources list
            for src in rag_sources:
                sources.append({"metadata": {"source": src}})

        elif category == "incident" and self.incident_agent:
            agent_name = "IncidentAgent (Consilium v4.1)"
            answer = self.incident_agent.diagnose(query)

        elif category == "config" and self.config_agent:
            agent_name = "ConfigAgent (Consilium v4.1)"
            answer = self.config_agent.configure(query)

        elif category == "knowledge" and self.knowledge_agent:
            agent_name = "KnowledgeAgent (RAG + Consilium v4.1)"
            answer, sources = self.knowledge_agent.answer(query)

        else:
            # GUARDRAIL: Check if query references specific network entities
            # If yes → route to Investigator (needs real data, not SLM memory)
            import re
            has_specific_entity = bool(re.search(
                r'SITE-|CELL-|ENB-|GNB-|cell\s+\d{3,}|site\s+\d{3,}|'
                r'compare.*(?:site|cell|performance)|'
                r'check.*(?:kpi|alarm|performance|status)',
                query, re.IGNORECASE
            ))
            if has_specific_entity and self.investigator:
                logger.info("Data-aware routing: query references specific entities → Investigator")
                agent_name = "InvestigatorAgent (Tools + RAG, Agentic)"
                result = self.investigator.investigate(query)
                answer = result["answer"]
                tools_used = result.get("tools_used", [])
                skills_used = result.get("skills_used", [])

                header = f"**Investigation completed** — skills: {', '.join(skills_used) if skills_used else 'legacy'}\n"
                header += f"**Tools used:** {', '.join(tools_used)}\n"
                header += f"**Steps taken:** {result.get('findings_count', 0)} data lookups\n\n---\n\n"
                answer = header + answer

                return answer, agent_name, sources

            # Phase 3C: Check registry for dynamic agents before falling back to Generic
            dynamic_agent = None
            if self.registry:
                dynamic_agent = self.registry.find_by_keywords(query)

            if dynamic_agent:
                # Use existing dynamic agent (candidate or active)
                agent_name = f"{dynamic_agent['name']} ({dynamic_agent['status']} — uses: {dynamic_agent['use_count']})"
                answer = self.factory.execute_with_agent(dynamic_agent, query)
                # Log the run
                import time
                self.registry.log_run(
                    agent_id=dynamic_agent["id"],
                    query=query,
                    response_summary=answer[:200],
                    latency_ms=0,
                    success=True,  # Assume success for now; feedback loop will refine
                )
                logger.info("Used dynamic agent: %s (id=%d, status=%s)",
                            dynamic_agent["name"], dynamic_agent["id"], dynamic_agent["status"])

            elif self.factory:
                # No match found — create a candidate agent via factory
                logger.info("No specialist agent found. Attempting Agent Factory...")
                new_agent = self.factory.create_agent_for_query(query)

                if new_agent:
                    agent_name = f"{new_agent['name']} ({new_agent['status']} — uses: {new_agent['use_count']})"
                    answer = self.factory.execute_with_agent(new_agent, query)
                    self.registry.log_run(
                        agent_id=new_agent["id"],
                        query=query,
                        response_summary=answer[:200],
                        latency_ms=0,
                        success=True,
                    )
                    logger.info("Factory created and used: %s (id=%d)",
                                new_agent["name"], new_agent["id"])
                else:
                    # Factory failed — fall back to Generic
                    agent_name = "GenericAgent (Consilium v4.1)"
                    answer = self.generic_agent.answer(query)
            else:
                agent_name = "GenericAgent (Consilium v4.1)"
                answer = self.generic_agent.answer(query)

        return answer, agent_name, sources

    # -----------------------------------------------------------------
    def run(self, query: str, use_memory: bool = True) -> AgentResponse:
        """
        Phase 2: Classify with conversation context, support multi-agent
        chaining, and maintain conversation memory.
        """
        t0 = time.time()

        # Get conversation context for the Supervisor
        context = self.memory.get_context_summary() if use_memory else ""

        # Step 1: Detect obvious follow-ups before even asking Supervisor
        followup_indicators = [
            "this", "that", "the above", "elaborate", "more detail", "tell me more",
            "what about", "can you explain", "resolution steps for this",
            "how to fix this", "what nodes", "contextualise", "contextualize",
            "my network", "in our case", "for this issue", "regarding this",
            "based on that", "following up", "as mentioned",
            "if the", "if this", "if it", "what if", "same for", "how about",
            "and for", "but for", "instead of", "rather than",
        ]
        query_lower = query.lower()
        is_likely_followup = (
            use_memory
            and len(self.memory.history) >= 2
            and any(indicator in query_lower for indicator in followup_indicators)
        )

        if is_likely_followup:
            last = self.memory.get_last_response()
            if last:
                enriched_query = (
                    f"Previous context: {last.answer[:500]}\n\n"
                    f"Follow-up question: {query}"
                )
                # For short follow-ups (< 8 words), inherit the previous category
                # "if Nokia?" or "what about Ericsson?" should stay in the same domain
                word_count = len(query.strip().split())
                if word_count <= 8 and last.category:
                    category = last.category
                    logger.info("Short follow-up (%d words) → inheriting category: %s", word_count, category)
                else:
                    category = self.supervisor.classify(enriched_query, context)
                    logger.info("Follow-up detected (keyword match) → classified as: %s", category)
                query = enriched_query
            else:
                category = self.supervisor.classify(query, context)
        else:
            # Step 1: Normal classification with context
            category = self.supervisor.classify(query, context)

        logger.info("Supervisor classified query as: %s", category)

        # Step 1b: Handle explicit followup classification
        if category == "followup":
            last = self.memory.get_last_response()
            if last:
                enriched_query = (
                    f"Previous context: {last.answer[:500]}\n\n"
                    f"Follow-up question: {query}"
                )
                category = last.category
                logger.info("Followup category → re-routing to: %s", category)
                query = enriched_query
            else:
                category = "general"

        # Step 2: Check if multi-agent chaining is needed
        # Only attempt multi-agent planning for complex queries (long queries with "and"/"then")
        needs_planning = (
            " and " in query.lower()
            or " then " in query.lower()
            or ("diagnose" in query.lower() and "config" in query.lower())
            or ("explain" in query.lower() and "generate" in query.lower())
        )

        if needs_planning:
            plan = self.supervisor.plan_agents(query, context)
            logger.info("Agent plan: %s", plan)
        else:
            plan = [category]  # Use the Supervisor's classification directly
            logger.info("Agent plan (from classification): %s", plan)

        if len(plan) <= 1:
            # Single agent — use the CLASSIFIED category, not the plan
            answer, agent_name, sources = self._run_single_agent(
                category, query
            )
        else:
            # Multi-agent chaining
            logger.info("Multi-agent chain: %s", " → ".join(plan))
            chain_answers = []
            all_sources = []
            agent_names = []
            accumulated_context = query

            for step_category in plan:
                step_answer, step_agent, step_sources = self._run_single_agent(
                    step_category, accumulated_context
                )
                chain_answers.append(f"**[{step_agent}]:**\n{step_answer}")
                all_sources.extend(step_sources)
                agent_names.append(step_agent)
                # Feed the output to the next agent as context
                accumulated_context = (
                    f"Original question: {query}\n\n"
                    f"Previous analysis:\n{step_answer}\n\n"
                    f"Based on the above, continue with the next step."
                )

            answer = "\n\n---\n\n".join(chain_answers)
            agent_name = " → ".join(agent_names)
            sources = all_sources

        elapsed = time.time() - t0

        response = AgentResponse(
            answer=answer,
            agent=agent_name if len(plan) <= 1 else f"Chain: {agent_name}",
            category=category,
            sources=[
                s.get("metadata", {}).get("source", "unknown")
                if isinstance(s, dict) else str(s)
                for s in sources
            ],
            metadata={
                "plan": plan,
                "context_used": bool(context),
                "is_followup": category == "followup",
            },
            elapsed_seconds=round(elapsed, 2),
        )

        # Save to memory
        if use_memory:
            self.memory.add_user_message(query)
            self.memory.add_assistant_response(response)

        return response

    # -----------------------------------------------------------------
    def clear_memory(self):
        """Reset conversation history."""
        self.memory.clear()
        logger.info("Conversation memory cleared.")
