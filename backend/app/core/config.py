"""全局配置:数据库路径等。"""
from pathlib import Path

# app/ 目录
BASE_DIR = Path(__file__).resolve().parent.parent

# backend/ 根目录(config.py 在 backend/app/core/ 下)
BACKEND_DIR = BASE_DIR.parent

# SQLite 数据目录(backend/local_data/sqlite,不入库),chronicle.db 存这里
SQLITE_DIR = BACKEND_DIR / "local_data" / "sqlite"
SQLITE_DIR.mkdir(parents=True, exist_ok=True)

# 本地数据目录(local_data):SQLite、默认头像库等
LOCAL_DATA_DIR = BACKEND_DIR / "local_data"

# 默认头像库目录:按人物名命名的图片(如 关羽.jpg),空头像时自动匹配
AVATARS_DIR = LOCAL_DATA_DIR / "avatars"

# SQLite 连接串。年份以整数存储,负数表示公元前。
DATABASE_URL = f"sqlite:///{SQLITE_DIR / 'chronicle.db'}"

# 服务监听
HOST = "127.0.0.1"
PORT = 8000
