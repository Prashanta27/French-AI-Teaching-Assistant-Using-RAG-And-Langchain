# 🇫🇷 French AI Teaching Assistant Using RAG and LangChain

A Retrieval-Augmented Generation (RAG) based French language teaching assistant built with LangChain, ChromaDB, SentenceTransformers, Ollama (Llama 3.2), FastAPI, and Streamlit.

## Features

* PDF Ingestion
* Semantic Search using ChromaDB
* SentenceTransformer Embeddings
* Local LLM Inference using Ollama
* Prompt Engineering
* FastAPI Backend
* Streamlit Frontend
* French Language Tutoring

## Tech Stack

Python

LangChain

Sentence Transformers

ChromaDB

Ollama

Llama 3.2

FastAPI

Streamlit

Docker

## Project Structure

French-AI-Teaching-Assistant-Using-RAG/

│

├── data/

│ ├── pdf/

│ └── vector_store/

│

├── src/

│ ├── data_loader.py

│ ├── split_document.py

│ ├── embedding.py

│ ├── vector_store.py

│ ├── retriever.py

│ ├── prompt_builder.py

│ └── ollama_client.py

│

├── main.py

├── streamlit_app.py

├── requirements.txt

├── Dockerfile

└── README.md

## Installation

Clone repository

git clone https://github.com/Prashanta27/French-AI-Teaching-Assistant-Using-RAG-And-Langchain.git

cd French-AI-Teaching-Assistant-Using-RAG-And-Langchain

Create virtual environment

python -m venv .venv

Activate Windows

.venv\Scripts\activate

Linux

source .venv/bin/activate

Install packages

pip install -r requirements.txt

Run Ollama

ollama run llama3.2

Run FastAPI

uvicorn main:app --reload

Open browser

http://localhost:8000/docs

Run Streamlit

streamlit run streamlit_app.py

## Docker

Build image

docker build -t french-rag .

Run container

docker run -p 8000:8000 french-rag

## Future Improvements

Conversation Memory

Citation Support

Streaming Responses

React Frontend

Docker Compose

AWS Deployment

## Author

Prashanta Das
