"""事件 schema。"""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ParticipantIn(BaseModel):
    """写入事件时的参与者:{person_id, role}。"""
    person_id: int
    role: str = ""


class EventParticipant(BaseModel):
    """事件参与者(已联表带出人物展示信息)。"""
    person_id: int
    role: str = ""
    name: str = ""
    color: str = ""
    dynasty: str = ""


class EventBase(BaseModel):
    title: str
    description: str = ""
    year_start: int
    year_end: int
    dynasty: str = ""
    location: Optional[str] = None


class EventCreate(EventBase):
    participants: List[ParticipantIn] = []


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    dynasty: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[List[ParticipantIn]] = None


class Event(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    participants: List[EventParticipant] = []
