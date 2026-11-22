from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class PredictRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    email: Optional[EmailStr] = None
    study_hours: float = Field(ge=0, le=24)
    attendance: float = Field(ge=0, le=100)
    sleep_hours: float = Field(ge=0, le=24)
    internet_usage: float = Field(ge=0, le=24)
    assignments_completed: int = Field(ge=0, le=100)
    previous_score: float = Field(ge=0, le=100)
    gender: Optional[str] = None
    group_name: Optional[str] = None
    parental_education: Optional[str] = None
    extracurricular_activities: Optional[bool] = None
    learning_disabilities: Optional[bool] = None

class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: int
    name: str
    email: Optional[str] = None
