"""默认头像库:按人物名匹配 local_data/avatars 里的图片,并生成访问 URL。

头像文件以人物名命名(如 关羽.jpg),空头像的人物会自动按名匹配;
用户也可以在上传之外,从库里显式选定某个头像(存成库 URL)。
"""
from pathlib import Path
from urllib.parse import quote

from app.core import config

AVATARS_DIR = config.AVATARS_DIR

# 支持的图片扩展名
_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

# name -> 文件名 映射缓存:目录 mtime 变化(增删文件)时自动重建
_cache: dict = {"mtime": None, "map": {}}


def _scan() -> dict[str, str]:
    """扫描头像目录,返回 {名字: 文件名}(名字 = 去掉扩展名的文件名)。"""
    result: dict[str, str] = {}
    if not AVATARS_DIR.is_dir():
        return result
    for p in AVATARS_DIR.iterdir():
        if not p.is_file() or p.suffix.lower() not in _EXTENSIONS:
            continue
        result.setdefault(p.stem, p.name)
    return result


def name_map() -> dict[str, str]:
    """人物名 -> 文件名 映射,目录增删文件时自动刷新。"""
    try:
        mtime = AVATARS_DIR.stat().st_mtime
    except FileNotFoundError:
        mtime = None
    if _cache["mtime"] != mtime:
        _cache["map"] = _scan()
        _cache["mtime"] = mtime
    return _cache["map"]


def file_path_for(name: str) -> Path | None:
    fn = name_map().get(name)
    if not fn:
        return None
    return AVATARS_DIR / fn


def url_for(name: str) -> str:
    """给定人物名返回默认头像 URL;无匹配返回空串。"""
    if not name or not file_path_for(name):
        return ""
    return f"/api/v1/avatars/file/{quote(name)}"


def list_names() -> list[str]:
    return sorted(name_map().keys())


def resolve_avatar(avatar: str, name: str) -> str:
    """人物头像的最终展示 URL。

    - avatar 非空(上传的 data URL,或从库里选定的库 URL)时原样返回;
    - avatar 为空时按人物名匹配默认头像库;
    - 都无则空串(前端回落为姓名首字)。
    """
    a = (avatar or "").strip()
    if a:
        return a
    return url_for(name)
