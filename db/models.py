"""
ORM models
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    role = Column(String(50), default="Viewer", nullable=False)
    password_hash = Column(String(256), nullable=True)
    salt = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspaces = relationship("Workspace", back_populates="owner")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="workspaces")
    variants = relationship("PrototypeVariant", back_populates="workspace")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    type = Column(String(100), nullable=False)
    status = Column(String(50), default="queued")  # queued, running, done, error
    request = Column(JSON)
    result_path = Column(String(255))
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PrototypeVariant(Base):
    __tablename__ = "prototype_variants"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    name = Column(String(150), nullable=False)
    file_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="variants")


class SecretToken(Base):
    __tablename__ = "secret_tokens"

    id = Column(Integer, primary_key=True)
    service = Column(String(50), nullable=False)  # confluence, jira
    token = Column(String(512), nullable=False)
    username = Column(String(150))
    created_at = Column(DateTime, default=datetime.utcnow)
