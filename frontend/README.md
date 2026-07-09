# FrenchAI — React frontend

A pixel-faithful React port of the Streamlit UI, talking to your existing
FastAPI backend at `POST /chat`.

## 1. Install and run the frontend

```bash
cd french-ai-react
npm install
npm run dev
```

This starts Vite's dev server, by default at **http://localhost:5173**.

## 2. Point it at your FastAPI backend

By default the app calls `http://localhost:8000`. If your backend runs
somewhere else, create a `.env` file next to `package.json`:

```
VITE_API_BASE=http://localhost:8000
```

## 3. IMPORTANT — enable CORS on your FastAPI app

The browser is now loading the frontend from `localhost:5173` and calling
the API on `localhost:8000` — that's a cross-origin request, and FastAPI
will reject it by default. Add this to your `api.py` (wherever you create
the `FastAPI()` app), **before** your route definitions:

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Without this, every request from the React app will fail silently with a
CORS error in the browser console (not a Python error — check DevTools →
Console/Network if requests seem to vanish).

## 4. Confirm the API contract matches

This frontend assumes your `/chat` endpoint looks like:

```python
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    answer = generator.generate(req.question)
    return {"answer": answer}
```

If your actual FastAPI route uses different field names, update
`src/api.js` (`askQuestion`) to match — that's the only file that knows
about the request/response shape.

## 5. Run both together (typical dev workflow)

Terminal 1:
```bash
uvicorn api:app --reload --port 8000
```

Terminal 2:
```bash
npm run dev
```

Open http://localhost:5173.

## 6. Building for production

```bash
npm run build
```

Outputs static files to `dist/`. Serve them with any static host (nginx,
Vercel, or even FastAPI's `StaticFiles`) — just make sure `VITE_API_BASE`
is set correctly at build time if the API isn't on the same origin as the
frontend.

## What changed vs. the Streamlit version

- **Sessions/threads** are now held in React state and persisted to
  `localStorage` (`src/hooks/useSessions.js`) instead of
  `st.session_state` — this means threads survive a page refresh, same
  as before.
- **Streaming typing indicator** is a CSS animation shown while the
  `fetch` to `/chat` is in flight (`isTyping` state in `App.jsx`).
- **Rewrite** re-sends the user question that preceded a given AI
  answer. **Copy** uses `navigator.clipboard`.
- All visual tokens (colors, spacing, fonts, dark mode via
  `prefers-color-scheme`) are copied 1:1 from your Streamlit CSS into
  `src/index.css` — same look, no re-design.
- No component library is used; it's plain CSS + React state, matching
  the original's minimal-dependency spirit.

## File structure

```
french-ai-react/
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.jsx           entry point
│   ├── App.jsx            top-level layout + send/typing logic
│   ├── api.js             fetch wrapper for POST /chat
│   ├── format.js           **bold** / *italic* / `code` -> HTML (escaped first)
│   ├── index.css          all styles (ported from Streamlit CSS)
│   ├── hooks/
│   │   └── useSessions.js  thread state + localStorage persistence
│   └── components/
│       ├── Sidebar.jsx
│       ├── TopBar.jsx
│       ├── EmptyState.jsx
│       ├── ChatMessage.jsx
│       ├── ChatInput.jsx
│       └── TypingIndicator.jsx
```
