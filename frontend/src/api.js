// Base URL of your FastAPI backend. Override at build time with a
// .env file (VITE_API_BASE=http://localhost:8000) if you deploy the
// frontend and backend separately.
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * Calls the FastAPI /ask endpoint with the same contract the
 * Streamlit app used: POST { question } -> { answer }.
 * Returns { answer, ok } so the caller can render an error bubble
 * without throwing.
 */
export async function askQuestion(question, { signal } = {}) {
  try {
    const res = await fetch(`${API_BASE}/ask`, { 
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });

    if (!res.ok) {
      const text = await res.text();
      return { answer: `API error ${res.status}: ${text}`, ok: false };
    }

    const data = await res.json();
    return { answer: data.answer ?? "No answer returned.", ok: true };
  } catch (err) {
    if (err.name === "AbortError") {
      return { answer: "Request cancelled.", ok: false };
    }
    return {
      answer:
        "⚠️ Could not reach the backend.\n\n" +
        "Start it with:\nuvicorn api:app --reload",
      ok: false,
    };
  }
}