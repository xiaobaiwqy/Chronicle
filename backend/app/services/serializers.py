"""ORM -> schema 序列化(读模型组装)。"""
import json

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.services import avatars


def person_to_schema(p: models.Person) -> schemas.Person:
    return schemas.Person(
        id=p.id,
        name=p.name,
        dynasty=p.dynasty or "",
        birth_year=p.birth_year,
        death_year=p.death_year,
        summary=p.summary or "",
        identity=p.identity or "",
        color=p.color or "",
        avatar=p.avatar or "",
        secondary_dynasties=_load_dynasties(p.secondary_dynasties),
        avatar_url=avatars.resolve_avatar(p.avatar or "", p.name),
    )


def _load_dynasties(raw) -> list[str]:
    """次朝代/国家 JSON 字符串 -> list,空/异常回落 []。"""
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except (TypeError, ValueError):
        return []


def event_to_schema(e: models.Event) -> schemas.Event:
    participants = [
        schemas.EventParticipant(
            person_id=link.person.id,
            role=link.role or "",
            name=link.person.name,
            color=link.person.color or "",
            dynasty=link.person.dynasty or "",
        )
        for link in sorted(e.participants, key=lambda x: x.id)
    ]
    return schemas.Event(
        id=e.id,
        title=e.title,
        description=e.description or "",
        year_start=e.year_start,
        year_end=e.year_end,
        dynasty=e.dynasty or "",
        location=e.location,
        participants=participants,
    )


def relation_to_schema(r: models.Relation) -> schemas.Relation:
    return schemas.Relation(
        id=r.id,
        from_person_id=r.from_person_id,
        to_person_id=r.to_person_id,
        label=r.label or "",
        directed=r.directed,
    )


def person_detail_to_schema(db: Session, person: models.Person) -> schemas.PersonDetail:
    events = (
        db.query(models.Event)
        .join(models.EventPerson)
        .filter(models.EventPerson.person_id == person.id)
        .order_by(models.Event.year_start.is_(None), models.Event.year_start, models.Event.id)
        .all()
    )
    relations = (
        db.query(models.Relation)
        .filter(or_(
            models.Relation.from_person_id == person.id,
            models.Relation.to_person_id == person.id,
        ))
        .order_by(models.Relation.id)
        .all()
    )
    rel_schemas = []
    for r in relations:
        other = r.to_person if r.from_person_id == person.id else r.from_person
        rel_schemas.append(schemas.DetailRelation(
            id=r.id,
            from_person_id=r.from_person_id,
            to_person_id=r.to_person_id,
            label=r.label or "",
            directed=r.directed,
            other_id=other.id,
            other_name=other.name,
            other_color=other.color or "",
        ))
    return schemas.PersonDetail(
        person=person_to_schema(person),
        events=[event_to_schema(e) for e in events],
        relations=rel_schemas,
    )
