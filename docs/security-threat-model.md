# Security checklist and threat model

## Data classification
- **Restricted health data:** consultation reason, prescriptions, clinical notes (future), payment references. Least-privilege access; encrypt at rest/in transit; do not log.
- **Sensitive identity data:** email, phone, profile data. Limit access and retention.
- **Operational data:** request IDs, status codes, aggregate counts. Avoid identifiers and low-cardinality metric labels.
- **Secrets:** JWT signing key, database/Redis credentials. Environment variables are for local demo only; production uses a secret manager.

## Threats and mitigations
| Threat | Example | Mitigation / status |
|---|---|---|
| Broken authentication | stolen or brute-forced password | Argon2id password hashing, generic login error, rate limiting; add MFA and breached-password controls before production |
| Broken object-level authorization | patient reads another patient's prescription | ownership checks for consultation and prescription endpoints; add negative tests for every object route |
| Privilege escalation | patient creates doctor/admin | public registration assigns patient role only; admin-only doctor provisioning |
| Double booking / race | two patients reserve same slot | `SELECT FOR UPDATE`, unique slot constraint, transaction and idempotency key |
| Replay / duplicate writes | client retries after timeout | persisted per-user idempotency record; payload hash mismatch returns 409 |
| Injection | crafted search or JSON input | SQLAlchemy parameterization and Pydantic validation; avoid dynamic SQL |
| Sensitive data exposure | tokens/clinical notes in logs | structured access logs exclude request body and auth headers; TLS and encryption at rest must be enabled in deployment |
| DoS / brute force | repeated login or search | Redis-backed IP rate limiter; deploy WAF, route-specific quotas and alerts |
| Dependency/supply-chain | vulnerable package | pinned direct dependencies, CI `pip-audit`; add lockfile/SBOM and image scanning |
| Audit tampering | privileged actor edits history | append-only application behavior; production should export to immutable/WORM storage and restrict DB permissions |
| Secret leakage | committed `.env` | `.env` ignored; `.env.example` contains demo-only values; rotate immediately if exposed |
| Insecure transport | sniffed credentials | TLS termination at load balancer; enforce HSTS and TLS to all managed services in production |

## Attack surface
Public endpoints: registration, login, doctor search, availability search, booking, health and metrics. Authenticated endpoints: profile, booking history, consultation state and prescriptions. Privileged endpoints: doctor provisioning, analytics, audit log access. Infrastructure surfaces include load balancer, API containers, PostgreSQL, Redis, CI runner, image registry, backups and secrets manager. Do not expose PostgreSQL/Redis publicly; restrict metrics to the internal network in production.

## Checklist
- [x] Argon2id password hashing
- [x] JWT access token expiry and signature verification
- [x] RBAC and resource ownership checks on implemented workflows
- [x] Pydantic input validation and parameterized SQL
- [x] Booking transaction, row lock, unique slot and idempotency key
- [x] Audit records for core mutations
- [x] Rate limiting and request IDs
- [x] Dependency audit in CI
- [x] Non-root container and no-new-privileges
- [ ] Production TLS, managed KMS/secret manager, key rotation and field-level encryption
- [ ] MFA/step-up auth for clinicians/admins; refresh-token rotation/revocation
- [ ] Alembic migration workflow and database least-privilege roles
- [ ] Immutable audit export, SIEM, retention/deletion and consent workflows
- [ ] SAST, container scanning, SBOM, DAST and independent penetration test
- [ ] Load, concurrency, restore and disaster-recovery drills
- [ ] Legal/privacy review for applicable Indian DPDP, telemedicine and clinical-record obligations

## Key rotation
JWT signing keys must be rotated with a key ID (`kid`) and a short overlap window where old keys verify existing access tokens until expiry. Database credentials should rotate through a secret manager with overlapping credentials or controlled pool restart. Encryption keys belong in KMS; use envelope encryption and rotate data-encryption keys without exposing plaintext keys to application logs. This take-home does not implement key rotation or field-level encryption and must not be represented as doing so.
