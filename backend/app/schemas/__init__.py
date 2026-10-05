"""schema 统一导出。"""
from app.schemas.avatar import AvatarOption
from app.schemas.custom_dynasty import (
    CustomDynasty,
    CustomDynastyCreate,
    CustomDynastyUpdate,
)
from app.schemas.event import (
    Event,
    EventCreate,
    EventParticipant,
    EventUpdate,
    ParticipantIn,
)
from app.schemas.person import Person, PersonCreate, PersonUpdate
from app.schemas.person_detail import PersonDetail
from app.schemas.relation import DetailRelation, Relation, RelationCreate, RelationUpdate

__all__ = [
    "AvatarOption",
    "CustomDynasty", "CustomDynastyCreate", "CustomDynastyUpdate",
    "Event", "EventCreate", "EventParticipant", "EventUpdate", "ParticipantIn",
    "Person", "PersonCreate", "PersonUpdate", "PersonDetail",
    "DetailRelation", "Relation", "RelationCreate", "RelationUpdate",
]
