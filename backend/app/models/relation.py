"""人物关系模型,如"君臣/父子/刺杀"。"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Relation(Base):
    __tablename__ = "relations"

    id = Column(Integer, primary_key=True, index=True)
    from_person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    to_person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    label = Column(String, default="")
    # 是否有方向性:True = 单向(from -> to),False = 双向/无向(如"同门/朋友")
    directed = Column(Boolean, default=True, nullable=False)

    from_person = relationship(
        "Person", foreign_keys=[from_person_id], back_populates="out_relations"
    )
    to_person = relationship(
        "Person", foreign_keys=[to_person_id], back_populates="in_relations"
    )
