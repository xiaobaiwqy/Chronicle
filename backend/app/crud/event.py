"""事件 CRUD。"""
from typing import Optional

from sqlalchemy.orm import Session

from app import models, schemas


def list_events(db: Session):
    return db.query(models.Event).order_by(models.Event.year_start, models.Event.id).all()


def get_event(db: Session, event_id: int):
    return db.query(models.Event).filter(models.Event.id == event_id).first()


def list_timeline(db: Session, from_year: Optional[int] = None, to_year: Optional[int] = None):
    q = db.query(models.Event)
    if from_year is not None:
        q = q.filter(models.Event.year_start >= from_year)
    if to_year is not None:
        q = q.filter(models.Event.year_start <= to_year)
    return q.order_by(models.Event.year_start, models.Event.id).all()


def create_event(db: Session, data: schemas.EventCreate) -> models.Event:
    event = models.Event(
        title=data.title,
        description=data.description or "",
        year_start=data.year_start,
        year_end=data.year_end,
        dynasty=data.dynasty or "",
        location=data.location,
        participants=[models.EventPerson(person_id=x.person_id, role=x.role) for x in data.participants],
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event: models.Event, data: schemas.EventUpdate) -> models.Event:
    for field in ("title", "description", "year_start", "year_end", "dynasty", "location"):
        value = getattr(data, field)
        if value is not None:
            setattr(event, field, value)
    if data.participants is not None:
        event.participants.clear()
        event.participants.extend(
            [models.EventPerson(person_id=x.person_id, role=x.role) for x in data.participants]
        )
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: models.Event) -> None:
    db.delete(event)
    db.commit()
