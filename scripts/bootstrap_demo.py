"""Create synthetic local demo accounts. Run only against a disposable local database."""
from app.db import Base, SessionLocal, engine
from app.models import User, Profile, Doctor
from app.security import hash_password

DEMO_PASSWORD = "Demo-Only-Password-2026!"


def get_or_create_user(db, email, role, name):
    user = db.query(User).filter(User.email == email).one_or_none()
    if user:
        user.role = role
        return user
    user = User(email=email, password_hash=hash_password(DEMO_PASSWORD), role=role, is_active=True)
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, full_name=name))
    db.flush()
    return user


def main():
    print("WARNING: use only with a disposable local/demo database; synthetic accounts only.")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        admin = get_or_create_user(db, "admin.demo@example.com", "admin", "Demo Admin")
        doctor_user = get_or_create_user(db, "doctor.demo@example.com", "doctor", "Demo Doctor")
        get_or_create_user(db, "patient.demo@example.com", "patient", "Demo Patient")
        doctor = db.query(Doctor).filter(Doctor.user_id == doctor_user.id).one_or_none()
        if not doctor:
            doctor = Doctor(user_id=doctor_user.id, specialty="General Medicine",
                            bio="Synthetic demo profile. Not a real clinician.", is_verified=True)
            db.add(doctor)
        db.commit()
        print(f"Demo accounts ready. Shared demo password: {DEMO_PASSWORD}")
        print(f"Doctor profile id: {doctor.id}")
        print("Do not use these credentials outside a local disposable environment.")


if __name__ == "__main__":
    main()
