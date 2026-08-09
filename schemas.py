from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str):
        if not value.strip():
            raise ValueError("name must not be empty or whitespace-only")
        return value.strip()

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime
    model_config = {"from_attributes": True}

class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1)
    tag: str = Field(default="general", min_length=1)
    owner_id: int

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    content: Optional[str] = Field(default=None, min_length=1)
    tag: Optional[str] = Field(default=None, min_length=1)

class AISuggestion(BaseModel):
    tags: list[str]
    summary: str

class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    tag: str
    owner_id: int
    created_at: datetime
    ai_suggestion: Optional[AISuggestion] = None
    model_config = {"from_attributes": True}
