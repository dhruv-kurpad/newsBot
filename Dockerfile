FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt README.md spec.md ./
COPY newsbot ./newsbot
COPY gmail_auth.py ./

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "newsbot"]
