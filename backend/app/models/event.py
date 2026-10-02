"""事件模型,以及事件-人物的多对多关联(带 role)。"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    year_start = Column(Integer, nullable=False)
    year_end = Column(Integer, nullable=False)
    dynasty = Column(String, default="")
    location = Column(String, nullable=True)

    participants = relationship(
        "EventPerson",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventPerson.id",
    )


class EventPerson(Base):
    """事件-人物关联,role 如"主将/主谋/被害"。"""
    __tablename__ = "event_persons"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    role = Column(String, default="")

    event = relationship("Event", back_populates="participants")
    person = relationship("Person", back_populates="event_links")
