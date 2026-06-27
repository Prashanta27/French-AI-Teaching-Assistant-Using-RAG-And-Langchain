from fastapi import FastAPI
from pydantic import BaseModel

from src.ollama_client import LLMGenerator


app = FastAPI()


generator = LLMGenerator(model="llama3.2")


class QuestionRequest(BaseModel):
    question: str


@app.get("/")
def root():

    return {

        "message":"French Tutor API Running"

    }


@app.post("/chat")
def chat(request: QuestionRequest):


    answer = generator.generate(

        request.question

    )


    return {

        "question":request.question,

        "answer":answer

    }