"""自定义朝代/国家 schema。"""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CustomDynastyBase(BaseModel):
    name: str
    color: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class CustomDynastyCreate(CustomDynastyBase):
    pass


class CustomDynastyUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class CustomDynasty(CustomDynastyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
