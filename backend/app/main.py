"""人物志 (Chronicle) FastAPI 入口。

启动即自动建表;API 前缀 /api/v1。
直接运行:python main.py / python app/main.py(端口用 CHRONICLE_PORT 覆盖)。
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 兼容以脚本方式直接运行(python main.py / python app/main.py):
# 把 backend 目录加进 sys.path,使下方的 `from app import ...` 能找到 app 包。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  确保模型注册到 Base.metadata
from app.api.v1.router import api_router
from app.core import config
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    # 轻量迁移:为已存在的 relations 表补充 directed 列(create_all 不会修改已有表)
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "relations" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("relations")}
        if "directed" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE relations ADD COLUMN directed BOOLEAN NOT NULL DEFAULT 1"))
    # 轻量迁移:为已存在的 persons 表补充 avatar/identity 列,并清理已废弃的 aliases/tags 列
    if "persons" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("persons")}
        if "avatar" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE persons ADD COLUMN avatar TEXT DEFAULT ''"))
        if "identity" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE persons ADD COLUMN identity VARCHAR DEFAULT ''"))
        if "secondary_dynasties" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE persons ADD COLUMN secondary_dynasties TEXT DEFAULT '[]'"))
        for legacy in ("aliases", "tags"):
            if legacy in cols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE persons DROP COLUMN {legacy}"))
    # 轻量迁移:让 events 表的 year_start/year_end 允许为空(事件可不填年份)。
    # SQLite 无法直接 ALTER COLUMN 去掉 NOT NULL,故重建表(列已存在且非空时执行一次)。
    if "events" in inspector.get_table_names():
        event_cols = {c["name"]: c for c in inspector.get_columns("events")}
        if event_cols.get("year_start", {}).get("nullable", True) is False:
            with engine.begin() as conn:
                conn.execute(text(
                    "CREATE TABLE events_new ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "title VARCHAR NOT NULL, "
                    "description TEXT DEFAULT '', "
                    "year_start INTEGER, "
                    "year_end INTEGER, "
                    "dynasty VARCHAR DEFAULT '', "
                    "location VARCHAR)"
                ))
                conn.execute(text(
                    "INSERT INTO events_new (id, title, description, year_start, year_end, dynasty, location) "
                    "SELECT id, title, description, year_start, year_end, dynasty, location FROM events"
                ))
                conn.execute(text("DROP TABLE events"))
                conn.execute(text("ALTER TABLE events_new RENAME TO events"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_id ON events (id)"))
    yield


app = FastAPI(title="人物志 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


# 打包模式:托管前端静态文件(单页应用),挂到根路径;开发模式:根路径返回应用信息
if config.STATIC_DIR and config.STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(config.STATIC_DIR), html=True), name="frontend")
else:

    @app.get("/")
    def root():
        return {"app": "Chronicle 人物志", "docs": "/docs", "api": "/api/v1"}


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("CHRONICLE_PORT", config.PORT))
    uvicorn.run(app, host=config.HOST, port=port)
