"""关系网/时间线所需数据组装。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import person as person_crud
from app.crud import relation as relation_crud
from app.db.session import get_db
from app.services.serializers import person_to_schema

router = APIRouter()


@router.get("")
def get_graph(db: Session = Depends(get_db)):
    """返回 3D 关系网所需数据:nodes(人物)+ edges(关系)。"""
    persons = person_crud.list_persons(db)
    relations = relation_crud.list_relations(db)
    return {
        "nodes": [person_to_schema(p) for p in persons],
        "edges": [
            {"id": r.id, "from": r.from_person_id, "to": r.to_person_id, "label": r.label, "directed": r.directed}
            for r in relations
        ],
    }
