from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import List, Optional
from pydantic_ai import AIModel

class JobBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company: str = Field(..., min_length=1, max_length=200)
    description: str
    location: str = Field(..., min_length=1, max_length=200)
    job_type: str = Field(..., min_length=1, max_length=50)
    salary_range: Optional[str] = Field(None, max_length=100)
    url: HttpUrl
    source: str = Field(..., min_length=1, max_length=50)
    requirements: List[str] = Field(default_factory=list)

class JobCreate(JobBase):
    posted_date: datetime
    status: str = Field(default="active", pattern="^(active|filled|expired)$")

class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    company: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    job_type: Optional[str] = Field(None, min_length=1, max_length=50)
    salary_range: Optional[str] = Field(None, max_length=100)
    url: Optional[HttpUrl] = None
    source: Optional[str] = Field(None, min_length=1, max_length=50)
    requirements: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(active|filled|expired)$")

class Job(JobBase):
    id: int
    posted_date: datetime
    scraped_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobSearchBase(BaseModel):
    keywords: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=200)
    job_type: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: bool = True

class JobSearchCreate(JobSearchBase):
    pass

class JobSearchUpdate(BaseModel):
    keywords: Optional[str] = Field(None, min_length=1, max_length=200)
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    job_type: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None

class JobSearch(JobSearchBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobMatch(AIModel):
    """AI-powered job matching model"""
    job_id: int
    user_id: int
    match_score: float = Field(..., ge=0.0, le=1.0)
    matching_skills: List[str]
    missing_skills: List[str]
    recommendations: List[str]

    class Config:
        from_attributes = True 