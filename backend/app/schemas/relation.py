"""关系 schema。"""
from pydantic import BaseModel, ConfigDict


class RelationBase(BaseModel):
    from_person_id: int
    to_person_id: int
    label: str = ""
    directed: bool = True


class RelationCreate(RelationBase):
    pass


class RelationUpdate(RelationBase):
    pass


class Relation(RelationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class DetailRelation(Relation):
    """人物详情里的关系,附带另一端人物信息,便于抽屉直接渲染。"""
    other_id: int
    other_name: str = ""
    other_color: str = ""
