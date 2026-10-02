"""自定义朝代/国家模型:用户在筛选框直接管理的朝代,独立于内置目录。"""
from sqlalchemy import Column, Integer, String

from app.db.base import Base


class CustomDynasty(Base):
    __tablename__ = "custom_dynasties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    color = Column(String, default="")
