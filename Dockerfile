# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for speech recognition and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    portaudio19-dev \
    flac \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining codebase
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Streamlit environment configurations
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_HEADLESS=true

# Command to launch Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
