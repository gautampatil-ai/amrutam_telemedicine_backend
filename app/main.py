import hashlib
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from redis import Redis
from redis.exceptions import RedisError
from app.config import settings
from app.db import Base, engine, get_db
from app import models, schemas
from app.security import hash_password, verify_password, create_access_token, decode_token
from app.observability import RequestObservabilityMiddleware, metrics_response

logging.basicConfig(level=logging.INFO)
bearer = HTTPBearer(auto_error=False)
redis_client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # For a take-home/demo. Production deployments should use Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield
    try:
        redis_client.close()
    except Exception:
        pass

app = FastAPI(title=settings.app_name, version="1.0.0", description="Secure telemedicine workflow API", lifespan=lifespan)
app.add_middleware(RequestObservabilityMiddleware)

@app.middleware("http")
async def basic_rate_limit(request: Request, call_next):
    if request.url.path in ("/health/live", "/health/ready", "/metrics"):
        return await call_next(request)
    key = f"rl:{request.client.host if request.client else 'unknown'}:{int(time.time() // 60)}"
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 60)
        if count > settings.rate_limit_per_minute:
            return __import__("fastapi").responses.JSONResponse({"detail":"Rate limit exceeded"}, status_code=429)
    except RedisError:
        # Fail open for availability; production should alert and may fail closed for sensitive routes.
        logging.warning("Redis unavailable; rate limit bypassed")
    return await call_next(request)

def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not creds:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate":"Bearer"})
    try:
        payload = decode_token(creds.credentials)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(models.User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or unknown user")
    return user

def require_roles(*roles):
    def dependency(user: models.User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency

def audit(db: Session, actor: int | None, action: str, resource_type: str, resource_id: str, details: dict | None = None):
    db.add(models.AuditLog(actor_user_id=actor, action=action, resource_type=resource_type,
                           resource_id=str(resource_id), detail_json=json.dumps(details or {}, separators=(",",":"))))

@app.get("/health/live", tags=["health"], response_model=schemas.HealthOut)
def liveness():
    return {"status":"ok"}

@app.get("/health/ready", tags=["health"], response_model=schemas.HealthOut)
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status":"ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")

@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_response()

@app.post("/auth/register", response_model=schemas.UserOut, status_code=201, tags=["auth"])
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(email=email, password_hash=hash_password(payload.password), role="patient")
    db.add(user)
    db.flush()
    db.add(models.Profile(user_id=user.id, full_name=payload.full_name.strip()))
    audit(db, user.id, "user.registered", "user", user.id)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

@app.post("/auth/login", response_model=schemas.TokenOut, tags=["auth"])
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        # Same response avoids disclosing whether an email exists.
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token":create_access_token(user.id, user.role),
            "expires_in":settings.access_token_minutes*60}

@app.get("/users/me", response_model=schemas.UserOut, tags=["users"])
def me(user: models.User = Depends(current_user)):
    return user

@app.post("/admin/doctors", response_model=schemas.DoctorOut, status_code=201, tags=["admin"])
def create_doctor(payload: schemas.DoctorCreate, db: Session = Depends(get_db),
                  admin: models.User = Depends(require_roles("admin"))):
    user = db.get(models.User, payload.user_id)
    if not user or user.role != "doctor":
        raise HTTPException(status_code=400, detail="user_id must reference a doctor-role user")
    doctor = models.Doctor(**payload.model_dump())
    db.add(doctor)
    audit(db, admin.id, "doctor.created", "doctor", payload.user_id)
    try:
        db.commit()
        db.refresh(doctor)
        return doctor
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Doctor profile already exists")

@app.get("/doctors", response_model=list[schemas.DoctorOut], tags=["doctors"])
def search_doctors(specialty: str | None = None, verified_only: bool = True,
                   limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 100)
    query = select(models.Doctor)
    if specialty:
        query = query.where(models.Doctor.specialty.ilike(f"%{specialty}%"))
    if verified_only:
        query = query.where(models.Doctor.is_verified.is_(True))
    return list(db.scalars(query.order_by(models.Doctor.id).limit(limit).offset(max(offset,0))).all())

@app.post("/doctors/{doctor_id}/slots", response_model=schemas.SlotOut, status_code=201, tags=["availability"])
def create_slot(doctor_id: int, payload: schemas.SlotCreate, db: Session = Depends(get_db),
                user: models.User = Depends(require_roles("doctor", "admin"))):
    doctor = db.scalar(select(models.Doctor).where(models.Doctor.id == doctor_id))
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if user.role == "doctor" and doctor.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot create availability for another doctor")
    start = payload.starts_at
    end = payload.ends_at
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise HTTPException(status_code=422, detail="Use timezone-aware datetimes and end after start")
    if start <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Availability must be in the future")
    slot = models.AvailabilitySlot(doctor_id=doctor_id, starts_at=start, ends_at=end, is_available=True)
    db.add(slot)
    audit(db, user.id, "availability.created", "availability_slot", "pending")
    try:
        db.commit()
        db.refresh(slot)
        return slot
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slot already exists")

@app.get("/doctors/{doctor_id}/slots", response_model=list[schemas.SlotOut], tags=["availability"])
def list_slots(
    doctor_id: int,
    from_at: datetime | None = None,
    to_at: datetime | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 200)
    query = select(models.AvailabilitySlot).where(
        models.AvailabilitySlot.doctor_id == doctor_id,
        models.AvailabilitySlot.is_available.is_(True),
    )

    if from_at:
        query = query.where(models.AvailabilitySlot.starts_at >= from_at)

    if to_at:
        query = query.where(models.AvailabilitySlot.starts_at < to_at)

    return list(
        db.scalars(
            query.order_by(models.AvailabilitySlot.starts_at).limit(limit)
        ).all()
    )

@app.post("/consultations", response_model=schemas.ConsultationOut, status_code=201, tags=["consultations"])
def book_consultation(payload: schemas.BookingIn, request: Request,
                      idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
                      db: Session = Depends(get_db),
                      patient: models.User = Depends(require_roles("patient"))):
    body_hash = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    existing = db.scalar(select(models.IdempotencyRecord).where(
        models.IdempotencyRecord.user_id == patient.id,
        models.IdempotencyRecord.key == idempotency_key))
    if existing:
        if existing.request_hash != body_hash:
            raise HTTPException(status_code=409, detail="Idempotency key reused with a different request")
        return schemas.ConsultationOut.model_validate(json.loads(existing.response_json))
    try:
        # Lock the slot row to serialize concurrent bookings for this slot.
        slot = db.scalar(select(models.AvailabilitySlot).where(
            models.AvailabilitySlot.id == payload.slot_id).with_for_update())
        if not slot:
            raise HTTPException(status_code=404, detail="Availability slot not found")
        if not slot.is_available:
            raise HTTPException(status_code=409, detail="Slot is no longer available")
        doctor = db.get(models.Doctor, slot.doctor_id)
        if not doctor or not doctor.is_verified:
            raise HTTPException(status_code=409, detail="Doctor is not verified")
        slot.is_available = False
        consultation = models.Consultation(patient_id=patient.id, doctor_id=doctor.id,
            slot_id=slot.id, status="booked", reason=payload.reason)
        db.add(consultation)
        db.flush()
        audit(db, patient.id, "consultation.booked", "consultation", consultation.id,
              {"doctor_id":doctor.id,"slot_id":slot.id})
        result = schemas.ConsultationOut.model_validate(consultation)
        record = models.IdempotencyRecord(user_id=patient.id, key=idempotency_key,
            request_hash=body_hash, response_json=result.model_dump_json(), status_code=201)
        db.add(record)
        db.commit()
        db.refresh(consultation)
        return consultation
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        # Includes a race on idempotency key or unique slot constraint.
        replay = db.scalar(select(models.IdempotencyRecord).where(
            models.IdempotencyRecord.user_id == patient.id,
            models.IdempotencyRecord.key == idempotency_key))
        if replay and replay.request_hash == body_hash:
            return schemas.ConsultationOut.model_validate(json.loads(replay.response_json))
        raise HTTPException(status_code=409, detail="Slot booked or idempotency conflict")

@app.get("/consultations", response_model=list[schemas.ConsultationOut], tags=["consultations"])
def list_consultations(db: Session = Depends(get_db), user: models.User = Depends(current_user),
                       limit: int = 50, offset: int = 0):
    limit = min(max(limit,1),100)
    query = select(models.Consultation).order_by(models.Consultation.created_at.desc()).limit(limit).offset(max(offset,0))
    if user.role == "patient":
        query = query.where(models.Consultation.patient_id == user.id)
    elif user.role == "doctor":
        doctor = db.scalar(select(models.Doctor).where(models.Doctor.user_id == user.id))
        if not doctor:
            return []
        query = query.where(models.Consultation.doctor_id == doctor.id)
    return list(db.scalars(query).all())

@app.patch("/consultations/{consultation_id}/status", response_model=schemas.ConsultationOut, tags=["consultations"])
def update_consultation_status(consultation_id: int, payload: schemas.ConsultationStatusIn,
                               db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    consultation = db.scalar(select(models.Consultation).where(
        models.Consultation.id == consultation_id).with_for_update())
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    doctor = db.scalar(select(models.Doctor).where(models.Doctor.user_id == user.id)) if user.role == "doctor" else None
    if user.role not in ("admin",) and consultation.patient_id != user.id and (not doctor or doctor.id != consultation.doctor_id):
        raise HTTPException(status_code=403, detail="Not permitted to update this consultation")
    transitions = {
        "booked":{"confirmed","cancelled"},
        "confirmed":{"in_progress","cancelled","no_show"},
        "in_progress":{"completed"},
        "completed":set(), "cancelled":set(), "no_show":set()
    }
    if payload.status not in transitions.get(consultation.status,set()):
        raise HTTPException(status_code=409, detail=f"Invalid transition: {consultation.status} -> {payload.status}")
    old_status = consultation.status
    consultation.status = payload.status
    if payload.status == "cancelled":
        slot = db.get(models.AvailabilitySlot, consultation.slot_id)
        if slot and slot.starts_at > datetime.now(timezone.utc):
            slot.is_available = True
    audit(db, user.id, "consultation.status_changed", "consultation", consultation.id,
          {"from":old_status,"to":payload.status})
    db.commit()
    db.refresh(consultation)
    return consultation

@app.post("/consultations/{consultation_id}/prescriptions", response_model=schemas.PrescriptionOut, status_code=201, tags=["prescriptions"])
def create_prescription(consultation_id: int, payload: schemas.PrescriptionIn,
                        db: Session = Depends(get_db), user: models.User = Depends(require_roles("doctor"))):
    doctor = db.scalar(select(models.Doctor).where(models.Doctor.user_id == user.id))
    consultation = db.get(models.Consultation, consultation_id)
    if not doctor or not consultation or consultation.doctor_id != doctor.id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if consultation.status != "completed":
        raise HTTPException(status_code=409, detail="Prescription allowed only after consultation completion")
    prescription = models.Prescription(consultation_id=consultation.id, doctor_id=doctor.id,
        medication_json=json.dumps(payload.medication, separators=(",",":")), instructions=payload.instructions)
    db.add(prescription)
    audit(db, user.id, "prescription.created", "prescription", "pending",
          {"consultation_id":consultation.id})
    try:
        db.commit()
        db.refresh(prescription)
        return prescription
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Prescription already exists")

@app.get("/consultations/{consultation_id}/prescription", response_model=schemas.PrescriptionOut, tags=["prescriptions"])
def get_prescription(consultation_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    consultation = db.get(models.Consultation, consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    doctor = db.scalar(select(models.Doctor).where(models.Doctor.user_id == user.id)) if user.role == "doctor" else None
    if user.role != "admin" and user.id != consultation.patient_id and (not doctor or doctor.id != consultation.doctor_id):
        raise HTTPException(status_code=403, detail="Not permitted")
    prescription = db.scalar(select(models.Prescription).where(models.Prescription.consultation_id == consultation_id))
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription

@app.get("/admin/analytics", tags=["admin"])
def admin_analytics(db: Session = Depends(get_db), admin: models.User = Depends(require_roles("admin"))):
    counts = dict(db.execute(select(models.Consultation.status, func.count()).group_by(models.Consultation.status)).all())
    return {"consultations_by_status":counts,
            "total_users":db.scalar(select(func.count()).select_from(models.User)),
            "total_doctors":db.scalar(select(func.count()).select_from(models.Doctor)),
            "total_prescriptions":db.scalar(select(func.count()).select_from(models.Prescription))}

@app.get("/admin/audit-logs", tags=["admin"])
def audit_logs(limit: int = 100, offset: int = 0, db: Session = Depends(get_db),
               admin: models.User = Depends(require_roles("admin"))):
    limit = min(max(limit,1),200)
    rows = db.scalars(select(models.AuditLog).order_by(models.AuditLog.created_at.desc()).offset(max(offset,0)).limit(limit)).all()
    return [{"id":r.id,"actor_user_id":r.actor_user_id,"action":r.action,"resource_type":r.resource_type,
             "resource_id":r.resource_id,"created_at":r.created_at} for r in rows]
