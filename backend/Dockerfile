# Use an official lightweight Python image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 📦 Install system dependencies + libgomp1 (Mandatory for FlashRank / ONNX)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first
COPY requirements.txt .

# 🚀 THE CRITICAL FIX: Upgrade pip, setuptools, and wheel first!
# This ensures Docker pulls precompiled binaries instead of building from source.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install your Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your backend application source code
COPY . .

# Expose FastAPI's default port
EXPOSE 8000

# Run Uvicorn with live reload enabled
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]