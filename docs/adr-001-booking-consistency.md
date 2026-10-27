# ADR-001: PostgreSQL is authoritative for booking

**Status:** Accepted

## Context
Two patients may attempt to reserve one doctor slot at the same time. A cache-only lock or availability check without a transaction can allow double booking.

## Decision
Lock the availability row with `SELECT ... FOR UPDATE`, verify it is available, set it unavailable, insert the consultation, idempotency record and audit event in one transaction. A unique constraint on `consultations.slot_id` is an independent consistency guard. Redis is not authoritative for booking state.

## Consequences
- Correctness is preserved across multiple API replicas when all use the same PostgreSQL primary.
- Contention serializes attempts for one slot; unrelated slots can proceed concurrently.
- Retries use an idempotency key. A durable outbox should be added before dispatching external side effects.
