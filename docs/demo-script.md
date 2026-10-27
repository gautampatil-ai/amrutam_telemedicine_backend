# Five-minute demo video script

**0:00–0:30 — Overview**
Show the repository and architecture diagram. Explain the stack and state that the demo uses synthetic data only.

**0:30–1:10 — API documentation and auth**
Open `/docs`. Register a patient, log in, copy the access token, call `/users/me`. Show that anonymous access fails and a patient receives `403` from admin analytics.

**1:10–2:20 — Doctor availability and booking**
Using local demo doctor/admin fixtures, show verified doctor search and a future availability slot. Book with `Idempotency-Key: demo-booking-0001`. Repeat the exact request and explain safe retry behavior. Reuse the key with a different body and show `409`. Try another booking for the same slot and show `409`.

**2:20–3:00 — Consultation lifecycle**
Show valid transitions: booked → confirmed → in_progress → completed. Demonstrate an invalid transition returning `409`. Show ownership checks.

**3:00–3:35 — Prescription and audit**
Create a prescription as the owning doctor after completion; show that patients can read their own but not another patient's prescription. Show the admin audit log with mutation events.

**3:35–4:20 — Tests and CI**
Run `pytest`, `ruff check app tests`, and show the GitHub Actions workflow. Mention dependency scanning.

**4:20–5:00 — Observability and architecture**
Show `/health/ready`, `/metrics`, and optional Prometheus. Explain transaction locking, Redis rate limiting, async outbox/queue production extension, backups, RPO/RTO targets and production-hardening checklist.

Do not claim measured 99.95% availability or p95 targets unless you run and document load tests in the target environment.
