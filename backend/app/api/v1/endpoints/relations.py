"""关系接口。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.crud import person as person_crud
from app.crud import relation as crud
from app.db.session import get_db
from app.services.serializers import relation_to_schema

router = APIRouter()


@router.get("", response_model=list[schemas.Relation])
def list_relations(db: Session = Depends(get_db)):
    return [relation_to_schema(r) for r in crud.list_relations(db)]


@router.post("", response_model=schemas.Relation, status_code=status.HTTP_201_CREATED)
def create_relation(data: schemas.RelationCreate, db: Session = Depends(get_db)):
    missing = [pid for pid in (data.from_person_id, data.to_person_id) if person_crud.get_person(db, pid) is None]
    if missing:
        raise HTTPException(status_code=422, detail=f"关系人物不存在: {missing}")
    return relation_to_schema(crud.create_relation(db, data))


@router.put("/{relation_id}", response_model=schemas.Relation)
def update_relation(relation_id: int, data: schemas.RelationUpdate, db: Session = Depends(get_db)):
    r = crud.get_relation(db, relation_id)
    if not r:
        raise HTTPException(status_code=404, detail="关系不存在")
    missing = [pid for pid in (data.from_person_id, data.to_person_id) if person_crud.get_person(db, pid) is None]
    if missing:
        raise HTTPException(status_code=422, detail=f"关系人物不存在: {missing}")
    return relation_to_schema(crud.update_relation(db, r, data))


@router.delete("/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relation(relation_id: int, db: Session = Depends(get_db)):
    r = crud.get_relation(db, relation_id)
    if not r:
        raise HTTPException(status_code=404, detail="关系不存在")
    crud.delete_relation(db, r)
