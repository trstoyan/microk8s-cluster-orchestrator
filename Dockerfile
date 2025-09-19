FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    sshpass \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ansible
RUN pip install ansible>=8.0.0

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install Ansible collections
RUN ansible-galaxy install -r ansible/requirements.yml

# Create necessary directories
RUN mkdir -p logs config ansible/inventory

# Initialize the application
RUN python cli.py init

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app
ENV PYTHONPATH=/app

# Run the web application
CMD ["python", "cli.py", "web", "--host", "0.0.0.0", "--port", "5000"]
