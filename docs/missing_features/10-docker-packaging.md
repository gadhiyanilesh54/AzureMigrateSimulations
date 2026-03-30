# Feature Spec: Docker Packaging

**ID**: 10-docker-packaging  
**Phase**: PLATFORM  
**Priority**: Tier 2 — Medium Impact  
**Status**: Not Started  
**Depends On**: Web App (✅)

## Problem Statement

Deploying the application requires Python, pip, and manual dependency installation. For partner-hosted or customer-portable scenarios, a containerised deployment is essential. Docker also enables Kubernetes deployment for multi-tenant partner scenarios.

## Goal

Package Azure Migrate Simulations as a **Docker container** with both the web dashboard and MCP server, plus a `docker-compose.yml` for easy startup.

## User Stories

### US-1: Docker Single-Command Start (P1)
```bash
docker run -p 5000:5000 -v ./data:/app/data ghcr.io/azure-migrate-simulations:latest
```

### US-2: Docker Compose with MCP (P1)
```yaml
# docker-compose.yml starts both web dashboard and MCP SSE server
services:
  web:     # port 5000
  mcp-sse: # port 3001
```

### US-3: Persistent Data Volume (P1)
**Given** a Docker container, **When** restarted, **Then** all data in `data/` persists via volume mount.

### US-4: Environment Configuration (P2)
**Given** Docker, **When** `MIGRATE_API_KEY` and `MCP_PORT` are set via env vars, **Then** authentication and ports are configurable without rebuilding.

## Deliverables

- `Dockerfile` — multi-stage build (slim Python image)
- `docker-compose.yml` — web + MCP services
- `.dockerignore` — exclude `.venv`, `__pycache__`, `.git`
- Updated README with Docker quickstart
