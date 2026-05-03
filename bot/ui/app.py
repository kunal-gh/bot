"""
bot/ui/app.py — Streamlit Frontend for BOT.

Run with: streamlit run bot/ui/app.py
"""
from __future__ import annotations

import json
import os
import time

import requests
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

API_URL = os.getenv("BOT_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="BOT — Excel Analytics Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# Custom CSS — Premium Dark Theme
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ─── Base ─────────────────────────────────────────────── */
:root {
    --bg-primary: #0f1117;
    --bg-secondary: #1a1d29;
    --bg-card: #1e2235;
    --accent: #6c63ff;
    --accent-hover: #8078ff;
    --accent-light: rgba(108,99,255,0.12);
    --text-primary: #e8eaf6;
    --text-secondary: #9094a8;
    --success: #4ade80;
    --warning: #fbbf24;
    --error: #f87171;
    --border: rgba(108,99,255,0.25);
    --shadow: 0 4px 24px rgba(0,0,0,0.4);
}

/* ─── Chat bubbles ──────────────────────────────────────── */
.user-bubble {
    background: var(--accent-light);
    border: 1px solid var(--border);
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    margin: 8px 0 8px 20%;
    color: var(--text-primary);
    animation: fadeIn 0.3s ease;
}
.bot-bubble {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 18px 18px 18px 4px;
    padding: 16px 20px;
    margin: 8px 20% 8px 0;
    color: var(--text-primary);
    animation: fadeIn 0.3s ease;
    box-shadow: var(--shadow);
}
@keyframes fadeIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }

/* ─── Complexity badge ──────────────────────────────────── */
.complexity-badge {
    display: inline-block;
    background: var(--accent-light);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    color: var(--accent-hover);
    font-weight: 600;
    letter-spacing: 0.5px;
}
.repaired-badge {
    display: inline-block;
    background: rgba(251,191,36,0.12);
    border: 1px solid rgba(251,191,36,0.3);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    color: #fbbf24;
    font-weight: 600;
    margin-left: 6px;
}

/* ─── Schema pill ───────────────────────────────────────── */
.schema-pill {
    background: var(--accent-light);
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin: 2px;
    display: inline-block;
}
.sample-query-btn {
    cursor: pointer;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    margin: 4px 0;
    font-size: 0.82rem;
    color: var(--text-secondary);
    width: 100%;
    text-align: left;
    transition: all 0.2s;
}
.sample-query-btn:hover { border-color: var(--accent); color: var(--accent); }

/* ─── Traceability panel ────────────────────────────────── */
.trace-panel {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 18px;
    margin-top: 10px;
    font-size: 0.85rem;
}
.trace-label {
    font-size: 0.72rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 700;
}
.trace-value { color: var(--text-primary); }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# State helpers
# ══════════════════════════════════════════════════════════════════════════════

def _init_state():
    defaults = {
        "chat_history": [],
        "schema_data": None,
        "workbook_loaded": False,
        "pending_query": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _api(endpoint: str, method: str = "GET", **kwargs):
    """Make an API call to the backend."""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            return requests.get(url, timeout=60)
        elif method == "POST":
            return requests.post(url, timeout=120, **kwargs)
    except requests.exceptions.ConnectionError:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Sample queries (dynamic based on schema, fallback to defaults)
# ══════════════════════════════════════════════════════════════════════════════

_DEFAULT_SAMPLES = [
    "Which products had the highest revenue?",
    "What are the top 5 items by total sales?",
    "Show me revenue by category",
    "Which orders had the highest total value?",
    "What is the average order value?",
    "Show me the trend of orders over time",
    "Which products witnessed a revenue drop?",
]


def _get_sample_queries(schema_data: dict | None) -> list[str]:
    """Generate sample queries from schema, or return defaults."""
    if not schema_data or not schema_data.get("tables"):
        return _DEFAULT_SAMPLES

    tables = schema_data["tables"]
    date_tables = [t for t in tables if t.get("date_columns")]
    metric_tables = [t for t in tables if t.get("metric_columns")]
    multi_table = len(tables) >= 2

    queries = []

    if multi_table:
        t1 = tables[0]["table_name"]
        t2 = tables[1]["table_name"] if len(tables) > 1 else t1
        queries.append(f"Show me the top 10 records from {t1} joined with {t2}")

    if metric_tables:
        t = metric_tables[0]["table_name"]
        m = metric_tables[0]["metric_columns"][0] if metric_tables[0]["metric_columns"] else "total"
        queries.append(f"What is the total {m} in {t}?")
        queries.append(f"Show me the top 5 {t} by {m}")

    if date_tables:
        t = date_tables[0]["table_name"]
        queries.append(f"Show me {t} from the last 30 days")
        queries.append(f"What is the revenue trend over time in {t}?")

    queries += [
        "Which products witnessed a revenue drop?",
        "What is the average order value?",
        "Show me revenue by category",
    ]

    return queries[:7]


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

def _render_sidebar():
    with st.sidebar:
        st.markdown("## 🤖 BOT")
        st.markdown("*Universal Excel Analytics Chatbot*")
        st.divider()

        # ── Upload ──────────────────────────────────────────────
        st.markdown("### 📂 Load Workbook")
        uploaded_file = st.file_uploader(
            "Upload any Excel file (.xlsx, .xls)",
            type=["xlsx", "xls"],
            help="Each sheet becomes a queryable table",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            if st.button("🚀 Load Workbook", use_container_width=True, type="primary"):
                with st.spinner("Loading workbook into DuckDB..."):
                    resp = _api(
                        "/upload",
                        method="POST",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                    )
                if resp and resp.status_code == 200:
                    data = resp.json()
                    st.success(f"✅ {data['message']}")
                    # Show table summary
                    for tname, rcount in data.get("row_counts", {}).items():
                        st.markdown(
                            f'<span class="schema-pill">📊 {tname} ({rcount:,} rows)</span>',
                            unsafe_allow_html=True,
                        )
                    st.session_state.workbook_loaded = True
                    # Refresh schema
                    _refresh_schema()
                    st.rerun()
                else:
                    err = resp.json().get("detail", "Upload failed") if resp else "Backend not reachable"
                    st.error(f"❌ {err}")

        # Reload button
        if st.session_state.workbook_loaded:
            if st.button("🔄 Reload Data", use_container_width=True):
                with st.spinner("Reloading..."):
                    resp = _api("/reload-data", method="POST")
                if resp and resp.status_code == 200:
                    st.success("✅ Data reloaded")
                    _refresh_schema()
                    st.rerun()

        st.divider()

        # ── Schema browser ──────────────────────────────────────
        st.markdown("### 🗂️ Schema Browser")

        schema = st.session_state.schema_data
        if schema and schema.get("tables"):
            for table in schema["tables"]:
                tname = table["table_name"]
                rcount = table.get("row_count", 0)
                with st.expander(f"📋 {tname} ({rcount:,} rows)"):
                    for col in table.get("columns", []):
                        role_icon = {
                            "primary_key": "🔑",
                            "foreign_key": "🔗",
                            "date": "📅",
                            "measure": "📊",
                            "dimension": "🏷️",
                        }.get(col.get("role", ""), "•")
                        samples = col.get("sample_values", [])
                        sample_str = f" ← {', '.join(str(s) for s in samples[:2])}" if samples else ""
                        st.markdown(
                            f"`{col['name']}` {role_icon} *{col['sql_type']}*{sample_str}"
                        )
        elif st.session_state.workbook_loaded:
            st.markdown("*Refreshing schema...*")
        else:
            st.markdown("*Upload a workbook to see schema*")

        st.divider()

        # ── Sample queries ──────────────────────────────────────
        st.markdown("### 💡 Sample Queries")
        samples = _get_sample_queries(st.session_state.schema_data)

        for q in samples:
            short = q[:55] + ("…" if len(q) > 55 else "")
            if st.button(f"💬 {short}", key=f"sample_{hash(q)}", use_container_width=True):
                st.session_state.pending_query = q
                st.rerun()

        # ── Health status ───────────────────────────────────────
        st.divider()
        resp = _api("/health")
        if resp and resp.status_code == 200:
            h = resp.json()
            status = "🟢 Connected" if h.get("duckdb_connected") else "🔴 Disconnected"
            st.markdown(f"**Backend:** {status}")
            if h.get("tables_loaded", 0) > 0:
                st.markdown(f"**Tables loaded:** {h['tables_loaded']}")
        else:
            st.markdown("**Backend:** 🔴 Not reachable")
            st.caption("Start the API with: `uvicorn bot.api.main:app --reload`")


def _refresh_schema():
    """Fetch and cache the schema from the backend."""
    resp = _api("/schema")
    if resp and resp.status_code == 200:
        st.session_state.schema_data = resp.json()
        st.session_state.workbook_loaded = True


# ══════════════════════════════════════════════════════════════════════════════
# Chat message rendering
# ══════════════════════════════════════════════════════════════════════════════

def _render_message(msg: dict):
    """Render a single chat message (user or bot)."""
    role = msg["role"]

    if role == "user":
        st.markdown(
            f'<div class="user-bubble">💬 {msg["content"]}</div>',
            unsafe_allow_html=True,
        )
        return

    # Bot message
    data = msg.get("data", {})
    answer = data.get("answer", msg.get("content", ""))
    error = data.get("error")
    sql = data.get("sql", "")
    tables_used = data.get("tables_used", [])
    explanation = data.get("explanation", "")
    complexity = data.get("query_complexity", "")
    was_repaired = data.get("was_repaired", False)
    result_preview = data.get("result_preview", [])

    with st.container():
        # Answer bubble
        badge_html = f'<span class="complexity-badge">{complexity}</span>' if complexity else ""
        if was_repaired:
            badge_html += '<span class="repaired-badge">🔧 Auto-repaired</span>'

        st.markdown(
            f'<div class="bot-bubble">{badge_html}<br/><br/>{answer}</div>',
            unsafe_allow_html=True,
        )

        if error:
            st.error(f"⚠️ {error}")
            return

        # SQL preview
        if sql:
            with st.expander("🔍 View SQL Query"):
                st.code(sql, language="sql")

        # Result table
        if result_preview:
            import pandas as pd
            df = pd.DataFrame(result_preview)
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Traceability panel
        if explanation or tables_used:
            with st.expander("🔎 Traceability & Explanation"):
                if tables_used:
                    st.markdown(
                        f'<div class="trace-label">Tables Used</div>'
                        f'<div class="trace-value">{" → ".join(tables_used)}</div>',
                        unsafe_allow_html=True,
                    )
                if explanation:
                    st.markdown("---")
                    st.markdown(f'<div class="trace-label">Explanation</div>', unsafe_allow_html=True)
                    st.markdown(explanation)
                if complexity:
                    st.markdown("---")
                    st.markdown(
                        f'<div class="trace-label">Complexity</div>'
                        f'<div class="trace-value">{complexity}</div>',
                        unsafe_allow_html=True,
                    )


# ══════════════════════════════════════════════════════════════════════════════
# Main chat area
# ══════════════════════════════════════════════════════════════════════════════

def _render_main():
    st.markdown("# 🤖 BOT — Excel Analytics Chatbot")
    st.markdown(
        "_Ask questions in plain English about your data. "
        "BOT will join tables, compute metrics, and explain how it got there._"
    )
    st.divider()

    # No workbook warning
    if not st.session_state.workbook_loaded:
        st.info(
            "👈 **Upload an Excel workbook** in the sidebar to get started.\n\n"
            "BOT will automatically detect tables, relationships, and available metrics."
        )

    # Render chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            _render_message(msg)

    st.divider()

    # Chat input
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([10, 1])
        with col1:
            # Pre-fill from sample query click
            default_val = st.session_state.pop("pending_query", None) or ""
            user_input = st.text_input(
                "Ask a question about your data…",
                value=default_val,
                placeholder="e.g. Which products had the highest revenue last week?",
                label_visibility="collapsed",
            )
        with col2:
            submitted = st.form_submit_button("▶", use_container_width=True)

    if submitted and user_input.strip():
        _handle_query(user_input.strip())


def _handle_query(query: str):
    """Send query to API and update chat history."""
    if not st.session_state.workbook_loaded:
        st.warning("Please upload a workbook first.")
        return

    # Add user message
    st.session_state.chat_history.append({"role": "user", "content": query})

    # Call API with spinner
    with st.spinner("🧠 Thinking…"):
        resp = _api(
            "/chat",
            method="POST",
            json={"session_id": "streamlit", "message": query},
        )

    if resp is None:
        st.session_state.chat_history.append({
            "role": "bot",
            "content": "❌ Backend not reachable. Is the API running?",
            "data": {"error": "Backend connection failed"},
        })
    elif resp.status_code == 200:
        data = resp.json()
        st.session_state.chat_history.append({
            "role": "bot",
            "content": data.get("answer", ""),
            "data": data,
        })
    else:
        try:
            err = resp.json().get("detail", resp.text)
        except Exception:
            err = resp.text
        st.session_state.chat_history.append({
            "role": "bot",
            "content": f"❌ Error: {err}",
            "data": {"error": err},
        })

    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    _init_state()
    # Attempt to load schema on first run
    if st.session_state.schema_data is None:
        _refresh_schema()

    _render_sidebar()
    _render_main()


if __name__ == "__main__":
    main()
else:
    main()
