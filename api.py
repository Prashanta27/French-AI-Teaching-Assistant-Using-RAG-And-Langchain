"""
FastAPI wrapper around LLMGenerator.

Run with:
    uvicorn api:app --host 0.0.0.0 --port 8000

LLMGenerator loads a vector store, an embedding model, and warms up
the query-understanding pipeline -- all of that happens ONCE at
server startup (via the lifespan handler below), not per-request.
Doing it per-request would reload the embedding model on every single
question, which would be unusably slow.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.ollama_client import LLMGenerator


logger = logging.getLogger(__name__)

# Populated at startup, used by the /ask endpoint. A module-level
# singleton like this is the simplest option for a single-process
# deployment; if you later run multiple worker processes, each
# process gets its own instance (each with its own loaded model) --
# fine for correctness, just means N x the memory/startup cost.
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





# from fastapi import FastAPI
# from pydantic import BaseModel

# from src.ollama_client import LLMGenerator


# app = FastAPI()


# generator = LLMGenerator(model="llama3.2")


# class QuestionRequest(BaseModel):
#     question: str


# @app.get("/")
# def root():

#     return {

#         "message":"French Tutor API Running"

#     }


# @app.post("/chat")
# def chat(request: QuestionRequest):


#     answer = generator.generate(

#         request.question

#     )


#     return {

#         "question":request.question,

#         "answer":answer

#     }