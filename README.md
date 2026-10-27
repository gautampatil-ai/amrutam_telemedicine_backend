# Amrutam Telemedicine Backend

A FastAPI reference implementation for telemedicine workflows, including authentication, role-based access control (RBAC), doctor search and availability, concurrency-safe consultation booking, consultation status management, prescriptions, audit trails, and admin analytics.

> **Project status:** Take-home/demo implementation, not a certified or production-approved clinical system. Use synthetic data only. Review `docs/architecture.md` and `docs/security-threat-model.md` before any production deployment.

## Technology Stack

- Python and FastAPI
- SQLAlchemy and PostgreSQL
- Redis-compatible storage for rate limiting and caching
- JWT authentication and Argon2id password hashing
- Pytest and Ruff
- Docker Compose
- GitHub Actions CI
- Prometheus metrics

## Features

- User registration, login, and role-based authorization
- Doctor search and availability-slot management
- Transaction-safe consultation booking
- Idempotency support for safe booking retries
- Consultation lifecycle and prescription workflows
- Audit logging and administrator analytics
- Health and readiness endpoints
- Metrics endpoint for monitoring
- Automated tests, linting, and dependency vulnerability scanning

## Quick Start: Docker

### Prerequisites

- Docker Desktop installed and running
- Git

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/gautampatil-ai/amrutam_telemedicine_backend.git
   cd amrutam_telemedicine_backend
   ```

2. Create your local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Open `.env` and configure the required database, Redis, and JWT settings. Use a unique, strong JWT secret. Never commit `.env` or production secrets.

4. Build and start the services:

   ```bash
   docker compose up --build
   ```

5. Open the API documentation:

   `http://localhost:8000/docs`

   The exact host and port depend on your Docker Compose configuration.

To stop the services, run:

```bash
docker compose down
```

> Check `.env.example` and `docker-compose.yml` for the actual environment variable names, ports, and service configuration. Do not assume the demo is ready for production simply because the containers start.

## Local Development

Activate the project's virtual environment in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Configure `.env` according to `.env.example`, and ensure PostgreSQL and Redis-compatible services are running.

Start the API:

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` to explore the endpoints.

## Testing and Code Quality

Run the automated tests:

```powershell
python -m pytest -q
```

Run lint checks:

```powershell
python -m ruff check app tests
```

Run the dependency vulnerability audit:

```powershell
python -m pip_audit -r requirements.txt
```

Build the container:

```powershell
docker build -t amrutam-telemedicine:local .
```

GitHub Actions runs the configured CI checks on pushes and pull requests. See the Actions tab in the repository for the latest result.

## API Overview

FastAPI generates the API schema and interactive documentation.

- Swagger UI: `/docs`
- OpenAPI schema: `/openapi.json`
- Liveness: `/health/live`
- Readiness: `/health/ready`
- Prometheus metrics: `/metrics`

Main endpoint groups include authentication, users, doctors, availability slots, consultations, prescriptions, and administrator analytics/audit logs. Use `/docs` to confirm request schemas, authorization requirements, and available routes for the current version.

## Demo Data and Video

Use the project's documented demo bootstrap process, if configured, to create synthetic demo accounts. Check `scripts/bootstrap_demo.py` and the environment configuration for the actual credentials and setup steps.

Do not publish real credentials, tokens, or patient information in the repository or demo recording.

See `docs/demo-script.md` for the five-minute walkthrough.

## Documentation

- `docs/architecture.md` - architecture, data flow, ER model, booking sequence, scaling, reliability, and production recommendations
- `docs/security-threat-model.md` - data classification, attack surface, threats, mitigations, and security checklist
- `docs/adr-001-booking-consistency.md` - booking consistency decision and rationale
- `docs/demo-script.md` - demonstration plan

## Security and Production Limitations

This project is a reference implementation and must not be used to process real patient data without appropriate engineering, security, privacy, and legal review.

Production deployment requires, at minimum, secure secret management and rotation, TLS, database migrations, backup and restore testing, appropriate encryption and access controls, stronger authentication for privileged users, monitoring and incident response, load testing, and review of applicable Indian data-protection and healthcare requirements.

The latency and availability goals in the architecture document are targets, not measured production guarantees.

## Repository

GitHub: https://github.com/gautampatil-ai/amrutam_telemedicine_backend
