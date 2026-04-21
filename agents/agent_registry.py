"""
Consilium — Agent Registry
SQLite-backed persistent storage for dynamic agent configurations.

Agent lifecycle: candidate → active → disabled → pruned

Responsibilities:
- Create / update / fetch / list agents
- Activate / deactivate / prune
- Domain similarity / duplicate checks
- Run logging for promotion decisions
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("agent_registry")

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "consilium.db"

# Agent states
STATUS_CANDIDATE = "candidate"
STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUS_PRUNED = "pruned"

# Promotion threshold
MIN_USES_FOR_PROMOTION = 2
MIN_SUCCESS_RATE_FOR_PROMOTION = 0.6


class AgentRegistry:
    """SQLite-backed agent registry with lifecycle management."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()
        logger.info("AgentRegistry initialized: %s", self.db_path)

    def _init_db(self):
        """Create tables if they don't exist."""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                domain TEXT NOT NULL UNIQUE,
                description TEXT,
                system_prompt TEXT NOT NULL,
                keywords_json TEXT NOT NULL,
                tools_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'candidate',
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                use_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                quality_score REAL NOT NULL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                response_summary TEXT,
                used_tools_json TEXT,
                latency_ms INTEGER,
                user_followup_flag INTEGER DEFAULT 0,
                success_signal INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            );

            CREATE INDEX IF NOT EXISTS idx_agents_domain ON agents(domain);
            CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
            CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id ON agent_runs(agent_id);
        """)
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ─── Create / Save ────────────────────────────────────────

    def create_agent(self, name: str, domain: str, description: str,
                     system_prompt: str, keywords: list[str],
                     tools: list[str]) -> Optional[dict]:
        """
        Create a new candidate agent. Returns the agent dict or None if duplicate domain.
        """
        # Check for duplicate domain
        existing = self.find_similar_domain(domain, keywords)
        if existing:
            logger.warning(
                "Domain '%s' is too similar to existing agent '%s' (domain: '%s'). Not creating duplicate.",
                domain, existing["name"], existing["domain"]
            )
            return None

        # Validate
        if not self._validate_agent(name, domain, system_prompt, keywords, tools):
            return None

        now = datetime.now().isoformat()
        conn = self._connect()
        try:
            cursor = conn.execute(
                """INSERT INTO agents (name, domain, description, system_prompt,
                   keywords_json, tools_json, status, version, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (name, domain, description, system_prompt,
                 json.dumps(keywords), json.dumps(tools),
                 STATUS_CANDIDATE, now)
            )
            conn.commit()
            agent_id = cursor.lastrowid
            logger.info("Created candidate agent: %s (id=%d, domain=%s)", name, agent_id, domain)
            return self.get_agent(agent_id)
        except sqlite3.IntegrityError:
            logger.warning("Agent with domain '%s' already exists", domain)
            return None
        finally:
            conn.close()

    def _validate_agent(self, name: str, domain: str, system_prompt: str,
                        keywords: list[str], tools: list[str]) -> bool:
        """Quality gate: validate agent config before saving."""
        valid_tools = {"kpi_lookup", "alarm_query", "config_audit"}

        if not name or len(name) < 3:
            logger.warning("Agent validation failed: name too short")
            return False
        if not domain or len(domain) < 3:
            logger.warning("Agent validation failed: domain too short")
            return False
        if not system_prompt or len(system_prompt) < 50:
            logger.warning("Agent validation failed: system_prompt too short (min 50 chars)")
            return False
        if not keywords or len(keywords) < 3:
            logger.warning("Agent validation failed: need at least 3 keywords")
            return False
        if tools and not all(t in valid_tools for t in tools):
            invalid = [t for t in tools if t not in valid_tools]
            logger.warning("Agent validation failed: invalid tools: %s", invalid)
            return False

        return True

    # ─── Read / Query ─────────────────────────────────────────

    def get_agent(self, agent_id: int) -> Optional[dict]:
        """Get agent by ID."""
        conn = self._connect()
        row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def get_agent_by_domain(self, domain: str) -> Optional[dict]:
        """Get agent by exact domain name."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM agents WHERE domain = ? AND status IN (?, ?)",
            (domain, STATUS_CANDIDATE, STATUS_ACTIVE)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def list_agents(self, status: str = None) -> list[dict]:
        """List all agents, optionally filtered by status."""
        conn = self._connect()
        if status:
            rows = conn.execute(
                "SELECT * FROM agents WHERE status = ? ORDER BY use_count DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM agents WHERE status != ? ORDER BY status, use_count DESC",
                (STATUS_PRUNED,)
            ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def find_by_keywords(self, query: str) -> Optional[dict]:
        """
        Find the best matching active or candidate agent for a query.
        Uses word-level keyword overlap scoring (not embedding similarity).
        """
        # Break query into words
        query_words = set()
        for word in query.lower().replace("-", " ").replace("_", " ").split():
            if len(word) >= 3:
                query_words.add(word)

        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM agents WHERE status IN (?, ?) ORDER BY status ASC",
            (STATUS_ACTIVE, STATUS_CANDIDATE)
        ).fetchall()
        conn.close()

        best_match = None
        best_score = 0

        for row in rows:
            agent = self._row_to_dict(row)
            # Build word set from keywords
            agent_words = set()
            for kw in agent["keywords"]:
                for word in kw.lower().replace("_", " ").replace("-", " ").split():
                    if len(word) >= 3:
                        agent_words.add(word)

            # Count word overlaps
            overlap = len(query_words & agent_words)
            score = overlap

            # Also check agent name and domain words
            name_words = set(w.lower() for w in agent["name"].replace("Agent", "").split() if len(w) >= 3)
            domain_words = set(w.lower() for w in agent["domain"].replace("_", " ").split() if len(w) >= 3)
            score += len(query_words & name_words) * 0.5
            score += len(query_words & domain_words) * 0.5

            # Bonus for active agents (prefer active over candidate)
            if agent["status"] == STATUS_ACTIVE:
                score += 1

            if score > best_score and score >= 1.5:  # Lower threshold — 1.5 allows partial matches
                best_score = score
                best_match = agent

        return best_match

    # ─── Domain Similarity / Dedup ────────────────────────────

    def find_similar_domain(self, domain: str, keywords: list[str]) -> Optional[dict]:
        """
        Check if a similar domain already exists.
        Uses word-level keyword overlap — NOT embedding similarity.
        Returns the existing agent if overlap is significant, else None.
        """
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM agents WHERE status != ?", (STATUS_PRUNED,)
        ).fetchall()
        conn.close()

        # Break keywords into individual words for fuzzy matching
        new_words = set()
        for kw in keywords:
            for word in kw.lower().replace("_", " ").replace("-", " ").split():
                if len(word) >= 3:
                    new_words.add(word)
        # Also add domain words
        for word in domain.lower().replace("_", " ").split():
            if len(word) >= 3:
                new_words.add(word)

        for row in rows:
            existing = self._row_to_dict(row)
            existing_words = set()
            for kw in existing["keywords"]:
                for word in kw.lower().replace("_", " ").replace("-", " ").split():
                    if len(word) >= 3:
                        existing_words.add(word)
            for word in existing["domain"].lower().replace("_", " ").split():
                if len(word) >= 3:
                    existing_words.add(word)

            if not existing_words or not new_words:
                continue

            # Word-level overlap
            overlap = len(new_words & existing_words)
            min_set = min(len(new_words), len(existing_words))
            similarity = overlap / min_set if min_set > 0 else 0

            if similarity > 0.3 and overlap >= 3:
                return existing

            # Also check domain name word overlap
            domain_words_new = set(domain.lower().replace("_", " ").split())
            domain_words_existing = set(existing["domain"].lower().replace("_", " ").split())
            if len(domain_words_new & domain_words_existing) >= 1:
                return existing

        return None

    # ─── Lifecycle: Promote / Disable / Prune ─────────────────

    def promote_agent(self, agent_id: int) -> bool:
        """Promote a candidate to active status."""
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        if agent["status"] != STATUS_CANDIDATE:
            logger.warning("Can only promote candidate agents, current status: %s", agent["status"])
            return False
        if agent["use_count"] < MIN_USES_FOR_PROMOTION:
            logger.warning("Agent needs %d uses before promotion, current: %d",
                           MIN_USES_FOR_PROMOTION, agent["use_count"])
            return False

        success_rate = agent["success_count"] / max(1, agent["use_count"])
        if success_rate < MIN_SUCCESS_RATE_FOR_PROMOTION:
            logger.warning("Agent success rate %.1f%% below threshold %.1f%%",
                           success_rate * 100, MIN_SUCCESS_RATE_FOR_PROMOTION * 100)
            return False

        conn = self._connect()
        conn.execute(
            "UPDATE agents SET status = ? WHERE id = ?",
            (STATUS_ACTIVE, agent_id)
        )
        conn.commit()
        conn.close()
        logger.info("Promoted agent %d (%s) to active", agent_id, agent["name"])
        return True

    def disable_agent(self, agent_id: int) -> bool:
        """Disable an agent (keeps it in registry but not used for routing)."""
        conn = self._connect()
        conn.execute("UPDATE agents SET status = ? WHERE id = ?", (STATUS_DISABLED, agent_id))
        conn.commit()
        conn.close()
        logger.info("Disabled agent %d", agent_id)
        return True

    def prune_unused(self, min_age_days: int = 30) -> int:
        """Prune candidate agents that haven't been used in min_age_days."""
        cutoff = datetime.now().isoformat()
        conn = self._connect()
        cursor = conn.execute(
            """UPDATE agents SET status = ?
               WHERE status = ? AND use_count = 0
               AND created_at < datetime('now', ? || ' days')""",
            (STATUS_PRUNED, STATUS_CANDIDATE, f"-{min_age_days}")
        )
        count = cursor.rowcount
        conn.commit()
        conn.close()
        if count > 0:
            logger.info("Pruned %d unused candidate agents", count)
        return count

    # ─── Run Logging ──────────────────────────────────────────

    def log_run(self, agent_id: int, query: str, response_summary: str,
                used_tools: list[str] = None, latency_ms: int = 0,
                success: bool = False) -> int:
        """Log an agent execution. Returns run ID."""
        now = datetime.now().isoformat()
        conn = self._connect()

        # Insert run
        cursor = conn.execute(
            """INSERT INTO agent_runs (agent_id, query, response_summary,
               used_tools_json, latency_ms, success_signal, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, query, response_summary[:500],
             json.dumps(used_tools or []), latency_ms,
             1 if success else 0, now)
        )
        run_id = cursor.lastrowid

        # Update agent stats
        conn.execute(
            """UPDATE agents SET
               use_count = use_count + 1,
               success_count = success_count + ?,
               last_used_at = ?
               WHERE id = ?""",
            (1 if success else 0, now, agent_id)
        )
        conn.commit()
        conn.close()

        # Check if candidate should be auto-promoted
        agent = self.get_agent(agent_id)
        if agent and agent["status"] == STATUS_CANDIDATE:
            if (agent["use_count"] >= MIN_USES_FOR_PROMOTION and
                    agent["success_count"] / max(1, agent["use_count"]) >= MIN_SUCCESS_RATE_FOR_PROMOTION):
                self.promote_agent(agent_id)

        return run_id

    # ─── Helpers ──────────────────────────────────────────────

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a database row to a dict with parsed JSON fields."""
        d = dict(row)
        d["keywords"] = json.loads(d["keywords_json"])
        d["tools"] = json.loads(d["tools_json"])
        del d["keywords_json"]
        del d["tools_json"]
        return d

    def get_stats(self) -> dict:
        """Get registry statistics."""
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM agents WHERE status = ?", (STATUS_ACTIVE,)).fetchone()[0]
        candidates = conn.execute("SELECT COUNT(*) FROM agents WHERE status = ?", (STATUS_CANDIDATE,)).fetchone()[0]
        total_runs = conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0]
        conn.close()
        return {
            "total_agents": total,
            "active": active,
            "candidates": candidates,
            "total_runs": total_runs,
        }
