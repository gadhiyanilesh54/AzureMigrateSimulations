FROM python:3.12-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install the package with web + mcp extras
RUN pip install --no-cache-dir -e ".[web,mcp]"

# Copy data directory (if present, for demo)
COPY data/ data/

# Expose ports
EXPOSE 5000 3001

# Default: run web dashboard
CMD ["python", "-m", "azure_migrate_simulations.web.app"]
