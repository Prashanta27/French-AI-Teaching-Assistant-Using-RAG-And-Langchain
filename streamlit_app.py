import re
import html as html_lib
from datetime import datetime

import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FrenchAI",
    page_icon="🇫🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000"

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Perplexity-exact architecture
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Tokens ── */
:root {
    --sidebar-w:      240px;
    --max-w:          780px;
    --font:           'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

    --bg:             #FFFFFF;
    --bg-sidebar:     #F7F7F8;
    --bg-hover:       #EBEBED;
    --bg-active:      #E4E4E8;
    --bg-input:       #F4F4F6;
    --bg-chip:        #F0F0F3;
    --bg-user-msg:    #F0F0F3;

    --border:         #E2E2E6;
    --border-focus:   #ADADB8;

    --text:           #111111;
    --text-2:         #555560;
    --text-3:         #9999A8;
    --text-inv:       #FFFFFF;

    --accent:         #1B6CF2;
    --accent-h:       #1558D6;
    --new-btn-bg:     #FFFFFF;
    --new-btn-border: #DADADF;

    --danger:         #D93025;
    --pin-color:      #E69820;
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg:             #111113;
        --bg-sidebar:     #171719;
        --bg-hover:       #222226;
        --bg-active:      #2B2B30;
        --bg-input:       #1E1E22;
        --bg-chip:        #252529;
        --bg-user-msg:    #252529;

        --border:         #2C2C32;
        --border-focus:   #55555F;

        --text:           #EEEEEE;
        --text-2:         #AAAABC;
        --text-3:         #66667A;
        --text-inv:       #FFFFFF;

        --accent:         #4D8EFF;
        --accent-h:       #3A7AEE;
        --new-btn-bg:     #1E1E22;
        --new-btn-border: #2C2C32;

        --danger:         #E55;
        --pin-color:      #F0A830;
    }
}

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
    font-family: var(--font) !important;
    font-size: 16px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}
html, body { overflow-x: hidden; background: var(--bg) !important; }
.stApp, [data-testid="stAppViewContainer"] { background: var(--bg) !important; }

/* ── Hide streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton { display: none !important; visibility: hidden !important; }

/* ── Block container — centered chat ── */
.block-container {
    max-width: var(--max-w) !important;
    margin: 0 auto !important;
    padding: 24px 20px 180px 20px !important;
}
@media (max-width: 768px) {
    .block-container { padding: 18px 14px 170px 14px !important; }
}
@media (max-width: 480px) {
    .block-container { padding: 14px 10px 165px 10px !important; }
}

/* ── Sidebar — Perplexity exact ── */
section[data-testid="stSidebar"] {
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border) !important;
    width: var(--sidebar-w) !important;
    min-width: var(--sidebar-w) !important;
    padding: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
    gap: 0 !important;
}
/* kill default Streamlit widget spacing in sidebar */
section[data-testid="stSidebar"] .element-container,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stButton {
    margin: 0 !important;
    padding: 0 !important;
}

/* ── Sidebar top logo bar ── */
.sb-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 14px 12px;
    border-bottom: 1px solid var(--border);
}
.sb-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 700;
    color: var(--text) !important;
    letter-spacing: -0.3px;
}
.sb-brand-icon {
    width: 28px; height: 28px;
    border-radius: 7px;
    background: var(--accent);
    color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px;
}
.sb-collapse-btn {
    width: 28px; height: 28px;
    border-radius: 7px;
    background: transparent;
    border: 1px solid var(--border);
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    color: var(--text-2);
    font-size: 13px;
    transition: background 0.15s;
}
.sb-collapse-btn:hover { background: var(--bg-hover); }

/* ── New Thread button ── */
.sb-new-btn-wrap {
    padding: 12px 10px 8px;
}
.sb-new-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 9px 13px;
    background: var(--new-btn-bg);
    border: 1px solid var(--new-btn-border);
    border-radius: 10px;
    font-family: var(--font);
    font-size: 13.5px;
    font-weight: 500;
    color: var(--text);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    text-align: left;
}
.sb-new-btn:hover {
    background: var(--bg-hover);
    border-color: var(--border-focus);
}
.sb-new-btn .kbd {
    margin-left: auto;
    font-size: 10px;
    color: var(--text-3);
    background: var(--bg-chip);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 1px 5px;
    font-family: var(--font);
}

/* ── Sidebar nav links (Home, Discover, Library) ── */
.sb-nav {
    padding: 4px 6px 0;
}
.sb-nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-radius: 9px;
    font-size: 13.5px;
    color: var(--text-2);
    cursor: pointer;
    transition: background 0.12s, color 0.12s;
    border: 1px solid transparent;
}
.sb-nav-item:hover { background: var(--bg-hover); color: var(--text); }
.sb-nav-item.active { background: var(--bg-active); color: var(--text); font-weight: 500; }
.sb-nav-icon { font-size: 14px; width: 18px; text-align: center; }

/* ── Chat history section ── */
.sb-section-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-3);
    text-transform: uppercase;
    letter-spacing: 0.7px;
    padding: 16px 16px 6px;
}

/* History item */
.sb-hist-item {
    display: flex;
    align-items: center;
    gap: 0;
    padding: 0 6px;
    margin-bottom: 1px;
    position: relative;
}
.sb-hist-text {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-radius: 9px;
    font-size: 13px;
    color: var(--text-2);
    cursor: pointer;
    transition: background 0.12s, color 0.12s;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    border: 1px solid transparent;
    min-width: 0;
}
.sb-hist-text:hover { background: var(--bg-hover); color: var(--text); }
.sb-hist-text.active {
    background: var(--bg-active);
    color: var(--text);
    font-weight: 500;
    border-color: var(--border);
}
.sb-hist-pin { color: var(--pin-color); font-size: 11px; flex-shrink: 0; }
.sb-hist-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
}

/* action buttons per history item */
.sb-hist-actions {
    display: flex;
    gap: 2px;
    opacity: 0;
    transition: opacity 0.15s;
    flex-shrink: 0;
}
.sb-hist-item:hover .sb-hist-actions { opacity: 1; }
.sb-act-btn {
    width: 26px; height: 26px;
    border-radius: 7px;
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px;
    color: var(--text-3);
    transition: background 0.12s, color 0.12s, border-color 0.12s;
    flex-shrink: 0;
}
.sb-act-btn:hover { background: var(--bg-hover); border-color: var(--border); color: var(--text); }
.sb-act-btn.danger:hover { background: #FEE; border-color: #FCC; color: var(--danger); }
.sb-act-btn.pin-active { color: var(--pin-color); }

/* ── Main topbar ── */
.main-topbar {
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 11px 0 11px;
    margin: -24px -20px 28px;
}
@media (max-width: 768px) {
    .main-topbar { margin: -18px -14px 22px; }
}
.main-topbar-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-2);
    padding: 0 20px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 500px;
}
.main-topbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 0 14px;
    flex-shrink: 0;
}
.topbar-btn {
    display: flex; align-items: center; gap: 5px;
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: transparent;
    font-family: var(--font);
    font-size: 12.5px;
    color: var(--text-2);
    cursor: pointer;
    transition: all 0.15s;
}
.topbar-btn:hover { background: var(--bg-hover); color: var(--text); border-color: var(--border-focus); }

/* ── Empty state ── */
.empty-wrap {
    text-align: center;
    padding: 70px 20px 20px;
    animation: fadeUp 0.35s ease both;
}
.empty-icon { font-size: 44px; display: block; margin-bottom: 18px; }
.empty-title {
    font-size: 26px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.5px;
    margin-bottom: 10px;
}
.empty-sub {
    font-size: 15.5px;
    color: var(--text-2);
    line-height: 1.65;
    max-width: 440px;
    margin: 0 auto 32px;
}
/* Starter grid */
.starter-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    max-width: 540px;
    margin: 0 auto;
}
@media (max-width: 480px) {
    .starter-grid { grid-template-columns: 1fr; }
}

/* ── Streamlit button base override (main area) ── */
.stButton > button {
    font-family: var(--font) !important;
    border-radius: 10px !important;
    font-size: 13.5px !important;
    font-weight: 400 !important;
    transition: all 0.15s !important;
    box-shadow: none !important;
}

/* Starter chip buttons */
div[data-testid="column"] .stButton > button,
.starter-btn .stButton > button {
    background: var(--bg-chip) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-2) !important;
    text-align: left !important;
    padding: 11px 15px !important;
    width: 100% !important;
    display: block !important;
    line-height: 1.45 !important;
}
div[data-testid="column"] .stButton > button:hover {
    background: var(--bg-hover) !important;
    border-color: var(--border-focus) !important;
    color: var(--text) !important;
    transform: none !important;
}

/* Clear button in topbar */
.clear-wrap .stButton > button {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--text-2) !important;
    padding: 6px 14px !important;
    font-size: 12.5px !important;
}
.clear-wrap .stButton > button:hover {
    background: var(--bg-hover) !important;
    color: var(--text) !important;
    border-color: var(--border-focus) !important;
}

/* Sidebar buttons — override */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: var(--text-2) !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    text-align: left !important;
    padding: 7px 10px !important;
    border-radius: 9px !important;
    width: 100% !important;
    box-shadow: none !important;
    display: block !important;
    justify-content: flex-start !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-hover) !important;
    color: var(--text) !important;
    transform: none !important;
}
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: var(--bg-active) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-weight: 600 !important;
}

/* ── Messages ── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

.msg-block {
    margin-bottom: 28px;
    animation: fadeUp 0.28s ease both;
}

/* User message */
.user-msg-wrap {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 24px;
    animation: fadeUp 0.25s ease both;
}
.user-bubble {
    max-width: 72%;
    background: var(--bg-user-msg);
    border: 1px solid var(--border);
    border-radius: 18px 18px 4px 18px;
    padding: 12px 17px;
    font-size: 15.5px;
    line-height: 1.65;
    color: var(--text);
    word-break: break-word;
    white-space: pre-wrap;
}
@media (max-width: 640px) {
    .user-bubble { max-width: 86%; font-size: 15px; }
}

/* Assistant message */
.ai-msg-wrap {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 6px;
    animation: fadeUp 0.28s ease both;
}
.ai-avatar {
    width: 30px; height: 30px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
    margin-top: 3px;
}
.ai-body {
    flex: 1;
    min-width: 0;
}
.ai-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-2);
    margin-bottom: 6px;
}
.ai-text {
    font-size: 15.5px;
    line-height: 1.72;
    color: var(--text);
    word-break: break-word;
    white-space: pre-wrap;
}
@media (max-width: 640px) {
    .ai-text { font-size: 15px; }
}

/* AI message action row */
.ai-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 12px;
    padding-left: 42px;
}
.ai-act {
    display: flex; align-items: center; gap: 5px;
    padding: 5px 10px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: transparent;
    font-size: 12px;
    color: var(--text-3);
    cursor: pointer;
    transition: all 0.13s;
}
.ai-act:hover { background: var(--bg-hover); color: var(--text-2); border-color: var(--border-focus); }

/* msg timestamp */
.msg-time {
    font-size: 11px;
    color: var(--text-3);
    padding-left: 42px;
    margin-top: 4px;
    margin-bottom: 8px;
}
.msg-time-user {
    font-size: 11px;
    color: var(--text-3);
    text-align: right;
    margin-top: 4px;
    margin-bottom: 8px;
}

/* Typing indicator */
.typing-wrap {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 18px;
    animation: fadeUp 0.2s ease both;
}
.typing-bubble {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 13px 18px;
    background: var(--bg-user-msg);
    border: 1px solid var(--border);
    border-radius: 18px;
    margin-top: 3px;
}
.t-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--text-3);
    animation: tBounce 1.3s infinite ease-in-out;
}
.t-dot:nth-child(2) { animation-delay: 0.18s; }
.t-dot:nth-child(3) { animation-delay: 0.36s; }
@keyframes tBounce {
    0%, 70%, 100% { transform: translateY(0); opacity: 0.4; }
    35% { transform: translateY(-5px); opacity: 1; }
}

/* ── Separator between Q/A pairs ── */
.msg-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 28px 0;
    opacity: 0.6;
}

/* ── Fixed bottom input ── */
[data-testid="stChatInput"] {
    background: var(--bg) !important;
    border-top: 1px solid var(--border) !important;
    padding: 10px 0 12px !important;
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 200 !important;
}
[data-testid="stChatInput"] > div {
    max-width: calc(var(--max-w) + 40px) !important;
    margin: 0 auto !important;
    padding: 0 20px !important;
}
[data-testid="stChatInput"] textarea {
    background: var(--bg-input) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 22px !important;
    font-family: var(--font) !important;
    font-size: 15.5px !important;
    padding: 13px 20px !important;
    line-height: 1.55 !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--border-focus) !important;
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent) !important;
    outline: none !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-3) !important;
    font-size: 15px !important;
}
[data-testid="stChatInput"] button {
    background: var(--accent) !important;
    border-radius: 50% !important;
    transition: background 0.15s !important;
}
[data-testid="stChatInput"] button:hover {
    background: var(--accent-h) !important;
}
[data-testid="stChatInput"] svg {
    color: #fff !important;
    fill: #fff !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-3); }

/* ── Responsive sidebar ── */
@media (max-width: 640px) {
    section[data-testid="stSidebar"] { display: none !important; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
def _init():
    if "sessions" not in st.session_state:
        st.session_state.sessions = {
            "s1": {"name": "New thread", "named": False, "pinned": False, "messages": []},
        }
    if "active" not in st.session_state:
        st.session_state.active = "s1"
    if "pending" not in st.session_state:
        st.session_state.pending = None
    if "delete_confirm" not in st.session_state:
        st.session_state.delete_confirm = None

_init()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def sess():
    return st.session_state.sessions[st.session_state.active]

def msgs():
    return sess()["messages"]

def add_message(role, content):
    msgs().append({"role": role, "content": content, "time": datetime.now().strftime("%H:%M")})

def auto_name(prompt):
    s = sess()
    if not s["named"]:
        title = prompt.strip().replace("\n", " ")
        s["name"] = (title[:34] + "…") if len(title) > 34 else title
        s["named"] = True

def new_session():
    import time
    sid = f"s_{int(time.time()*1000)}"
    st.session_state.sessions[sid] = {
        "name": "New thread", "named": False, "pinned": False, "messages": []
    }
    st.session_state.active = sid

def call_api(question):
    try:
        r = requests.post(f"{API_BASE}/chat", json={"question": question}, timeout=300)
        if r.status_code == 200:
            return r.json().get("answer", "No answer returned."), True
        return f"API error {r.status_code}: {r.text}", False
    except requests.exceptions.ConnectionError:
        return (
            "⚠️ Could not reach the backend.\n\n"
            "Start it with:\n```\nuvicorn main:app --reload\n```", False
        )
    except Exception as e:
        return f"Unexpected error: {e}", False

def fmt(text):
    t = html_lib.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code style='background:var(--bg-chip);padding:2px 6px;border-radius:5px;font-size:0.9em;'>\1</code>", t)
    t = t.replace("\n", "<br>")
    return t

def autoscroll():
    st.markdown("""
    <script>
    setTimeout(function(){
        try {
            var m = window.parent.document.querySelector('section.main');
            if (m) m.scrollTop = m.scrollHeight;
        } catch(e){}
    }, 100);
    </script>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Perplexity layout
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── Brand topbar ──
    st.markdown("""
    <div class="sb-topbar">
        <div class="sb-brand">
            <div class="sb-brand-icon">🇫🇷</div>
            FrenchAI
        </div>
    </div>""", unsafe_allow_html=True)

    # ── New Thread button ──
    st.markdown('<div class="sb-new-btn-wrap">', unsafe_allow_html=True)
    if st.button("＋  New Thread", key="new_thread_btn", use_container_width=True):
        new_session()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Nav links ──
    st.markdown("""
    <div class="sb-nav">
        <div class="sb-nav-item active">
            <span class="sb-nav-icon">🏠</span> Home
        </div>
        <div class="sb-nav-item">
            <span class="sb-nav-icon">🔍</span> Discover
        </div>
        <div class="sb-nav-item">
            <span class="sb-nav-icon">📚</span> Library
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Chat history ──
    all_sessions = list(st.session_state.sessions.items())

    # Pinned first, then reverse chronological
    pinned   = [(sid, s) for sid, s in all_sessions if s.get("pinned")]
    unpinned = [(sid, s) for sid, s in reversed(all_sessions) if not s.get("pinned")]

    def render_history_group(label, items):
        if not items:
            return
        st.markdown(f'<div class="sb-section-label">{label}</div>', unsafe_allow_html=True)
        for sid, s in items:
            is_active = sid == st.session_state.active
            pin_icon  = "📌" if s.get("pinned") else ""
            name      = s["name"]
            active_cls = "active" if is_active else ""

            # Confirm-delete state
            if st.session_state.delete_confirm == sid:
                col_y, col_n = st.columns([1,1])
                with col_y:
                    if st.button("🗑 Yes", key=f"del_yes_{sid}", use_container_width=True):
                        if st.session_state.active == sid:
                            remaining = [k for k in st.session_state.sessions if k != sid]
                            st.session_state.active = remaining[-1] if remaining else new_session() or st.session_state.active
                        del st.session_state.sessions[sid]
                        st.session_state.delete_confirm = None
                        st.rerun()
                with col_n:
                    if st.button("✕ No", key=f"del_no_{sid}", use_container_width=True):
                        st.session_state.delete_confirm = None
                        st.rerun()
                continue

            # Normal item row: select | pin | delete
            c_name, c_pin, c_del = st.columns([7, 1, 1])

            with c_name:
                label_text = f"{pin_icon} {name}" if pin_icon else name
                btn_type = "primary" if is_active else "secondary"
                if st.button(label_text, key=f"sel_{sid}", use_container_width=True, type=btn_type):
                    st.session_state.active = sid
                    st.session_state.delete_confirm = None
                    st.rerun()

            with c_pin:
                pin_tip = "📌" if not s.get("pinned") else "📍"
                if st.button(pin_tip, key=f"pin_{sid}", help="Pin / Unpin", use_container_width=True):
                    st.session_state.sessions[sid]["pinned"] = not s.get("pinned", False)
                    st.rerun()

            with c_del:
                if st.button("🗑", key=f"del_{sid}", help="Delete", use_container_width=True):
                    st.session_state.delete_confirm = sid
                    st.rerun()

    render_history_group("📌 Pinned", pinned)
    render_history_group("🕘 Recent", unpinned)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────
current_msgs = msgs()
session_name = sess()["name"]

# ── Topbar ──
top_left, top_right = st.columns([8, 2])
with top_left:
    st.markdown(
        f'<div style="padding:11px 0 11px;font-size:14px;font-weight:600;color:var(--text-2);">'
        f'{session_name}</div>',
        unsafe_allow_html=True,
    )
with top_right:
    if current_msgs:
        st.markdown('<div class="clear-wrap">', unsafe_allow_html=True)
        if st.button("Clear chat", key="clear_main"):
            sess()["messages"] = []
            sess()["named"] = False
            sess()["name"] = "New thread"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    '<hr style="border:none;border-top:1px solid var(--border);margin:0 0 28px;">',
    unsafe_allow_html=True,
)

# ── Empty state ──
STARTERS = [
    "How do I say 'I would like...' in French?",
    "Explain the difference between être and avoir",
    "How do I order food at a French restaurant?",
    "What are common French greetings?",
    "Teach me how to count to 20 in French",
    "How do I ask for directions in French?",
]

if not current_msgs:
    st.markdown("""
    <div class="empty-wrap">
        <span class="empty-icon">🇫🇷</span>
        <div class="empty-title">Bonjour ! How can I help?</div>
        <div class="empty-sub">Your personal French tutor — ask about grammar, vocabulary, pronunciation, or culture.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    for i, prompt in enumerate(STARTERS):
        with (col1 if i % 2 == 0 else col2):
            if st.button(prompt, key=f"starter_{i}", use_container_width=True):
                st.session_state.pending = prompt
                st.rerun()

else:
    # ── Render message pairs ──
    for idx, m in enumerate(current_msgs):
        is_user = m["role"] == "user"

        if is_user:
            # Divider between Q/A pairs (not before first message)
            if idx > 0:
                st.markdown('<hr class="msg-divider">', unsafe_allow_html=True)

            st.markdown(f"""
            <div class="user-msg-wrap">
                <div class="user-bubble">{fmt(m['content'])}</div>
            </div>
            <div class="msg-time-user">{m['time']}</div>
            """, unsafe_allow_html=True)

        else:
            st.markdown(f"""
            <div class="ai-msg-wrap">
                <div class="ai-avatar">🇫🇷</div>
                <div class="ai-body">
                    <div class="ai-name">FrenchAI</div>
                    <div class="ai-text">{fmt(m['content'])}</div>
                </div>
            </div>
            <div class="msg-time">{m['time']}</div>
            <div class="ai-actions">
                <button class="ai-act">↻ Rewrite</button>
                <button class="ai-act">⎘ Copy</button>
            </div>
            """, unsafe_allow_html=True)


# ── Chat input ──
prompt = st.chat_input("Ask a follow-up…" if current_msgs else "Ask anything about French…")

# ── Handle pending starter clicks ──
if st.session_state.pending:
    prompt = st.session_state.pending
    st.session_state.pending = None

if prompt and prompt.strip():
    q = prompt.strip()
    add_message("user", q)
    auto_name(q)

    # Rerender with user bubble + typing indicator
    st.rerun()

# ── If last message is from user → call API ──
if current_msgs and current_msgs[-1]["role"] == "user":
    last_q = current_msgs[-1]["content"]

    # Show typing indicator while calling
    st.markdown("""
    <div class="typing-wrap">
        <div class="ai-avatar">🇫🇷</div>
        <div class="typing-bubble">
            <div class="t-dot"></div>
            <div class="t-dot"></div>
            <div class="t-dot"></div>
        </div>
    </div>""", unsafe_allow_html=True)

    autoscroll()

    answer, _ = call_api(last_q)
    add_message("assistant", answer)
    st.rerun()

autoscroll()