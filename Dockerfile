FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    openssh-client \
    sshpass \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl for in-cluster plugin apply operations.
RUN KUBECTL_VERSION="$(curl -L -s https://dl.k8s.io/release/stable.txt)" && \
    curl -L --fail --output /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    chmod +x /usr/local/bin/kubectl

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
RUN mkdir -p data logs config ansible/inventory ssh_keys backups migrations

# Set proper permissions for SSH keys directory
RUN chmod 700 ssh_keys

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app
ENV PYTHONPATH=/app
ENV ORCHESTRATOR_CONFIG=/app/config/cluster.yml

# Run the production web application.
CMD ["gunicorn", "--config", "deployment/config/gunicorn.conf.py", "wsgi:application"]
