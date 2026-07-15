// Base URL of your FastAPI backend. Override at build time with a
// .env file (VITE_API_BASE=http://localhost:8000) if you deploy the
// frontend and backend separately.
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * Calls the FastAPI /ask endpoint with the same contract the
 * Streamlit app used: POST { question } -> { answer }.
 * Returns { answer, ok } so the caller can render an error bubble
 * without throwing.
 *
 * Kept around (not removed) for anything that still wants the
 * "wait for the whole answer" behavior -- e.g. a future non-chat
 * feature, or as a manual fallback if streaming is ever disabled.
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

/**
 * Calls the FastAPI /ask/stream endpoint and streams the answer back
 * chunk by chunk, ChatGPT-style.
 *
 * The backend sends plain chunked text (not JSON, not SSE) -- so we
 * read the response body with a ReadableStream reader and decode
 * each chunk as it arrives, instead of waiting for `res.json()`.
 *
 * @param {string} question - The user's question.
 * @param {(chunk: string, meta: { done: boolean, ok: boolean }) => void} onChunk
 *   Called once per received chunk with `done: false`, and exactly
 *   once more at the very end with `done: true` (chunk === "" on a
 *   clean finish, or an error message if something went wrong).
 * @param {{ signal?: AbortSignal }} [options]
 * @returns {Promise<{ ok: boolean }>}
 */
export async function askQuestionStream(question, onChunk, { signal } = {}) {
  try {
    const res = await fetch(`${API_BASE}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });

    if (!res.ok || !res.body) {
      const text = await res.text().catch(() => "");
      onChunk(`API error ${res.status}: ${text}`, { done: true, ok: false });
      return { ok: false };
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");

    while (true) {
      const { value, done } = await reader.read();

      if (done) break;

      const text = decoder.decode(value, { stream: true });

      if (text) onChunk(text, { done: false, ok: true });
    }

    onChunk("", { done: true, ok: true });

    return { ok: true };
  } catch (err) {
    if (err.name === "AbortError") {
      onChunk("Request cancelled.", { done: true, ok: false });
      return { ok: false };
    }

    onChunk(
      "⚠️ Could not reach the backend.\n\nStart it with:\nuvicorn api:app --reload",
      { done: true, ok: false }
    );

    return { ok: false };
  }
}






// // Base URL of your FastAPI backend. Override at build time with a
// // .env file (VITE_API_BASE=http://localhost:8000) if you deploy the
// // frontend and backend separately.
// export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// /**
//  * Calls the FastAPI /ask endpoint with the same contract the
//  * Streamlit app used: POST { question } -> { answer }.
//  * Returns { answer, ok } so the caller can render an error bubble
//  * without throwing.
//  */
// export async function askQuestion(question, { signal } = {}) {
//   try {
//     const res = await fetch(`${API_BASE}/ask`, { 
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ question }),
//       signal,
//     });

//     if (!res.ok) {
//       const text = await res.text();
//       return { answer: `API error ${res.status}: ${text}`, ok: false };
//     }

//     const data = await res.json();
//     return { answer: data.answer ?? "No answer returned.", ok: true };
//   } catch (err) {
//     if (err.name === "AbortError") {
//       return { answer: "Request cancelled.", ok: false };
//     }
//     return {
//       answer:
//         "⚠️ Could not reach the backend.\n\n" +
//         "Start it with:\nuvicorn api:app --reload",
//       ok: false,
//     };
//   }
// }