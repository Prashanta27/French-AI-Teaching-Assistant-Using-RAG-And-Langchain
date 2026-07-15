"""
FastAPI wrapper around LLMGenerator.

Run with:
    uvicorn api:app --host 0.0.0.0 --port 8000

LLMGenerator loads a vector store, an embedding model, and warms up
the query-understanding pipeline -- all of that happens ONCE at
server startup (via the lifespan handler below), not per-request.
Doing it per-request would reload the embedding model on every single
question, which would be unusably slow.

Two endpoints are exposed:
    - POST /ask         -- waits for the full answer, returns JSON
    - POST /ask/stream   -- streams the answer as plain text chunks,
                            for a typing/ChatGPT-style frontend effect
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.LLM.llm_generator import LLMGenerator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Populated at startup, used by the /ask and /ask/stream endpoints. A
# module-level singleton like this is the simplest option for a
# single-process deployment; if you later run multiple worker
# processes, each process gets its own instance (each with its own
# loaded model) -- fine for correctness, just means N x the
# memory/startup cost.
_generator: Optional[LLMGenerator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):

    global _generator

    logger.info("Starting up: loading LLMGenerator...")

    _generator = LLMGenerator()

    logger.info("Startup complete.")

    yield

    logger.info("Shutting down.")


app = FastAPI(
    title="French AI Teaching Assistant",
    version="1.0",
    lifespan=lifespan
)

# Adjust allow_origins for your actual frontend's domain(s) before
# deploying -- "*" is fine for local development only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------

class AskRequest(BaseModel):

    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):

    answer: str


class HealthResponse(BaseModel):

    status: str


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health():

    if _generator is None:

        raise HTTPException(status_code=503, detail="Still starting up.")

    return HealthResponse(status="ok")


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """Non-streaming: waits for the full answer, then returns it as JSON."""

    if _generator is None:

        raise HTTPException(status_code=503, detail="Still starting up.")

    try:

        answer = _generator.generate(request.question)

    except Exception:

        logger.exception("Unhandled error while generating an answer.")

        raise HTTPException(
            status_code=500,
            detail="Something went wrong while generating the answer."
        )

    return AskResponse(answer=answer)


@app.post("/ask/stream")
def ask_stream(request: AskRequest):
    """Streaming: returns the answer as a chunked plain-text response.

    The frontend reads this with `fetch(...).body.getReader()` (NOT
    `res.json()`) and appends each chunk to the message bubble as it
    arrives. This is plain chunked text, not Server-Sent Events (SSE)
    -- simpler to consume from `fetch` and sufficient for a single
    text stream like this one.
    """

    if _generator is None:

        raise HTTPException(status_code=503, detail="Still starting up.")

    def token_stream():

        try:

            for chunk in _generator.generate_stream(request.question):

                yield chunk

        except Exception:

            logger.exception("Unhandled error while streaming an answer.")

            yield "\n[Something went wrong while generating the answer.]"

    return StreamingResponse(
        token_stream(),
        media_type="text/plain",
        headers={
            # Prevents some reverse proxies (e.g. nginx) from buffering
            # the whole response before sending it -- without this,
            # streaming can silently turn back into one big chunk in
            # production even though it works fine with `uvicorn --reload`.
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )











# """
# FastAPI wrapper around LLMGenerator.

# Run with:
#     uvicorn api:app --host 0.0.0.0 --port 8000

# LLMGenerator loads a vector store, an embedding model, and warms up
# the query-understanding pipeline -- all of that happens ONCE at
# server startup (via the lifespan handler below), not per-request.
# Doing it per-request would reload the embedding model on every single
# question, which would be unusably slow.
# """

# import logging
# from contextlib import asynccontextmanager
# from typing import Optional

# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field

# from src.LLM.openai_client import OpenAILLM

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Populated at startup, used by the /ask endpoint. A module-level
# # singleton like this is the simplest option for a single-process
# # deployment; if you later run multiple worker processes, each
# # process gets its own instance (each with its own loaded model) --
# # fine for correctness, just means N x the memory/startup cost.
# _generator: Optional[OpenAILLM] = None


# @asynccontextmanager
# async def lifespan(app: FastAPI):

#     global _generator

#     logger.info("Starting up: loading OpenAILLM...")

#     _generator = OpenAILLM()

#     logger.info("Startup complete.")

#     yield

#     logger.info("Shutting down.")


# app = FastAPI(
#     title="French AI Teaching Assistant",
#     version="1.0",
#     lifespan=lifespan
# )

# # Adjust allow_origins for your actual frontend's domain(s) before
# # deploying -- "*" is fine for local development only.
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ---------------------------------------------------------
# # Request / response schemas
# # ---------------------------------------------------------

# class AskRequest(BaseModel):

#     question: str = Field(..., min_length=1, max_length=2000)


# class AskResponse(BaseModel):

#     answer: str


# class HealthResponse(BaseModel):

#     status: str


# # ---------------------------------------------------------
# # Endpoints
# # ---------------------------------------------------------

# @app.get("/health", response_model=HealthResponse)
# def health():

#     if _generator is None:

#         raise HTTPException(status_code=503, detail="Still starting up.")

#     return HealthResponse(status="ok")


# @app.post("/ask", response_model=AskResponse)
# def ask(request: AskRequest):

#     if _generator is None:

#         raise HTTPException(status_code=503, detail="Still starting up.")

#     try:

#         answer = _generator.generate(request.question)

#     except Exception:

#         logger.exception("Unhandled error while generating an answer.")

#         raise HTTPException(
#             status_code=500,
#             detail="Something went wrong while generating the answer."
#         )

#     return AskResponse(answer=answer)





# # from fastapi import FastAPI
# # from pydantic import BaseModel

# # from src.ollama_client import LLMGenerator


# # app = FastAPI()


# # generator = LLMGenerator(model="llama3.2")


# # class QuestionRequest(BaseModel):
# #     question: str


# # @app.get("/")
# # def root():

# #     return {

# #         "message":"French Tutor API Running"

# #     }


# # @app.post("/chat")
# # def chat(request: QuestionRequest):


# #     answer = generator.generate(

# #         request.question

# #     )


# #     return {

# #         "question":request.question,

# #         "answer":answer

# #     }