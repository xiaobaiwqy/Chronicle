"""人物模型。"""
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    dynasty = Column(String, default="")
    secondary_dynasties = Column(Text, default="[]")  # 次朝代/国家(JSON 数组字符串);主朝代仍用 dynasty
    birth_year = Column(Integer, nullable=True)   # 负数 = 公元前
    death_year = Column(Integer, nullable=True)
    summary = Column(Text, default="")
    identity = Column(String, default="")  # 身份/头衔,如 君主、名将、丞相
    color = Column(String, default="")  # 空 = 跟随朝代色(前端按 dynasty 计算),非空 = 手动覆盖
    avatar = Column(Text, default="")  # 自定义头像(data URL),空 = 用姓名首字

    event_links = relationship(
        "EventPerson", back_populates="person", cascade="all, delete-orphan"
    )
    out_relations = relationship(
        "Relation", foreign_keys="Relation.from_person_id",
        back_populates="from_person", cascade="all, delete-orphan",
    )
    in_relations = relationship(
        "Relation", foreign_keys="Relation.to_person_id",
        back_populates="to_person", cascade="all, delete-orphan",
    )
