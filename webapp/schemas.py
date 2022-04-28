from typing import List, Optional
from pydantic import BaseModel


class Job(BaseModel):
    id: int = 0
    own_id: int

    class Config:
        orm_mode = True


class User(BaseModel):
    id: int = 0
    user_name: str
    password: str
    skills: str
    jobs: List[Job] = []

    class Config:
        orm_mode = True


class UserOut(BaseModel):
    id: int = 0
    user_name: str
    skills: str
    jobs: List[Job] = []

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    skills: str

    class Config:
        orm_mode = True


class Image(BaseModel):
    id: int = 0
    created_at: str
    url: str
    is_reference: bool

    job: Job = None
    job_id: int

    class Config:
        orm_mode = True


class Result(BaseModel):
    id: int = 0
    created_at: str
    url: str

    job: Job = None
    job_id: int

    class Config:
        orm_mode = True