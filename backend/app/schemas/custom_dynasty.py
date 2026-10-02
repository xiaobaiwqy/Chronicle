"""自定义朝代/国家 schema。"""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CustomDynastyBase(BaseModel):
    name: str
    color: str = ""


class CustomDynastyCreate(CustomDynastyBase):
    pass


class CustomDynastyUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class CustomDynasty(CustomDynastyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
