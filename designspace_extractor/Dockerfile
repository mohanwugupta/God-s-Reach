FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    octave \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Install JavaScript parsers
RUN npm install -g @babel/parser @babel/traverse

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt requirements.lock* ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directories
RUN mkdir -p out/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Create non-root user
RUN useradd -m -u 1000 extractor && \
    chown -R extractor:extractor /app
USER extractor

# Entry point
ENTRYPOINT ["python", "-m", "designspace_extractor"]
