"""
TelcoGPT — FastAPI Server
Exposes the agent system via REST API.

Usage:
    uvicorn app.api_server:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Consilium API",
    description="Consilium — Network Intelligence Platform. Multi-agent system for incident diagnosis, config generation, and 3GPP knowledge.",
    version="1.0.0",
)

# Global orchestrator — initialized on first request
_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from agents.telco_agents import AgentOrchestrator
        _orchestrator = AgentOrchestrator(skip_rag=True)
    return _orchestrator


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    use_memory: bool = True


class QueryResponse(BaseModel):
    answer: str
    agent: str
    category: str
    sources: list[str] = []
    plan: list[str] = []
    is_followup: bool = False
    context_used: bool = False
    elapsed_seconds: float = 0.0
    memory_entries: int = 0


class MemoryEntry(BaseModel):
    role: str
    content: str
    agent: Optional[str] = None
    category: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "name": "Consilium API",
        "version": "1.0.0",
        "agents": [
            "SupervisorAgent (Consilium v4.1 — routing)",
            "IncidentAgent (Consilium v4.1)",
            "ConfigAgent (Consilium v4.1)",
            "KnowledgeAgent (RAG + Consilium v4.1)",
            "GenericAgent (Consilium v4.1)",
            "InvestigatorAgent (Consilium v4.1 + Tools)",
        ],
        "endpoints": ["/query", "/memory", "/clear", "/health"],
    }


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """Send a query to the Consilium agent system."""
    orch = get_orchestrator()
    response = orch.run(request.query, use_memory=request.use_memory)

    return QueryResponse(
        answer=response.answer,
        agent=response.agent,
        category=response.category,
        sources=response.sources,
        plan=response.metadata.get("plan", []),
        is_followup=response.metadata.get("is_followup", False),
        context_used=response.metadata.get("context_used", False),
        elapsed_seconds=response.elapsed_seconds,
        memory_entries=len(orch.memory),
    )


@app.get("/memory")
def get_memory():
    """Get conversation history."""
    orch = get_orchestrator()
    entries = []
    for entry in orch.memory.history:
        entries.append(MemoryEntry(
            role=entry["role"],
            content=entry["content"][:200],
            agent=entry.get("agent"),
            category=entry.get("category"),
        ))
    return {"entries": entries, "count": len(entries)}


@app.post("/clear")
def clear_memory():
    """Clear conversation memory."""
    orch = get_orchestrator()
    orch.clear_memory()
    return {"status": "cleared"}


@app.get("/health")
def health():
    """Health check."""
    orch = get_orchestrator()
    return {
        "status": "healthy",
        "ollama": orch.ollama is not None,
        "model": "llama-telco-v41",
        "rag": orch.rag is not None,
        "memory_entries": len(orch.memory),
    }
