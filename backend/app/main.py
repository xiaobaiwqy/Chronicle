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


@app.get("/")
def root():
    return {"app": "Chronicle 人物志", "docs": "/docs", "api": "/api/v1"}


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("CHRONICLE_PORT", config.PORT))
    uvicorn.run(app, host=config.HOST, port=port)
