"""
Consilium — Streamlit Chat UI
Visual interface for the multi-agent telecom AI system.

Usage:
    streamlit run app/streamlit_ui.py
"""

import streamlit as st
import requests
import os

API_URL = "http://localhost:3002"
ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "consilium_icon.png")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Consilium",
    page_icon=ICON_PATH if os.path.exists(ICON_PATH) else "🧠",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    if os.path.exists(ICON_PATH):
        st.image(ICON_PATH, width=120)
    st.title("CONSILIUM")
    st.markdown("**Domain-trained. Agent-driven. Self-evolving.**")
    st.markdown("*Consilium = Deliberation, Judgment, Action (Latin)*")
    st.markdown("---")

    st.markdown("**Agents:**")
    st.markdown("""
    - 🎯 **Supervisor** — Routes queries
    - 🔧 **Incident** — Alarm diagnosis
    - ⚙️ **Config** — YAML generation
    - 📚 **Knowledge** — 3GPP specs (RAG)
    - 🔍 **Investigator** — Tool-based investigation
    - 🏭 **Factory** — Dynamic agent creation
    - 💬 **Generic** — General telco
    """)
    st.caption("All agents powered by Consilium v4.1 (Llama 3.1 8B)")

    st.markdown("---")

    st.markdown("**Capabilities:**")
    st.markdown("""
    - 🧠 Conversation memory (10 turns)
    - 🔗 Multi-agent chaining
    - 🔄 Follow-up detection
    - 🔍 Tool-based investigation (KPI, Alarm, Config)
    - 🏭 Self-evolving agent factory
    - 🛡️ Anti-hallucination guardrails
    - 📊 84.1% benchmark accuracy
    """)

    st.markdown("---")

    if st.button("🗑️ Clear Memory"):
        try:
            requests.post(f"{API_URL}/clear")
            st.session_state.messages = []
            st.success("Memory cleared!")
        except Exception:
            st.error("API not running. Start it first.")

    try:
        mem = requests.get(f"{API_URL}/memory", timeout=2).json()
        st.metric("Memory Entries", mem["count"])
    except Exception:
        st.warning("API not connected")

    st.markdown("---")
    st.markdown("**Try these:**")
    examples = [
        "High CPU on eNodeB ENB-5432 at 95%",
        "Investigate throughput degradation on SITE-METRO-002-S2",
        "Compare performance of SITE-METRO-001 and SITE-METRO-002",
        "Generate config for URLLC network slice",
        "How does NRF work in 5G SBA?",
        "VoLTE SIP 503 errors from P-CSCF",
        "How to optimize spectrum allocation for mmWave?",
        "What KPIs are impacted when a site goes down?",
    ]
    for ex in examples:
        if st.button(f"💡 {ex[:42]}...", key=ex):
            st.session_state.pending_query = ex

# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1, 10])
with col1:
    if os.path.exists(ICON_PATH):
        st.image(ICON_PATH, width=50)
with col2:
    st.title("CONSILIUM")

st.caption("Domain-trained. Agent-driven. Self-evolving. | Powered by Consilium v4.1 (Llama 3.1 8B) + RAG + Tool-based Investigation")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    avatar = "🧑‍💻" if msg["role"] == "user" else ICON_PATH if os.path.exists(ICON_PATH) else "🧠"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg.get("metadata"):
            meta = msg["metadata"]
            cols = st.columns(4)
            with cols[0]:
                st.caption(f"🎯 {meta.get('agent', '—')}")
            with cols[1]:
                st.caption(f"📁 {meta.get('category', '—')}")
            with cols[2]:
                st.caption(f"⏱️ {meta.get('time', '—')}s")
            with cols[3]:
                plan = meta.get("plan", [])
                if len(plan) > 1:
                    st.caption(f"🔗 {' → '.join(plan)}")

# Chat input — always visible at bottom
query = st.chat_input("Ask Consilium about telecom networks...")

# Handle pending query from sidebar (overrides chat input)
if "pending_query" in st.session_state:
    query = st.session_state.pop("pending_query")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(query)

    avatar = ICON_PATH if os.path.exists(ICON_PATH) else "🧠"
    with st.chat_message("assistant", avatar=avatar):
        with st.spinner("Consilium is analyzing..."):
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"query": query, "use_memory": True},
                    timeout=120,
                ).json()

                st.markdown(response["answer"])

                cols = st.columns(4)
                with cols[0]:
                    st.caption(f"🎯 {response['agent']}")
                with cols[1]:
                    st.caption(f"📁 {response['category']}")
                with cols[2]:
                    st.caption(f"⏱️ {response['elapsed_seconds']}s")
                with cols[3]:
                    if len(response.get("plan", [])) > 1:
                        st.caption(f"🔗 {' → '.join(response['plan'])}")
                    elif response.get("is_followup"):
                        st.caption("🔄 Follow-up")

                if response.get("sources"):
                    with st.expander("📚 Sources"):
                        for src in response["sources"][:5]:
                            st.code(src)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "metadata": {
                        "agent": response["agent"],
                        "category": response["category"],
                        "time": response["elapsed_seconds"],
                        "plan": response.get("plan", []),
                    },
                })

            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to Consilium API. Start both services first:\n\n"
                    "```\n"
                    "# Terminal 1: Data Service\n"
                    "uvicorn app.telecom_data_service:app --port 3003\n\n"
                    "# Terminal 2: Agent API\n"
                    "TOKENIZERS_PARALLELISM=false uvicorn app.api_server:app --port 3002\n"
                    "```"
                )
            except Exception as e:
                st.error(f"Error: {e}")
