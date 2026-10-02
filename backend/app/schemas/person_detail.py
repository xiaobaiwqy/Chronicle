"""人物详情 schema:人物 + 其事件 + 其关系。"""
from typing import List

from pydantic import BaseModel

from app.schemas.event import Event
from app.schemas.person import Person
from app.schemas.relation import DetailRelation


class PersonDetail(BaseModel):
    person: Person
    events: List[Event]
    relations: List[DetailRelation]
