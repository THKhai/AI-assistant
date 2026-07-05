FROM python:3.11-slim

WORKDIR /app

# Build tools needed by some Python packages (tokenizers, chromadb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure runtime data directories exist (volumes will overlay these at runtime)
RUN mkdir -p data/sqlite data/chroma_db data/raw data/logs

# Default: web UI. Override in docker-compose for the bot.
CMD ["python", "main.py", "web"]
