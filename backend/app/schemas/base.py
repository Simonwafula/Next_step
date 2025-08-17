from pydantic import BaseModel
from typing import Optional, List

class JobPostOut(BaseModel):
    id: int
    title: str
    organization: str | None = None
    location: str | None = None
    url: str
    why_match: str | None = None

class RecommendOut(BaseModel):
    target_role: str
    overlap: float
    gap_skills: list[str]
