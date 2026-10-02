"""默认头像库接口:列出可用头像、按人物名取图。"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app import schemas
from app.services import avatars

router = APIRouter()


@router.get("", response_model=list[schemas.AvatarOption])
def list_avatars():
    return [schemas.AvatarOption(name=n, url=avatars.url_for(n)) for n in avatars.list_names()]


@router.get("/file/{name}", response_class=FileResponse)
def get_avatar_file(name: str):
    path = avatars.file_path_for(name)
    if not path:
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(path)
