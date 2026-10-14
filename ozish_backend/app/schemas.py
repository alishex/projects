import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None
    height_cm: Optional[float] = None
    target_weight_kg: Optional[float] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: Optional[str] = None
    height_cm: Optional[float] = None
    target_weight_kg: Optional[float] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class FoodLogCreate(BaseModel):
    description: str
    meal_type: Optional[str] = None
    logged_at: Optional[dt.datetime] = None


class FoodLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    meal_type: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    logged_at: dt.datetime


class WeightLogCreate(BaseModel):
    weight_kg: float
    logged_at: Optional[dt.datetime] = None


class WeightLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    weight_kg: float
    logged_at: dt.datetime


class WorkoutCreate(BaseModel):
    name: str
    duration_min: Optional[int] = None
    calories_burned: Optional[float] = None
    notes: Optional[str] = None
    logged_at: Optional[dt.datetime] = None


class WorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    duration_min: Optional[int] = None
    calories_burned: Optional[float] = None
    notes: Optional[str] = None
    logged_at: dt.datetime


class PushTokenIn(BaseModel):
    expo_push_token: str


class ReminderIn(BaseModel):
    label: str
    time_of_day: str
    enabled: bool = True


class ReminderOut(ReminderIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CoachChatIn(BaseModel):
    message: str


class CoachChatOut(BaseModel):
    reply: str
