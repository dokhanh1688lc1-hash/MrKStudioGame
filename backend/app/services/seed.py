"""Khởi tạo dữ liệu nền: 14 phòng ban, agent mặc định, provider, tài khoản chủ studio."""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Agent, Department, ProviderConfig, Task, User
from ..security import hash_password
from .common import audit

BASE_RULES = (
    "Bạn là một thành viên của MrK Studio Game. Trả lời bằng tiếng Việt, rõ ràng, có cấu trúc. "
    "Không bịa số liệu thị trường, doanh thu hoặc chi phí: phân biệt dữ liệu đã xác minh, giả thuyết và dự đoán; "
    "nêu nguồn khi có. Không sao chép tài sản hay nội dung độc quyền của game khác. "
    "Không tuyên bố đã làm điều bạn chưa làm."
)

# key, tên, provider ưu tiên, mô tả
DEPARTMENTS = [
    ("ceo", "CEO Dashboard", "openai", "Điều hành tổng thể, tổng hợp báo cáo cho chủ studio."),
    ("market_research", "Market Research AI", "openai", "Nghiên cứu thị trường, đối thủ, nhu cầu người chơi."),
    ("game_design", "Product & Game Design AI", "openai", "Ý tưởng, GDD, core loop, UX, MVP, backlog."),
    ("art", "Art Studio AI", "openai", "Art Bible, brief hình ảnh, quản lý tài sản đồ họa."),
    ("audio", "Audio Studio AI", "openai", "Audio Bible, brief nhạc và hiệu ứng âm thanh."),
    ("game_dev", "Game Development AI", "anthropic", "Godot 4/GDScript, scene, gameplay, tích hợp, build."),
    ("qa", "QA & Game Testing AI", "anthropic", "Test case, kiểm thử, báo cáo lỗi, hồi quy."),
    ("monetization", "Monetization & Economy AI", "openai", "Quảng cáo, IAP, kinh tế game, A/B test."),
    ("marketing", "Marketing Studio AI", "openai", "Định vị, ASO, kế hoạch ra mắt, nội dung."),
    ("analytics", "Data & Analytics AI", "openai", "Retention, conversion, cohort, báo cáo dữ liệu."),
    ("devops", "DevOps & Release AI", "anthropic", "Build, version, checklist cửa hàng, phát hành."),
    ("finance", "Finance & Resource Management AI", "openai", "Ngân sách, chi phí API, hiệu quả provider."),
    ("compliance", "IP, Legal & Compliance AI", "openai", "Nguồn gốc tài sản, giấy phép, checklist bản quyền."),
    ("operations", "Telegram & Operations AI", "anthropic", "Thông báo, tra cứu, yêu cầu công việc (Telegram chưa triển khai)."),
]


def seed_all(s: Session, settings: Settings) -> str | None:
    """Trả về mật khẩu vừa sinh ngẫu nhiên (nếu có) để in ra một lần."""
    for key, name, prov, desc in DEPARTMENTS:
        dept = s.scalar(select(Department).where(Department.key == key))
        if not dept:
            dept = Department(key=key, name=name, preferred_provider=prov, description=desc)
            s.add(dept)
            s.flush()
            s.add(Agent(department_id=dept.id, name=f"Agent {name}",
                        system_prompt=f"{BASE_RULES}\nVai trò: {name}. Phạm vi: {desc}"))

    for name, model in (("openai", settings.openai_default_model),
                        ("anthropic", settings.anthropic_default_model), ("internal", "internal")):
        if not s.scalar(select(ProviderConfig).where(ProviderConfig.name == name)):
            s.add(ProviderConfig(name=name, default_model=model, allow_sensitive=(name == "internal")))

    generated = None
    if not s.scalar(select(User).limit(1)):
        pwd = settings.admin_password
        if not pwd:
            pwd = generated = secrets.token_urlsafe(12)
        s.add(User(username=settings.admin_username, password_hash=hash_password(pwd), role="owner"))
        audit(s, "system", "bootstrap_owner", "user", settings.admin_username)
    s.commit()
    return generated


def recover_interrupted(s: Session) -> int:
    """Sau khi backend khởi động lại: nhiệm vụ đang Running bị gián đoạn → Failed (có thể chạy lại)."""
    rows = s.scalars(select(Task).where(Task.status == "Running")).all()
    for t in rows:
        t.status = "Failed"
        t.error = "Bị gián đoạn do backend khởi động lại. Có thể chạy lại."
        audit(s, "system", "task_recovered", "task", t.id)
    s.commit()
    return len(rows)
