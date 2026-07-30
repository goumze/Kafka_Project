FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# requirements live at repo root; also support local copy
COPY requirements.txt* ./
# If requirements not in build context, fall back to inline install list
RUN if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    else \
      pip install --no-cache-dir \
        "kafka-python>=2.0.2" \
        "fastapi==0.111.0" \
        "uvicorn[standard]==0.30.1" \
        "pydantic==2.7.4" \
        "requests>=2.31.0" \
        "python-multipart>=0.0.6"; \
    fi

COPY . .

# Ensure import paths work when WORKDIR is /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Default: API. Consumer service overrides CMD.
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
