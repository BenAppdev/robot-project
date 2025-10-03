# Ubuntu Dockerfile for Xeon server: OpenCV, Ollama, TCP stream processing
FROM ubuntu:20.04

# Set non-interactive frontend for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libopencv-dev \
    python3-opencv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies for TCP server
RUN pip3 install numpy

# Copy server scripts (to be added later in /ubuntu-docker)
WORKDIR /app
COPY . /app

# Expose TCP ports for low-res and full-res streams
EXPOSE 5000 5001

# Command to run TCP server (placeholder, replace with actual script)
CMD ["python3", "server.py"]
