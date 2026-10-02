"""全局配置:数据库路径、头像库、前端静态资源等。

区分两种运行模式:
- 开发模式(源码直接跑):数据在 backend/local_data/,前端由 `nuxt dev` 提供。
- 打包模式(PyInstaller 冻结,sys.frozen 为 True):只读资源(默认头像库、前端静态文件)
  从 sys._MEIPASS 解压目录读取;可写数据(SQLite)走环境变量 CHRONICLE_DATA_DIR,
  由 Electron 主进程传入用户数据目录。
"""
import os
import sys
from pathlib import Path

# app/ 目录
BASE_DIR = Path(__file__).resolve().parent.parent

# backend/ 根目录(config.py 在 backend/app/core/ 下)
BACKEND_DIR = BASE_DIR.parent

# 是否打包运行(PyInstaller)
FROZEN = bool(getattr(sys, "frozen", False))
MEIPASS = getattr(sys, "_MEIPASS", None)

# 可写数据目录:优先环境变量(Electron 传入用户数据目录),否则开发模式用 backend/local_data
DATA_DIR = Path(os.environ.get("CHRONICLE_DATA_DIR", BACKEND_DIR / "local_data"))

# SQLite 数据目录,chronicle.db 存这里(自动创建)
SQLITE_DIR = DATA_DIR / "sqlite"
SQLITE_DIR.mkdir(parents=True, exist_ok=True)

# 默认头像库目录(只读资源):打包时打进二进制解压目录,开发时用 backend/local_data/avatars
if FROZEN and MEIPASS:
    AVATARS_DIR = Path(MEIPASS) / "avatars"
else:
    AVATARS_DIR = BACKEND_DIR / "local_data" / "avatars"

# 前端静态文件目录:打包时打进二进制;开发模式为 None(由 nuxt dev 提供,后端不托管)
if FROZEN and MEIPASS:
    STATIC_DIR = Path(MEIPASS) / "frontend"
else:
    STATIC_DIR = None

# SQLite 连接串。年份以整数存储,负数表示公元前。
DATABASE_URL = f"sqlite:///{SQLITE_DIR / 'chronicle.db'}"

# 服务监听
HOST = "127.0.0.1"
PORT = 8000
