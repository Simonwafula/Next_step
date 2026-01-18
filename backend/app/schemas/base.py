from pydantic import BaseModel
from typing import Optional, List

class JobPostOut(BaseModel):
    id: int
    title: str
    organization: Optional[str] = None
    location: Optional[str] = None
    url: str
    why_match: Optional[str] = None

class RecommendOut(BaseModel):
    target_role: str
    overlap: float
    gap_skills: List[str]
