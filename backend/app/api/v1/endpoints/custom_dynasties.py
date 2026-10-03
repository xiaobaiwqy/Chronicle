"""自定义朝代/国家接口。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.crud import custom_dynasty as crud
from app.db.session import get_db

router = APIRouter()


@router.get("", response_model=list[schemas.CustomDynasty])
def list_custom_dynasties(db: Session = Depends(get_db)):
    return crud.list_custom_dynasties(db)


@router.post("", response_model=schemas.CustomDynasty, status_code=status.HTTP_201_CREATED)
def create_custom_dynasty(data: schemas.CustomDynastyCreate, db: Session = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="朝代/国家名不能为空")
    if crud.get_custom_dynasty_by_name(db, name):
        raise HTTPException(status_code=409, detail="该朝代/国家已存在")
    return crud.create_custom_dynasty(db, schemas.CustomDynastyCreate(name=name, color=data.color, start_year=data.start_year, end_year=data.end_year))


@router.put("/{dynasty_id}", response_model=schemas.CustomDynasty)
def update_custom_dynasty(dynasty_id: int, data: schemas.CustomDynastyUpdate, db: Session = Depends(get_db)):
    dynasty = crud.get_custom_dynasty(db, dynasty_id)
    if not dynasty:
        raise HTTPException(status_code=404, detail="朝代/国家不存在")
    # 改名时检查是否与其它记录重名
    if data.name is not None and data.name.strip():
        dup = crud.get_custom_dynasty_by_name(db, data.name.strip())
        if dup and dup.id != dynasty_id:
            raise HTTPException(status_code=409, detail="该朝代/国家已存在")
    return crud.update_custom_dynasty(db, dynasty, data)


@router.delete("/{dynasty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_dynasty(dynasty_id: int, db: Session = Depends(get_db)):
    dynasty = crud.get_custom_dynasty(db, dynasty_id)
    if not dynasty:
        raise HTTPException(status_code=404, detail="朝代/国家不存在")
    crud.delete_custom_dynasty(db, dynasty)
