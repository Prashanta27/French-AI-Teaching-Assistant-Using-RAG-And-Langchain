# base image
FROM python:3.11-slim

# workdir

WORKDIR /app

# Copy requirements

COPY requirements.txt .

# Install dependencies

RUN pip install --no-cache-dir -r requirements.txt

# Copy source code

COPY . .


# port

EXPOSE 8000

# Start FastAPI

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
