from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=160)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    model_config = ConfigDict(from_attributes=True)

class DoctorCreate(BaseModel):
    user_id: int
    specialty: str = Field(min_length=2, max_length=120)
    bio: str | None = Field(default=None, max_length=3000)
    is_verified: bool = False

class DoctorOut(BaseModel):
    id: int
    user_id: int
    specialty: str
    bio: str | None
    is_verified: bool
    model_config = ConfigDict(from_attributes=True)

class SlotCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime

class SlotOut(BaseModel):
    id: int
    doctor_id: int
    starts_at: datetime
    ends_at: datetime
    is_available: bool
    model_config = ConfigDict(from_attributes=True)

class BookingIn(BaseModel):
    slot_id: int
    reason: str | None = Field(default=None, max_length=2000)

class ConsultationOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    slot_id: int
    status: str
    reason: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConsultationStatusIn(BaseModel):
    status: str = Field(pattern="^(confirmed|in_progress|completed|cancelled|no_show)$")

class PrescriptionIn(BaseModel):
    medication: list[dict] = Field(min_length=1, max_length=30)
    instructions: str = Field(min_length=1, max_length=5000)

class PrescriptionOut(BaseModel):
    id: int
    consultation_id: int
    doctor_id: int
    medication_json: str
    instructions: str
    model_config = ConfigDict(from_attributes=True)

class HealthOut(BaseModel):
    status: str
