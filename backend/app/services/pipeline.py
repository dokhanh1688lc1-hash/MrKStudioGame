"""Pipeline sản xuất game: chuỗi nhiệm vụ liên phòng ban có phụ thuộc và cổng phê duyệt.

Bước có `gate=True` yêu cầu chủ studio phê duyệt trước khi chạy (Concept → GDD, Feasibility → Prototype,
trước Release). Kết quả của bước trước được truyền vào bước sau qua cơ chế phụ thuộc.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Agent, Department, Project, Task, TaskDependency
from .common import EngineError, audit

PREFIX = "[Pipeline]"


@dataclass(frozen=True)
class Step:
    key: str
    dept: str
    title: str
    objective: str
    deps: tuple[str, ...] = ()
    gate: bool = False
    criteria: str = ""


TEMPLATE: list[Step] = [
    Step("research", "market_research", "Nghiên cứu thị trường",
         "Nghiên cứu thị trường, đối thủ và nhu cầu người chơi cho game này. Nêu khoảng trống sản phẩm, rủi ro và đề xuất thử nghiệm xác minh nhu cầu.",
         criteria="Phân biệt rõ dữ liệu đã xác minh / giả thuyết / dự đoán; có nguồn tham khảo hoặc ghi rõ chưa có nguồn."),
    Step("concept", "game_design", "Ý tưởng game (Concept)",
         "Đề xuất 1 concept game có bản sắc riêng dựa trên nghiên cứu: core loop, điểm khác biệt, đối tượng, phạm vi MVP.",
         ("research",), criteria="Không sao chép nhân vật/tài sản/nội dung độc quyền của game khác."),
    Step("gdd", "game_design", "Tài liệu thiết kế (GDD)",
         "Viết GDD cho concept đã được chủ studio duyệt: gameplay, tiến trình, UX/onboarding, độ khó, backlog MVP có tiêu chí nghiệm thu.",
         ("concept",), gate=True, criteria="Backlog MVP có tiêu chí nghiệm thu đo được."),
    Step("feasibility", "game_dev", "Đánh giá khả thi kỹ thuật",
         "Đánh giá khả thi kỹ thuật của GDD với Godot 4/GDScript: kiến trúc đề xuất, rủi ro, ước lượng công việc theo mốc.",
         ("gdd",)),
    Step("art_bible", "art", "Art Bible",
         "Xây dựng Art Bible: phong cách thống nhất, danh sách tài sản cần có, brief cho nhân vật/môi trường/UI. Chỉ là brief và prompt, chưa tạo ảnh.",
         ("gdd",), criteria="Mỗi tài sản có nguồn gốc dự kiến và yêu cầu giấy phép."),
    # Studio âm thanh đang tạm dừng: phòng Dev đảm nhiệm danh mục âm thanh tạm, phòng Pháp lý (compliance) rà soát.
    Step("audio_bible", "game_dev", "Danh mục âm thanh (Dev, tạm thay Studio âm thanh)",
         "Studio âm thanh đang tạm dừng. Lập danh mục âm thanh tối thiểu cho UI/gameplay/thắng-thua và chỗ đặt (placeholder) trong "
         "Godot; chỉ ghi nhu cầu, không tạo hay tuyên bố đã có tệp âm thanh. Mỗi mục ghi nguồn dự kiến để phòng Pháp lý rà soát.",
         ("gdd",), criteria="Không dùng âm thanh thương mại khi chưa xác minh quyền sử dụng; mọi tệp âm thanh phải qua phòng Pháp lý."),
    Step("monetization", "monetization", "Mô hình kiếm tiền",
         "Đề xuất mô hình quảng cáo/mua hàng phù hợp gameplay, kinh tế game và thử nghiệm A/B. Không cam kết doanh thu.",
         ("gdd",), criteria="Không bịa số liệu doanh thu; tránh thiết kế ép chi tiền."),
    Step("prototype", "game_dev", "Kế hoạch prototype",
         "Lập kế hoạch xây prototype: cấu trúc scene/script Godot, thứ tự triển khai, tiêu chí nghiệm thu prototype.",
         ("feasibility", "art_bible", "audio_bible"), gate=True),
    Step("qa_plan", "qa", "Kế hoạch kiểm thử",
         "Xây dựng test case cho các luồng chính, lưu tiến trình, quảng cáo/mua hàng (môi trường test) và tiêu chí Passed/Failed/Blocked/Not Run.",
         ("prototype",)),
    Step("compliance", "compliance", "Rà soát bản quyền & chính sách",
         "Lập checklist nguồn gốc tài sản (gồm âm thanh do Dev đề xuất), giấy phép, chính sách cửa hàng. Không tuyên bố chắc chắn không vi phạm.",
         ("art_bible", "audio_bible", "prototype")),
    Step("release_prep", "devops", "Chuẩn bị phát hành",
         "Lập checklist phát hành App Store/Google Play: build, version, metadata. Không tự phát hành.",
         ("qa_plan", "compliance"), gate=True),
    Step("marketing", "marketing", "Marketing & ASO",
         "Định vị thương hiệu, tên/mô tả cửa hàng, ASO, brief screenshot/trailer, kế hoạch ra mắt. Không tự đăng công khai.",
         ("gdd", "monetization")),
]


def _context(p: Project, brief: str) -> str:
    bits = [f"Game: {p.name}", f"Thể loại: {p.genre or '(chưa rõ)'}", f"Nền tảng: {p.platform or '(chưa rõ)'}",
            f"Thị trường mục tiêu: {p.target_market or '(chưa rõ)'}"]
    if p.description:
        bits.append(f"Mô tả: {p.description}")
    if brief:
        bits.append(f"Yêu cầu của chủ studio: {brief}")
    return "\n".join(bits)


def _title(i: int, s: Step) -> str:
    return f"{PREFIX} {i}. {s.title}"


def pipeline_tasks(s: Session, project_id: int) -> list[Task]:
    return list(s.scalars(select(Task).where(Task.project_id == project_id, Task.title.like(f"{PREFIX}%"))
                          .order_by(Task.id)))


def create_pipeline(s: Session, project_id: int, brief: str, actor: str) -> list[Task]:
    p = s.get(Project, project_id)
    if not p:
        raise EngineError(404, "Không tìm thấy dự án.")
    if p.status == "Archived":
        raise EngineError(409, "Dự án đã lưu trữ (Archived).")
    if pipeline_tasks(s, project_id):
        raise EngineError(409, "Dự án đã có pipeline.")
    ctx = _context(p, brief)
    created: dict[str, Task] = {}
    for i, st in enumerate(TEMPLATE, 1):
        dept = s.scalar(select(Department).where(Department.key == st.dept))
        agent = s.scalar(select(Agent).where(Agent.department_id == dept.id, Agent.enabled.is_(True)).order_by(Agent.id))
        if not agent:
            raise EngineError(409, f"Phòng ban '{dept.name}' chưa có agent nào được bật.")
        t = Task(project_id=p.id, department_key=st.dept, agent_id=agent.id, title=_title(i, st),
                 objective=st.objective, context=ctx, acceptance_criteria=st.criteria,
                 requires_approval=st.gate, status="Assigned")
        s.add(t)
        s.flush()
        for d in st.deps:
            s.add(TaskDependency(task_id=t.id, depends_on_id=created[d].id))
        created[st.key] = t
    audit(s, actor, "pipeline_created", "project", p.id, f"{len(created)} bước")
    s.commit()
    return list(created.values())
