"""v1 路由汇总。"""
from fastapi import APIRouter

from app.api.v1.endpoints import avatars, custom_dynasties, events, graph, persons, relations

api_router = APIRouter()
api_router.include_router(persons.router, prefix="/persons", tags=["persons"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(relations.router, prefix="/relations", tags=["relations"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(custom_dynasties.router, prefix="/custom-dynasties", tags=["custom-dynasties"])
api_router.include_router(avatars.router, prefix="/avatars", tags=["avatars"])
