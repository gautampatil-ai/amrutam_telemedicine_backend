# Five-Minute Demo Video Script

**0:00-0:30 - Overview**

Show the GitHub repository and architecture diagram. Introduce FastAPI, PostgreSQL, Redis, and the main features. Confirm that the demo uses synthetic data only.

**0:30-1:10 — API Documentation and Authentication**

Open `/docs`. Register a patient, log in, and use the access token to call `/users/me`. Demonstrate that anonymous access is rejected and that a patient receives `403 Forbidden` when accessing admin analytics.

**1:10-2:20 — Doctor Availability and Booking**

Use the local demo doctor/admin accounts. Show verified doctor search and an upcoming availability slot. Book a consultation using `Idempotency-Key: demo-booking-0001`. Repeat the same request to demonstrate safe retries. Reuse the key with a different request body and show `409 Conflict`. Attempt to book the same slot again and show that duplicate booking is rejected.

**2:20-3:00 — Consultation Lifecycle**

Demonstrate the valid status transitions: `booked` -> `confirmed` -> `in_progress` -> `completed`. Show an invalid transition returning `409 Conflict` and verify resource ownership restrictions.

**3:00-3:35 — Prescriptions and Audit Logs**

Create a prescription as the authorized doctor after consultation completion. Show that the patient can access their own prescription but cannot access another patient's prescription. Open the admin audit log and show recorded mutation events.

**3:35-4:20 — Tests and Continuous Integration**

Run `python -m pytest -q` and `python -m ruff check app tests`. Open the GitHub Actions workflow and show the successful run, including dependency vulnerability scanning.

**4:20-5:00 — Observability and Architecture**

Show `/health/ready` and `/metrics`, and Prometheus if configured. Explain database transaction locking, Redis rate limiting, the proposed asynchronous outbox/queue, encrypted backups, and the documented recovery objectives.

**Important:** Do not claim that 99.95% availability or the p95 latency targets have been achieved unless you have supporting measurements from load tests and the target deployment.
