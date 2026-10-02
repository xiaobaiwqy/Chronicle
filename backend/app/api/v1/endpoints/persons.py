"""人物接口。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.crud import person as crud
from app.db.session import get_db
from app.services.serializers import person_detail_to_schema, person_to_schema

router = APIRouter()


@router.get("", response_model=list[schemas.Person])
def list_persons(db: Session = Depends(get_db)):
    return [person_to_schema(p) for p in crud.list_persons(db)]


@router.post("", response_model=schemas.Person, status_code=status.HTTP_201_CREATED)
def create_person(data: schemas.PersonCreate, db: Session = Depends(get_db)):
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="姓名不能为空")
    if crud.get_person_by_name(db, name):
        raise HTTPException(status_code=409, detail="该人物已存在")
    data.name = name
    return person_to_schema(crud.create_person(db, data))


@router.get("/{person_id}", response_model=schemas.Person)
def get_person(person_id: int, db: Session = Depends(get_db)):
    p = crud.get_person(db, person_id)
    if not p:
        raise HTTPException(status_code=404, detail="人物不存在")
    return person_to_schema(p)


@router.get("/{person_id}/detail", response_model=schemas.PersonDetail)
def get_person_detail(person_id: int, db: Session = Depends(get_db)):
    p = crud.get_person(db, person_id)
    if not p:
        raise HTTPException(status_code=404, detail="人物不存在")
    return person_detail_to_schema(db, p)


@router.put("/{person_id}", response_model=schemas.Person)
def update_person(person_id: int, data: schemas.PersonUpdate, db: Session = Depends(get_db)):
    p = crud.get_person(db, person_id)
    if not p:
        raise HTTPException(status_code=404, detail="人物不存在")
    # 改名时检查是否与其它人物重名(排除自己)
    if data.name is not None and data.name.strip():
        name = data.name.strip()
        dup = crud.get_person_by_name(db, name)
        if dup and dup.id != person_id:
            raise HTTPException(status_code=409, detail="该人物已存在")
        data.name = name
    return person_to_schema(crud.update_person(db, p, data))


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: int, db: Session = Depends(get_db)):
    p = crud.get_person(db, person_id)
    if not p:
        raise HTTPException(status_code=404, detail="人物不存在")
    crud.delete_person(db, p)
