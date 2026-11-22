from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    user_id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    email = __import__("sqlalchemy").Column(String(255), nullable=False, unique=True, index=True)
    password_hash = __import__("sqlalchemy").Column(String(255), nullable=False)
    role = __import__("sqlalchemy").Column(String(20), nullable=False, default="student")
    is_active = __import__("sqlalchemy").Column(Boolean, nullable=False, default=True)
    created_at = __import__("sqlalchemy").Column(DateTime, default=datetime.utcnow, nullable=False)
    student = relationship("Student", back_populates="user", uselist=False)

class Student(Base):
    __tablename__ = "students"
    student_id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    user_id = __import__("sqlalchemy").Column(Integer, ForeignKey("users.user_id"), nullable=True, unique=True, index=True)
    name = __import__("sqlalchemy").Column(String(120), nullable=False)
    email = __import__("sqlalchemy").Column(String(255), nullable=True, index=True)
    created_at = __import__("sqlalchemy").Column(DateTime, default=datetime.utcnow, nullable=False)
    user = relationship("User", back_populates="student")
    academic_records = relationship("AcademicRecord", back_populates="student", cascade="all, delete-orphan")
    class_statuses = relationship("ClassStatus", back_populates="student", cascade="all, delete-orphan")
    backgrounds = relationship("StudentBackground", back_populates="student", cascade="all, delete-orphan")
    predictions = relationship("PlacementPrediction", back_populates="student", cascade="all, delete-orphan")

class AcademicRecord(Base):
    __tablename__ = "academic_records"
    record_id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    student_id = __import__("sqlalchemy").Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    previous_score = __import__("sqlalchemy").Column(Float, nullable=False)
    math_score = __import__("sqlalchemy").Column(Float, nullable=True)
    reading_score = __import__("sqlalchemy").Column(Float, nullable=True)
    writing_score = __import__("sqlalchemy").Column(Float, nullable=True)
    created_at = __import__("sqlalchemy").Column(DateTime, default=datetime.utcnow, nullable=False)
    student = relationship("Student", back_populates="academic_records")

class ClassStatus(Base):
    __tablename__ = "class_status"
    class_record_id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    student_id = __import__("sqlalchemy").Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    attendance = __import__("sqlalchemy").Column(Float, nullable=False)
    study_hours = __import__("sqlalchemy").Column(Float, nullable=False)
    sleep_hours = __import__("sqlalchemy").Column(Float, nullable=False)
    internet_usage = __import__("sqlalchemy").Column(Float, nullable=False)
    assignments_completed = __import__("sqlalchemy").Column(Integer, nullable=False)
    created_at = __import__("sqlalchemy").Column(DateTime, default=datetime.utcnow, nullable=False)
    student = relationship("Student", back_populates="class_statuses")

class StudentBackground(Base):
    __tablename__ = "student_background"
    background_id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    student_id = __import__("sqlalchemy").Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    gender = __import__("sqlalchemy").Column(String(30), nullable=True)
    group_name = __import__("sqlalchemy").Column(String(30), nullable=True)
    parental_education = __import__("sqlalchemy").Column(String(120), nullable=True)
    extracurricular_activities = __import__("sqlalchemy").Column(Boolean, nullable=True)
    learning_disabilities = __import__("sqlalchemy").Column(Boolean, nullable=True)
    student = relationship("Student", back_populates="backgrounds")

class PlacementPrediction(Base):
    __tablename__ = "placement_predictions"
    prediction_id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    student_id = __import__("sqlalchemy").Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    predicted_status = __import__("sqlalchemy").Column(String(30), nullable=False)
    placement_probability = __import__("sqlalchemy").Column(Float, nullable=True)
    model_version = __import__("sqlalchemy").Column(String(80), nullable=False, default="random-forest-v1")
    actual_placement_status = __import__("sqlalchemy").Column(String(30), nullable=True)
    recommendations = __import__("sqlalchemy").Column(Text, nullable=True)
    prediction_date = __import__("sqlalchemy").Column(DateTime, default=datetime.utcnow, nullable=False)
    student = relationship("Student", back_populates="predictions")
