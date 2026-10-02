"""关系 CRUD。"""
from sqlalchemy.orm import Session

from app import models, schemas


def list_relations(db: Session):
    return db.query(models.Relation).order_by(models.Relation.id).all()


def get_relation(db: Session, relation_id: int):
    return db.query(models.Relation).filter(models.Relation.id == relation_id).first()


def create_relation(db: Session, data: schemas.RelationCreate) -> models.Relation:
    relation = models.Relation(
        from_person_id=data.from_person_id,
        to_person_id=data.to_person_id,
        label=data.label or "",
        directed=data.directed,
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


def delete_relation(db: Session, relation: models.Relation) -> None:
    db.delete(relation)
    db.commit()
