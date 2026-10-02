"""事件接口。"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import schemas
from app.crud import event as crud
from app.crud import person as person_crud
from app.db.session import get_db
from app.services.serializers import event_to_schema

router = APIRouter()


def _validate_participants(db: Session, participants) -> None:
    missing = [p.person_id for p in participants if person_crud.get_person(db, p.person_id) is None]
    if missing:
        raise HTTPException(status_code=422, detail=f"参与者人物不存在: {missing}")


@router.get("", response_model=list[schemas.Event])
def list_events(db: Session = Depends(get_db)):
    return [event_to_schema(e) for e in crud.list_events(db)]


@router.post("", response_model=schemas.Event, status_code=status.HTTP_201_CREATED)
def create_event(data: schemas.EventCreate, db: Session = Depends(get_db)):
    _validate_participants(db, data.participants)
    return event_to_schema(crud.create_event(db, data))


@router.get("/timeline", response_model=list[schemas.Event])
def get_timeline(
    from_: Optional[int] = Query(None, alias="from"),
    to: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return [event_to_schema(e) for e in crud.list_timeline(db, from_, to)]


@router.get("/{event_id}", response_model=schemas.Event)
def get_event(event_id: int, db: Session = Depends(get_db)):
    e = crud.get_event(db, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="事件不存在")
    return event_to_schema(e)


@router.put("/{event_id}", response_model=schemas.Event)
def update_event(event_id: int, data: schemas.EventUpdate, db: Session = Depends(get_db)):
    e = crud.get_event(db, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="事件不存在")
    if data.participants is not None:
        _validate_participants(db, data.participants)
    return event_to_schema(crud.update_event(db, e, data))


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    e = crud.get_event(db, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="事件不存在")
    crud.delete_event(db, e)
