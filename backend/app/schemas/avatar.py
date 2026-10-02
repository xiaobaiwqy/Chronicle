"""默认头像库 schema。"""
from pydantic import BaseModel


class AvatarOption(BaseModel):
    """一个可选的默认头像:名字(不含扩展名)与其访问 URL。"""
    name: str
    url: str
