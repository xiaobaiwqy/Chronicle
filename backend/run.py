"""打包入口:以 app 对象方式启动 uvicorn,供 PyInstaller 冻结为可执行文件。

源码开发时仍用 `python app/main.py` 启动;此文件仅在打包时作为 PyInstaller 入口。
"""
import os
import sys
from pathlib import Path

# 确保能找到 app 包(打包后由 PyInstaller 冻结,此行为运行时兜底)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # noqa: E402

from app.core import config  # noqa: E402
from app.main import app  # noqa: E402,F401  导入即完成 FastAPI app 与路由注册


if __name__ == "__main__":
    port = int(os.environ.get("CHRONICLE_PORT", config.PORT))
    uvicorn.run(app, host=config.HOST, port=port, log_level="info")
