import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "frenchai_sessions_v1";

function makeSession() {
  return {
    id: `s_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    name: "New thread",
    named: false,
    pinned: false,
    messages: [],
  };
}

function loadInitial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.sessions?.length) return parsed;
    }
  } catch {
    // fall through to fresh state
  }
  const first = makeSession();
  return { sessions: [first], active: first.id };
}

export function useSessions() {
  const [state, setState] = useState(loadInitial);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  const active = state.sessions.find((s) => s.id === state.active) || state.sessions[0];

  const setActive = useCallback((id) => {
    setState((s) => ({ ...s, active: id }));
  }, []);

  const newSession = useCallback(() => {
    const s = makeSession();
    setState((prev) => ({
      sessions: [...prev.sessions, s],
      active: s.id,
    }));
  }, []);

  const deleteSession = useCallback((id) => {
    setState((prev) => {
      const remaining = prev.sessions.filter((s) => s.id !== id);
      if (remaining.length === 0) {
        const fresh = makeSession();
        return { sessions: [fresh], active: fresh.id };
      }
      const active = prev.active === id ? remaining[remaining.length - 1].id : prev.active;
      return { sessions: remaining, active };
    });
  }, []);

  const togglePin = useCallback((id) => {
    setState((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s) => (s.id === id ? { ...s, pinned: !s.pinned } : s)),
    }));
  }, []);

  const clearActive = useCallback(() => {
    setState((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s) =>
        s.id === prev.active ? { ...s, messages: [], named: false, name: "New thread" } : s
      ),
    }));
  }, []);

  const addMessage = useCallback((role, content) => {
    setState((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s) => {
        if (s.id !== prev.active) return s;
        const messages = [
          ...s.messages,
          { role, content, time: new Date().toTimeString().slice(0, 5) },
        ];
        // Auto-name the thread from the first user message, same as
        // the Streamlit version did.
        const shouldName = role === "user" && !s.named;
        const name = shouldName
          ? content.trim().length > 34
            ? content.trim().slice(0, 34) + "…"
            : content.trim()
          : s.name;
        return { ...s, messages, named: s.named || shouldName, name };
      }),
    }));
  }, []);

  return {
    sessions: state.sessions,
    active,
    setActive,
    newSession,
    deleteSession,
    togglePin,
    clearActive,
    addMessage,
  };
}
