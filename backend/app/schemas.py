from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal["Research", "Concept", "Pre-production", "Prototype", "Production", "QA",
                        "Release Preparation", "Live Operations", "Paused", "Archived"]
ProviderName = Literal["claude_cli", "codex_cli", "internal"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    username: str
    password: str


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["owner", "manager", "viewer"] = "viewer"


class UserOut(ORM):
    id: int
    username: str
    role: str
    active: bool


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    genre: str = ""
    platform: str = ""
    target_market: str = ""
    status: ProjectStatus = "Research"


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    genre: str | None = None
    platform: str | None = None
    target_market: str | None = None
    status: ProjectStatus | None = None


class ProjectOut(ORM):
    id: int
    name: str
    description: str
    genre: str
    platform: str
    target_market: str
    status: str
    workspace_path: str
    source_type: str = ""
    source_ref: str = ""
    source_branch: str = ""
    source_synced_at: datetime | None = None
    allow_write: bool = False
    auto_apply: bool = False
    created_at: datetime
    updated_at: datetime


class DepartmentOut(ORM):
    id: int
    key: str
    name: str
    description: str
    preferred_provider: str


class DepartmentPatch(BaseModel):
    preferred_provider: Literal["openai", "anthropic"]


class AgentOut(ORM):
    id: int
    department_id: int
    name: str
    system_prompt: str
    enabled: bool


class AgentPatch(BaseModel):
    enabled: bool | None = None
    system_prompt: str | None = None


class TaskIn(BaseModel):
    project_id: int
    department_key: str
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1)
    context: str = ""
    constraints: str = ""
    expected_output: str = ""
    acceptance_criteria: str = ""
    provider: ProviderName | None = None
    model: str | None = None
    sensitive: bool = False
    max_output_tokens: int = Field(default=1024, ge=16, le=32000)
    timeout_s: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=1, ge=0, le=3)
    requires_approval: bool = False
    depends_on: list[int] = []


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    objective: str | None = Field(default=None, min_length=1)
    context: str | None = None
    constraints: str | None = None
    expected_output: str | None = None
    acceptance_criteria: str | None = None
    requires_approval: bool | None = None
    provider: ProviderName | None = None   # gửi null = theo routing
    timeout_s: int | None = Field(default=None, ge=1, le=600)
    max_output_tokens: int | None = Field(default=None, ge=16, le=32000)


class BulkTaskIn(BaseModel):
    """Giao cùng một nhiệm vụ cho nhiều phòng ban một lúc (mỗi phòng ban nhận một nhiệm vụ riêng)."""
    project_id: int
    department_keys: list[str] = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1)
    context: str = ""
    constraints: str = ""
    expected_output: str = ""
    acceptance_criteria: str = ""
    # Ghi chú riêng cho từng phòng ban (key phòng ban → nội dung), nối vào cuối mục tiêu
    notes: dict[str, str] = {}
    provider: ProviderName | None = None
    model: str | None = None
    sensitive: bool = False
    max_output_tokens: int = Field(default=1024, ge=16, le=32000)
    timeout_s: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=1, ge=0, le=3)
    requires_approval: bool = False
    run_now: bool = False


class AttemptOut(ORM):
    id: int
    provider: str
    model: str
    status: str
    error: str | None
    input_tokens: int | None
    output_tokens: int | None
    started_at: datetime
    finished_at: datetime | None


class TaskOut(ORM):
    id: int
    project_id: int
    department_key: str
    agent_id: int | None
    title: str
    objective: str
    context: str
    constraints: str
    expected_output: str
    acceptance_criteria: str
    provider: str | None
    model: str | None
    sensitive: bool
    status: str
    max_output_tokens: int
    timeout_s: int
    max_retries: int
    attempts_made: int
    requires_approval: bool
    result: str | None
    result_source: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class TaskDetail(TaskOut):
    attempts: list[AttemptOut] = []
    depends_on: list[int] = []
    help: dict | None = None   # hướng dẫn "bạn cần làm gì" khi nhiệm vụ lỗi


class ProviderOut(BaseModel):
    name: str
    kind: str = "cli"
    enabled: bool
    configured: bool
    program_path: str
    default_model: str
    allow_sensitive: bool
    last_check_status: str
    last_check_message: str
    last_check_at: datetime | None


class ProviderPatch(BaseModel):
    enabled: bool | None = None
    default_model: str | None = None
    allow_sensitive: bool | None = None


class ApprovalOut(ORM):
    id: int
    kind: str
    task_id: int | None
    title: str
    detail: str
    status: str
    requested_at: datetime
    decided_by: str | None
    decided_at: datetime | None


class ApprovalIn(BaseModel):
    kind: Literal["spend", "publish", "delete", "access", "other"]
    title: str = Field(min_length=1, max_length=200)
    detail: str = ""


class DecisionIn(BaseModel):
    approve: bool


class BudgetIn(BaseModel):
    scope: Literal["studio", "project", "department", "provider", "model", "task"]
    scope_key: str = ""
    period: Literal["daily", "monthly", "total"] = "monthly"
    limit_runs: int = Field(gt=0, le=1_000_000)
    warn_ratio: float = Field(default=0.8, gt=0, le=1)


class BudgetOut(ORM):
    id: int
    scope: str
    scope_key: str
    period: str
    limit_runs: int
    warn_ratio: float
    enabled: bool


class AuditOut(ORM):
    id: int
    actor: str
    action: str
    entity: str
    entity_id: str
    detail: str
    created_at: datetime


class UsageOut(ORM):
    id: int
    task_id: int | None
    project_id: int | None
    department_key: str
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime


class StopIn(BaseModel):
    active: bool


class SettingsPatch(BaseModel):
    fallback_enabled: bool | None = None
    auto_run: bool | None = None
