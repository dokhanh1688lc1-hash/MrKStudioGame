from __future__ import annotations

from datetime import datetime

from sqlalchemy import (Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, UTCDateTime, utcnow

PROJECT_STATUSES = ["Research", "Concept", "Pre-production", "Prototype", "Production", "QA",
                    "Release Preparation", "Live Operations", "Paused", "Archived"]
TASK_STATUSES = ["Pending", "Planned", "Assigned", "Running", "Blocked", "Awaiting Approval",
                 "Completed", "Failed", "Cancelled"]
ROLES = ["owner", "manager", "viewer"]
BUDGET_SCOPES = ["studio", "project", "department", "provider", "model", "task"]
BUDGET_PERIODS = ["daily", "monthly", "total"]


def _in(col: str, values: list[str]) -> str:
    return f"{col} IN (" + ",".join(f"'{v}'" for v in values) + ")"


class Stamped:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class User(Base, Stamped):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="viewer")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint(_in("role", ROLES), name="ck_user_role"),)


class Project(Base, Stamped):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[str] = mapped_column(String(80), default="")
    platform: Mapped[str] = mapped_column(String(80), default="")
    target_market: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(32), default="Research")
    workspace_path: Mapped[str] = mapped_column(String(300), default="")
    source_type: Mapped[str] = mapped_column(String(16), default="")      # "", zip, github, folder
    source_ref: Mapped[str] = mapped_column(String(500), default="")      # URL repo hoặc đường dẫn thư mục
    source_branch: Mapped[str] = mapped_column(String(100), default="")
    source_synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    allow_write: Mapped[bool] = mapped_column(Boolean, default=False)   # cho phép ghi vào thư mục gốc trên máy
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")
    __table_args__ = (CheckConstraint(_in("status", PROJECT_STATUSES), name="ck_project_status"),)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    preferred_provider: Mapped[str] = mapped_column(String(20), default="openai")
    agents: Mapped[list["Agent"]] = relationship(back_populates="department")


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(120))
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    department: Mapped[Department] = relationship(back_populates="agents")


class ProviderConfig(Base):
    """Cấu hình provider chạy trên máy (Claude Code / Codex / nội bộ). Không có API key."""
    __tablename__ = "provider_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    default_model: Mapped[str] = mapped_column(String(120), default="")
    allow_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    last_check_status: Mapped[str] = mapped_column(String(20), default="never")
    last_check_message: Mapped[str] = mapped_column(Text, default="")
    last_check_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Task(Base, Stamped):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    department_key: Mapped[str] = mapped_column(String(40))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    objective: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, default="")
    constraints: Mapped[str] = mapped_column(Text, default="")
    expected_output: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)  # None = theo routing
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(24), default="Assigned")
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=1024)
    timeout_s: Mapped[int] = mapped_column(Integer, default=60)
    max_retries: Mapped[int] = mapped_column(Integer, default=1)
    attempts_made: Mapped[int] = mapped_column(Integer, default=0)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_source: Mapped[str | None] = mapped_column(String(20), nullable=True)  # provider đã tạo kết quả
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    project: Mapped[Project] = relationship(back_populates="tasks")
    attempts: Mapped[list["TaskAttempt"]] = relationship(back_populates="task", order_by="TaskAttempt.id")
    __table_args__ = (
        CheckConstraint(_in("status", TASK_STATUSES), name="ck_task_status"),
        Index("ix_tasks_project_status", "project_id", "status"),
    )


class FileChange(Base):
    """Đề xuất sửa một tệp trong thư mục dự án trên máy. Chỉ ghi sau khi chủ studio bấm Áp dụng."""
    __tablename__ = "file_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    path: Mapped[str] = mapped_column(String(400))
    new_content: Mapped[str] = mapped_column(Text)
    base_sha: Mapped[str] = mapped_column(String(64), default="")      # "" = tệp mới
    applied_sha: Mapped[str] = mapped_column(String(64), default="")
    backup_path: Mapped[str] = mapped_column(String(600), default="")
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)  # pending|applied|rejected|reverted
    source: Mapped[str] = mapped_column(String(12), default="ai")      # ai|manual
    created_by: Mapped[str] = mapped_column(String(64), default="")
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    __table_args__ = (CheckConstraint(_in("status", ["pending", "applied", "rejected", "reverted"]), name="ck_fchange_status"),)


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), primary_key=True)
    depends_on_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), primary_key=True)


class TaskAttempt(Base):
    __tablename__ = "task_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(16), default="running")  # running|ok|error
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    task: Mapped[Task] = relationship(back_populates="attempts")


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))  # task_run, spend, publish, delete, access...
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    requested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    __table_args__ = (CheckConstraint(_in("status", ["pending", "approved", "rejected"]), name="ck_appr"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(40), default="")
    entity_id: Mapped[str] = mapped_column(String(40), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)


class Budget(Base, Stamped):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(16))
    scope_key: Mapped[str] = mapped_column(String(80), default="")  # project id / dept key / provider / model
    period: Mapped[str] = mapped_column(String(10), default="monthly")
    limit_runs: Mapped[int] = mapped_column(Integer)  # số lượt chạy AI tối đa trong kỳ
    warn_ratio: Mapped[float] = mapped_column(Float, default=0.8)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint(_in("scope", BUDGET_SCOPES), name="ck_budget_scope"),
        CheckConstraint(_in("period", BUDGET_PERIODS), name="ck_budget_period"),
        CheckConstraint("limit_runs > 0", name="ck_budget_limit"),
        UniqueConstraint("scope", "scope_key", "period", name="uq_budget"),
    )


class UsageRecord(Base):
    __tablename__ = "usage_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    department_key: Mapped[str] = mapped_column(String(40), default="")
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(120), default="")
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
