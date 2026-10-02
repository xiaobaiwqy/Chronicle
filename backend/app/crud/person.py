"""人物 CRUD。"""
import json

from sqlalchemy.orm import Session

from app import models, schemas


def list_persons(db: Session):
    return db.query(models.Person).order_by(models.Person.id).all()


def get_person(db: Session, person_id: int):
    return db.query(models.Person).filter(models.Person.id == person_id).first()


def get_person_by_name(db: Session, name: str):
    return db.query(models.Person).filter(models.Person.name == name).first()


def create_person(db: Session, data: schemas.PersonCreate) -> models.Person:
    person = models.Person(
        name=data.name,
        dynasty=data.dynasty or "",
        birth_year=data.birth_year,
        death_year=data.death_year,
        summary=data.summary or "",
        identity=data.identity or "",
        color=data.color or "",
        avatar=data.avatar or "",
        secondary_dynasties=json.dumps(data.secondary_dynasties or []),
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def update_person(db: Session, person: models.Person, data: schemas.PersonUpdate) -> models.Person:
    # 用 model_fields_set 区分“未提供”与“显式置 null”,使可空字段(birth_year/death_year 等)能被清空。
    for field in ("name", "dynasty", "birth_year", "death_year", "summary", "identity", "color", "avatar", "secondary_dynasties"):
        if field not in data.model_fields_set:
            continue
        value = getattr(data, field)
        if field == "name" and value is None:
            continue  # name 非空,忽略显式 null
        if field == "secondary_dynasties":
            value = json.dumps(value or [])
        setattr(person, field, value)
    db.commit()
    db.refresh(person)
    return person


def delete_person(db: Session, person: models.Person) -> None:
    """删除人物,并级联清理关联数据:事件参与记录、以该人物为任一端的关系。

    先显式删除关联行,避免留下脏数据;再删除人物本身。
    """
    db.query(models.EventPerson).filter(
        models.EventPerson.person_id == person.id
    ).delete(synchronize_session=False)
    db.query(models.Relation).filter(
        (models.Relation.from_person_id == person.id)
        | (models.Relation.to_person_id == person.id)
    ).delete(synchronize_session=False)
    db.delete(person)
    db.commit()
