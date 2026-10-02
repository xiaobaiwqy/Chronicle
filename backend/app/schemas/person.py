"""人物 schema。"""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PersonBase(BaseModel):
    name: str
    dynasty: str = ""
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    summary: str = ""
    identity: str = ""
    color: str = ""
    avatar: str = ""
    secondary_dynasties: list[str] = []


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    dynasty: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    summary: Optional[str] = None
    identity: Optional[str] = None
    color: Optional[str] = None
    avatar: Optional[str] = None
    secondary_dynasties: Optional[list[str]] = None


class Person(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    avatar_url: str = ""  # 最终展示用头像 URL(上传的 data URL / 库里选定的 / 按名匹配的默认头像)
