import datetime as dt

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=True)
    height_cm = Column(Float, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    food_logs = relationship("FoodLog", back_populates="user", cascade="all, delete-orphan")
    weight_logs = relationship("WeightLog", back_populates="user", cascade="all, delete-orphan")
    workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    push_tokens = relationship("PushToken", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    coach_messages = relationship("CoachMessage", back_populates="user", cascade="all, delete-orphan")


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    meal_type = Column(String, nullable=True)
    calories = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    logged_at = Column(DateTime, default=dt.datetime.utcnow, index=True)

    user = relationship("User", back_populates="food_logs")


class WeightLog(Base):
    __tablename__ = "weight_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    weight_kg = Column(Float, nullable=False)
    logged_at = Column(DateTime, default=dt.datetime.utcnow, index=True)

    user = relationship("User", back_populates="weight_logs")


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    duration_min = Column(Integer, nullable=True)
    calories_burned = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    logged_at = Column(DateTime, default=dt.datetime.utcnow, index=True)

    user = relationship("User", back_populates="workouts")


class PushToken(Base):
    __tablename__ = "push_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expo_push_token = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User", back_populates="push_tokens")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    label = Column(String, nullable=False)
    time_of_day = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)

    user = relationship("User", back_populates="reminders")


class CoachMessage(Base):
    __tablename__ = "coach_messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)

    user = relationship("User", back_populates="coach_messages")
