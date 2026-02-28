FROM python:3.12-slim

# Install system dependencies required by some MySQL drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Uvicorn docs: https://www.uvicorn.org/deployment/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
