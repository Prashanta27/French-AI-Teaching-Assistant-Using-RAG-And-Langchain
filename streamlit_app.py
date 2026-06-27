import re
import html as html_lib
from datetime import datetime

import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FrenchAI",
    page_icon="🇫🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000"

# ─────────────────────────────────────────────────────────────────────────
# Styling — light & dark mode, ChatGPT / Perplexity inspired
# ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Color tokens — light mode (default) ── */
:root {
    --bg-primary:    #FFFFFF;
    --bg-secondary:  #F7F7F8;
    --bg-tertiary:   #ECECF1;
    --bg-hover:      #F0F0F2;
    --border:        #E4E4E8;
    --text-primary:  #0D0D0D;
    --text-secondary:#6E6E80;
    --accent:        #2F6FED;
    --accent-text:   #FFFFFF;
    --bubble-user-bg:#2F6FED;
    --bubble-user-tx:#FFFFFF;
    --bubble-ai-bg:  #F1F1F3;
    --bubble-ai-tx:  #0D0D0D;
    --shadow:        rgba(0,0,0,0.04);
}

/* ── Color tokens — dark mode ── */
@media (prefers-color-scheme: dark) {
    :root {
        --bg-primary:    #111113;
        --bg-secondary:  #1A1A1D;
        --bg-tertiary:   #232327;
        --bg-hover:      #26262B;
        --border:        #2E2E33;
        --text-primary:  #ECECEC;
        --text-secondary:#9B9BA8;
        --accent:        #5B8DEF;
        --accent-text:   #FFFFFF;
        --bubble-user-bg:#2F5FCB;
        --bubble-user-tx:#FFFFFF;
        --bubble-ai-bg:  #232327;
        --bubble-ai-tx:  #ECECEC;
        --shadow:        rgba(0,0,0,0.25);
    }
}

/* ── Reset & base type ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text-primary);
}
html, body { overflow-x: hidden; scroll-behavior: smooth; }

#MainMenu, footer, header { visibility: hidden; }

.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background: var(--bg-primary) !important;
}

/* Centered, max-width chat column */
.block-container {
    max-width: 900px !important;
    margin: 0 auto !important;
    padding: 28px 24px 150px 24px !important;
}

@media (max-width: 1024px) {
    .block-container { padding: 22px 18px 145px 18px !important; }
}
@media (max-width: 640px) {
    .block-container { padding: 16px 12px 135px 12px !important; }
}

@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
    width: 280px !important;
}
section[data-testid="stSidebar"] * { color: var(--text-primary); }

.sidebar-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 18px 18px 14px;
    font-size: 17px;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
    margin-bottom: 12px;
}
.sidebar-logo .flag { font-size: 20px; }

.sidebar-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    letter-spacing: 0.6px;
    text-transform: uppercase;
    padding: 4px 18px 8px;
}

section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: var(--text-primary) !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    text-align: left !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 9px 12px !important;
    box-shadow: none !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
    justify-content: flex-start !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-hover) !important;
    transform: none !important;
    box-shadow: none !important;
}
/* Active conversation (rendered as a primary-type button).
   Different Streamlit versions expose this state via different
   attributes, so we cover the common ones. */
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: rgba(47,111,237,0.12) !important;
    color: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    font-weight: 600 !important;
}
/* ── Generic button reset for main area (kept minimal — chat_input has its own send button) ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: background 0.15s ease, transform 0.1s ease !important;
}

/* ── Top header (current conversation title) ── */
.chat-topbar {
    text-align: center;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-secondary);
    padding-bottom: 18px;
    margin-bottom: 6px;
    border-bottom: 1px solid var(--border);
}

/* ── Messages ── */
.msg-row {
    display: flex;
    gap: 12px;
    margin-bottom: 22px;
    animation: fadeIn 0.35s ease both;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

.msg-row.user { flex-direction: row-reverse; }

.avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    margin-top: 2px;
}
.avatar.assistant { background: var(--accent); color: var(--accent-text); }
.avatar.user { background: var(--bg-tertiary); }

.bubble {
    max-width: 78%;
    border-radius: 18px;
    padding: 13px 17px;
    font-size: 16px;
    line-height: 1.65;
    word-wrap: break-word;
    box-shadow: 0 1px 2px var(--shadow);
}
.bubble.assistant {
    background: var(--bubble-ai-bg);
    color: var(--bubble-ai-tx);
    border-top-left-radius: 4px;
}
.bubble.user {
    background: var(--bubble-user-bg);
    color: var(--bubble-user-tx);
    border-top-right-radius: 4px;
}

@media (max-width: 640px) {
    .bubble { max-width: 88%; font-size: 15.5px; padding: 11px 14px; }
    .avatar { width: 28px; height: 28px; font-size: 13px; }
}

/* Typing indicator */
.typing-dots { display: flex; align-items: center; gap: 4px; padding: 4px 2px; }
.typing-dots span {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--text-secondary);
    animation: bounce 1.2s infinite ease-in-out;
}
.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
}

/* Empty state */
.empty-state { text-align: center; padding: 90px 20px 20px; color: var(--text-secondary); }
.empty-state-emoji { font-size: 42px; margin-bottom: 14px; }
.empty-state-title { font-size: 22px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.empty-state-sub { font-size: 15px; line-height: 1.6; }

/* ── Chat input (native st.chat_input) ── */
[data-testid="stChatInput"] {
    background: var(--bg-primary) !important;
    border-top: 1px solid var(--border) !important;
    padding-top: 10px !important;
}
[data-testid="stChatInput"] textarea {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 22px !important;
    font-size: 16px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 13px 18px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(47,111,237,0.18) !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--text-secondary) !important; }
[data-testid="stChatInput"] button {
    background: var(--accent) !important;
    border-radius: 50% !important;
}
[data-testid="stChatInput"] svg { color: var(--accent-text) !important; fill: var(--accent-text) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-secondary); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "sessions": {
            "session_1": {
                "id": "session_1",
                "name": "New chat",
                "named": False,
                "messages": [],
            }
        },
        "active_session": "session_1",
        "pending_prompt": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────
def active_session():
    return st.session_state.sessions[st.session_state.active_session]


def active_messages():
    return active_session()["messages"]


def add_message(role, content):
    active_messages().append({
        "role": role,
        "content": content,
        "time": datetime.now().strftime("%H:%M"),
    })


def new_session():
    n = len(st.session_state.sessions) + 1
    sid = f"session_{n}"
    while sid in st.session_state.sessions:
        n += 1
        sid = f"session_{n}"
    st.session_state.sessions[sid] = {
        "id": sid,
        "name": "New chat",
        "named": False,
        "messages": [],
    }
    st.session_state.active_session = sid


def maybe_name_session(prompt: str):
    sess = active_session()
    if not sess["named"]:
        title = prompt.strip().replace("\n", " ")
        sess["name"] = (title[:32] + "…") if len(title) > 32 else title
        sess["named"] = True


def call_api(question: str):
    """POST to FastAPI /chat endpoint."""
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            json={"question": question},
            timeout=180,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("answer", "No answer returned."), True
        else:
            return f"API error {resp.status_code}: {resp.text}", False
    except requests.exceptions.ConnectionError:
        return (
            "⚠️ Could not reach the FastAPI server at `localhost:8000`.\n\n"
            "Make sure you've run:\n```\nuvicorn main:app --reload\n```",
            False,
        )
    except Exception as e:
        return f"Unexpected error: {str(e)}", False


def format_content(text: str) -> str:
    """Escape HTML, then apply minimal markdown-style formatting safely."""
    escaped = html_lib.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = escaped.replace("\n", "<br>")
    return escaped


def render_message(msg):
    side = "user" if msg["role"] == "user" else "assistant"
    avatar = "🙂" if side == "user" else "🇫🇷"
    st.markdown(f"""
    <div class="msg-row {side}">
        <div class="avatar {side}">{avatar}</div>
        <div class="bubble {side}">{format_content(msg['content'])}</div>
    </div>
    """, unsafe_allow_html=True)


def render_typing_indicator():
    st.markdown("""
    <div class="msg-row assistant">
        <div class="avatar assistant">🇫🇷</div>
        <div class="bubble assistant">
            <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def autoscroll():
    st.markdown("""
    <script>
        setTimeout(function() {
            try {
                var main = window.parent.document.querySelector('section.main');
                if (main) { main.scrollTop = main.scrollHeight; }
            } catch (e) {}
        }, 80);
    </script>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────
# Sidebar — conversation history
# ─────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo"><span class="flag">🇫🇷</span> FrenchAI</div>',
        unsafe_allow_html=True,
    )

    if st.button("＋  New chat", use_container_width=True, key="new_chat_btn", type="primary"):
        new_session()
        st.rerun()

    st.markdown('<div class="sidebar-label">Conversations</div>', unsafe_allow_html=True)

    for sid, sess in st.session_state.sessions.items():
        is_active = sid == st.session_state.active_session
        if st.button(
            sess["name"],
            key=f"sess_{sid}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.active_session = sid
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# Main chat area
# ─────────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="chat-topbar">{active_session()["name"]}</div>',
    unsafe_allow_html=True,
)

msgs = active_messages()

if not msgs:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-emoji">🇫🇷</div>
        <div class="empty-state-title">Bonjour ! Ready to learn?</div>
        <div class="empty-state-sub">Ask anything about French — grammar, vocabulary,<br>pronunciation, or culture.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in msgs:
        render_message(msg)

prompt = st.chat_input("Message FrenchAI…")

if prompt and prompt.strip():
    add_message("user", prompt.strip())
    maybe_name_session(prompt.strip())

    # Show the new user bubble + a typing indicator immediately, before the
    # (potentially slow) backend call, for a smooth, responsive feel.
    render_message(active_messages()[-1])
    typing_placeholder = st.empty()
    with typing_placeholder.container():
        render_typing_indicator()
    autoscroll()

    answer, _ = call_api(prompt.strip())

    typing_placeholder.empty()
    add_message("assistant", answer)
    st.rerun()

autoscroll()