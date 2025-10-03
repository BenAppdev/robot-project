# Raspberry Pi Dockerfile for camera streaming
FROM balenalib/raspberrypi3-debian:buster

# Set non-interactive frontend for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libopencv-dev \
    python3-opencv \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for TCP streaming
RUN pip3 install numpy

# Enable camera access
RUN usermod -a -G video root

# Copy streaming scripts (to be added later in /pi-scripts)
WORKDIR /app
COPY . /app

# Expose TCP ports for low-res and full-res streams
EXPOSE 5000 5001

# Command to run streaming script (placeholder, replace with actual script)
CMD ["python3", "streamer.py"]
