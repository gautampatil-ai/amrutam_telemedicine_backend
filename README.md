# Amrutam Telemedicine Backend

A FastAPI reference implementation for telemedicine workflows, including authentication, role-based access, doctor search and availability, concurrency-safe booking, consultation status management, prescriptions, audit trails, and admin analytics.

> **Take-home / demo status:** This is a starter implementation, not a certified or production-approved clinical system. Do not use real patient data. See `docs/security-threat-model.md` and `docs/architecture.md` for production gaps.

## Stack

Python, FastAPI, SQLAlchemy 2, PostgreSQL, Redis-compatible storage, pytest, Docker Compose, GitHub Actions, Prometheus, and Grafana.

## Quick start (Docker)

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Set a strong, unique `JWT_SECRET` and secure the database and Redis credentials.
4. Run:

```bash
docker compose up --build