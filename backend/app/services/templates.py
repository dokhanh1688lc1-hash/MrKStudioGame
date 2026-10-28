"""Mẫu nhiệm vụ theo phòng ban: điền sẵn mục tiêu / đầu ra mong muốn / tiêu chí nghiệm thu để giao việc nhanh và đúng cách."""
from __future__ import annotations

T = lambda title, objective, expected, accept: {  # noqa: E731
    "title": title, "objective": objective, "expected_output": expected, "acceptance_criteria": accept}

TEMPLATES: dict[str, list[dict]] = {
    "ceo": [
        T("Báo cáo tổng hợp tuần", "Tổng hợp tiến độ tất cả phòng ban trong tuần từ các kết quả nhiệm vụ đã có trong ngữ cảnh.",
          "Tóm tắt 1 trang: việc đã xong, đang chạy, bị chặn, rủi ro, 3 quyết định cần chủ studio đưa ra.", "Mỗi ý nêu rõ phòng ban/nhiệm vụ nguồn; không bịa số liệu."),
        T("Ưu tiên hóa backlog", "Sắp xếp các việc tồn đọng theo giá trị/công sức và đề xuất thứ tự làm.",
          "Bảng ưu tiên (việc, lý do, công sức ước tính S/M/L, phụ thuộc).", "Có tiêu chí xếp hạng rõ ràng."),
    ],
    "market_research": [
        T("Phân tích đối thủ", "Phân tích 5 game đối thủ trực tiếp của dự án: điểm mạnh/yếu, mô hình kiếm tiền, đánh giá người chơi.",
          "Bảng so sánh + 5 cơ hội khác biệt hóa.", "Chỉ nêu thông tin bạn chắc chắn; ghi rõ phần cần xác minh bằng nguồn thật."),
        T("Xu hướng thể loại", "Mô tả xu hướng hiện tại của thể loại và nền tảng mục tiêu, nhóm người chơi chính.",
          "Báo cáo ngắn: xu hướng, chân dung người chơi, rủi ro thị trường.", "Phân biệt rõ dữ kiện và suy đoán."),
        T("Ý tưởng game mới", "Đề xuất 5 ý tưởng game phù hợp nguồn lực nhỏ (2D, đội nhỏ), kèm vì sao có thị trường.",
          "5 ý tưởng, mỗi ý: hook, core loop 1 câu, đối tượng, độ khó thực hiện.", "Mỗi ý khả thi trong phạm vi đội nhỏ."),
    ],
    "game_design": [
        T("Viết GDD (bản đầu)", "Viết Game Design Document cho dự án: tầm nhìn, core loop, hệ thống chính, tiến trình, UX, phạm vi MVP.",
          "GDD có mục lục: Tầm nhìn, Core loop, Cơ chế, Tiến trình/độ khó, UI/UX, MVP và những gì bỏ ngoài phạm vi.", "MVP làm được trong 4–8 tuần; mỗi cơ chế có tiêu chí hoàn thành."),
        T("Thiết kế màn chơi / cân bằng độ khó", "Thiết kế 10 màn đầu và đường cong độ khó, điểm dạy cơ chế mới.",
          "Bảng màn chơi (mục tiêu, cơ chế mới, độ khó 1–10) + ghi chú cân bằng.", "Độ khó tăng dần hợp lý, không nhảy vọt."),
        T("Backlog MVP", "Chuyển GDD thành backlog công việc cho MVP.", "Danh sách việc có ưu tiên, công sức, phụ thuộc, tiêu chí xong.", "Không có việc mơ hồ; mỗi việc kiểm tra được."),
    ],
    "art": [
        T("Art Bible", "Xây dựng Art Bible: phong cách, bảng màu, nhân vật, UI, ánh sáng, quy ước đặt tên tài sản.",
          "Tài liệu Art Bible + danh sách tài sản cần làm.", "Có mã màu cụ thể và nguyên tắc nhất quán; chỉ dùng tài sản gốc hoặc có giấy phép rõ ràng."),
        T("Brief nhân vật / vật phẩm", "Viết brief hình ảnh chi tiết cho nhân vật và vật phẩm chính để họa sĩ hoặc công cụ tạo ảnh thực hiện.",
          "Mỗi mục: mô tả, tham chiếu phong cách (không sao chép tác phẩm cụ thể), kích thước, các trạng thái/animation.", "Không yêu cầu bắt chước nhân vật/tác phẩm có bản quyền."),
        T("Danh mục tài sản đồ họa", "Liệt kê toàn bộ tài sản đồ họa cần cho MVP.", "Bảng: tên, loại, kích thước, ưu tiên, nguồn (tự làm/mua/AI).", "Đủ cho tất cả màn hình trong GDD."),
    ],
    "audio": [
        T("Audio Bible", "Xác định định hướng âm thanh: phong cách nhạc, nhạc cụ, tâm trạng từng khu vực, nguyên tắc SFX.",
          "Tài liệu Audio Bible + danh sách nhạc/SFX cần có.", "Chỉ dùng nhạc/SFX tự tạo hoặc có giấy phép rõ ràng."),
        T("Danh sách SFX & nhạc nền", "Liệt kê SFX và nhạc nền cho MVP kèm thời lượng, vòng lặp, thời điểm phát.", "Bảng: tên, loại, thời lượng, loop, trigger.", "Khớp với các hành động trong GDD."),
    ],
    "game_dev": [
        T("Kiến trúc & lập kế hoạch kỹ thuật", "Đề xuất kiến trúc (Godot 4/GDScript hoặc công nghệ của dự án), cấu trúc thư mục, scene chính.",
          "Sơ đồ module bằng văn bản, danh sách scene/script, thứ tự dựng prototype.", "Mỗi module có trách nhiệm rõ ràng; ghi rủi ro kỹ thuật."),
        T("Rà soát mã & tìm lỗi", "Rà soát mã nguồn trong ngữ cảnh: lỗi logic, rò rỉ, hiệu năng, mã trùng lặp.",
          "Danh sách vấn đề theo mức nghiêm trọng, nêu tệp/dòng, cách sửa.", "Chỉ nêu vấn đề có trong mã đã cung cấp."),
        T("Viết tính năng mới", "Viết mã cho tính năng được mô tả, theo phong cách mã hiện có của dự án.",
          "Mã hoàn chỉnh theo từng tệp, cách tích hợp, cách kiểm thử thủ công.", "Mã chạy được trong ngữ cảnh đã cho; nêu giả định."),
    ],
    "qa": [
        T("Bộ test case cho tính năng", "Viết test case cho tính năng/màn chơi được mô tả: bình thường, biên, lỗi.",
          "Bảng test case: ID, bước, kết quả mong đợi, mức ưu tiên.", "Bao phủ trường hợp biên và lỗi; kiểm tra được bằng tay."),
        T("Checklist kiểm thử trước phát hành", "Lập checklist QA trước khi phát hành lên cửa hàng (chức năng, hiệu năng, thiết bị, mua hàng, quảng cáo).",
          "Checklist theo nhóm, có tiêu chí đạt/không đạt.", "Không bỏ sót luồng người dùng chính."),
        T("Phân tích báo cáo lỗi", "Phân loại và ưu tiên danh sách lỗi được cung cấp, đề xuất nguyên nhân gốc có thể.", "Bảng lỗi: mức độ, nhóm, nguyên nhân khả dĩ, đề xuất sửa.", "Phân biệt rõ nguyên nhân chắc chắn và phỏng đoán."),
    ],
    "monetization": [
        T("Mô hình kiếm tiền", "Đề xuất mô hình kiếm tiền (quảng cáo, IAP, premium) phù hợp thể loại, kèm rủi ro trải nghiệm.",
          "So sánh các phương án, khuyến nghị 1 phương án, điểm đặt quảng cáo/cửa hàng.", "Không làm hỏng trải nghiệm cốt lõi; không dùng mẫu thiết kế đánh lừa người chơi."),
        T("Kinh tế trong game", "Thiết kế tiền tệ, nguồn thu/chi trong game và cân bằng.", "Bảng nguồn–tiêu hao, giá vật phẩm, kịch bản người chơi.", "Không có vòng lặp lạm phát hiển nhiên."),
        T("Kế hoạch A/B test", "Đề xuất các thử nghiệm A/B cho giá, quảng cáo, onboarding.", "Giả thuyết, chỉ số, cỡ mẫu gợi ý, thời gian chạy.", "Mỗi thử nghiệm có chỉ số thành công rõ."),
    ],
    "marketing": [
        T("Định vị & thông điệp", "Xác định định vị, USP, thông điệp chính cho từng nhóm người chơi.", "Bảng định vị + 3 thông điệp thử nghiệm.", "Không hứa hẹn quá sự thật về game."),
        T("Nội dung cửa hàng (ASO)", "Viết tiêu đề, mô tả ngắn/dài, từ khóa và gợi ý ảnh chụp cho trang cửa hàng.", "Văn bản theo giới hạn ký tự từng cửa hàng + danh sách ảnh cần có.", "Đúng giới hạn ký tự; không chứa thương hiệu của bên khác."),
        T("Kế hoạch ra mắt", "Lập kế hoạch ra mắt 4 tuần (trước, trong, sau).", "Lịch theo tuần, kênh, ngân sách thô, chỉ số theo dõi.", "Khả thi với đội nhỏ."),
    ],
    "analytics": [
        T("Kế hoạch theo dõi sự kiện", "Thiết kế bộ sự kiện phân tích (onboarding, tiến trình, mua hàng, quảng cáo).", "Bảng sự kiện: tên, thời điểm, tham số, mục đích.", "Không thu thập dữ liệu cá nhân không cần thiết."),
        T("Phân tích retention / funnel", "Phân tích số liệu được cung cấp: retention, funnel, điểm rơi.", "Phát hiện chính, nguyên nhân khả dĩ, 3 đề xuất hành động.", "Chỉ kết luận từ số liệu đã cung cấp."),
    ],
    "devops": [
        T("Quy trình build & phát hành", "Thiết lập quy trình build, đánh số phiên bản, ký ứng dụng, xuất bản.", "Các bước theo thứ tự cho từng nền tảng + checklist.", "Mỗi bước có cách kiểm tra."),
        T("Checklist nộp cửa hàng", "Liệt kê yêu cầu của cửa hàng mục tiêu (chính sách, quyền riêng tư, chấm điểm độ tuổi, tài sản).", "Checklist có trạng thái và người phụ trách.", "Ghi rõ điều cần xác minh trên tài liệu chính thức mới nhất."),
    ],
    "finance": [
        T("Kế hoạch ngân sách studio", "Lập kế hoạch chi phí/doanh thu dự kiến cho dự án.", "Bảng chi phí theo tháng, kịch bản thấp/vừa/cao.", "Nêu rõ giả định; không bịa số liệu thị trường."),
        T("Hiệu quả sử dụng AI", "Đánh giá việc dùng Claude Code/Codex theo số lượt chạy và kết quả đạt được.", "Nhận xét theo phòng ban, đề xuất phân bổ lại hạn mức lượt chạy.", "Dựa trên số liệu thật trong hệ thống."),
    ],
    "compliance": [
        T("Kiểm tra nguồn gốc tài sản", "Kiểm tra danh sách tài sản (hình, âm thanh, phông, mã) về giấy phép và nguồn gốc.", "Bảng: tài sản, nguồn, giấy phép, rủi ro, hành động.", "Không khẳng định pháp lý chắc chắn; đề nghị xác minh khi nghi ngờ."),
        T("Rà soát tên/nhận diện", "Rà soát tên game, nhân vật, logo xem có nguy cơ trùng thương hiệu hoặc nhân vật có sẵn.", "Danh sách rủi ro và đề xuất đổi tên/thay thế.", "Không sao chép nhân vật hay tác phẩm có bản quyền."),
        T("Chính sách quyền riêng tư", "Soạn dàn ý chính sách quyền riêng tư và danh sách dữ liệu thu thập theo thiết kế game.", "Dàn ý + danh sách dữ liệu + lưu ý theo khu vực.", "Ghi rõ cần luật sư xem lại trước khi dùng."),
    ],
    "operations": [
        T("Quy trình vận hành hằng ngày", "Soạn quy trình theo dõi, thông báo và xử lý yêu cầu hằng ngày của studio.", "Danh sách việc hằng ngày/tuần, người phụ trách, cách báo cáo.", "Đơn giản, làm được bởi 1–2 người."),
    ],
}


def all_templates() -> dict[str, list[dict]]:
    return TEMPLATES
