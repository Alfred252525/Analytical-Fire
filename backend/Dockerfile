FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Clear Python cache to ensure fresh imports
RUN find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
RUN find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Create public directory for landing page
RUN mkdir -p /app/public

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
