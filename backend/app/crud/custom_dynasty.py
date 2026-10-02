"""自定义朝代/国家 CRUD。"""
from sqlalchemy.orm import Session

from app import models, schemas


def list_custom_dynasties(db: Session):
    return db.query(models.CustomDynasty).order_by(models.CustomDynasty.id).all()


def get_custom_dynasty(db: Session, dynasty_id: int):
    return db.query(models.CustomDynasty).filter(models.CustomDynasty.id == dynasty_id).first()


def get_custom_dynasty_by_name(db: Session, name: str):
    return db.query(models.CustomDynasty).filter(models.CustomDynasty.name == name).first()


def create_custom_dynasty(db: Session, data: schemas.CustomDynastyCreate) -> models.CustomDynasty:
    dynasty = models.CustomDynasty(name=data.name, color=data.color or "")
    db.add(dynasty)
    db.commit()
    db.refresh(dynasty)
    return dynasty


def update_custom_dynasty(db: Session, dynasty: models.CustomDynasty, data: schemas.CustomDynastyUpdate) -> models.CustomDynasty:
    if data.name is not None and data.name.strip():
        dynasty.name = data.name.strip()
    if data.color is not None:
        dynasty.color = data.color
    db.commit()
    db.refresh(dynasty)
    return dynasty


def delete_custom_dynasty(db: Session, dynasty: models.CustomDynasty) -> None:
    db.delete(dynasty)
    db.commit()
