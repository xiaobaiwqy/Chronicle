"""统一导出 ORM 模型,便于 main.py 导入以注册表。"""
from app.models.custom_dynasty import CustomDynasty
from app.models.event import Event, EventPerson
from app.models.person import Person
from app.models.relation import Relation

__all__ = ["Person", "Event", "EventPerson", "Relation", "CustomDynasty"]
