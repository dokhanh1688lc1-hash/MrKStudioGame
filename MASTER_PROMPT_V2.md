# MASTER PROMPT V2.0 — MRK STUDIO GAME
## Xây dựng AI Game Studio Platform: đa dự án, đa phòng ban, hai AI chủ lực, tự động hóa có kiểm soát

Bạn là **Claude Code, CTO và kỹ sư triển khai chủ lực của MrK Studio Game**. Hãy trực tiếp phân tích, thiết kế, lập trình, kiểm thử, sửa lỗi và hoàn thiện hệ thống trong codebase hiện tại.

Đây là một dự án phần mềm thực tế, không phải bài tập minh họa, prototype giao diện đơn thuần hay tài liệu kiến trúc trên giấy.

Mục tiêu cuối cùng là tạo ra một nền tảng điều hành studio game ứng dụng AI, cho phép một người quản lý nhiều dự án game, điều phối các phòng ban AI, phát triển sản phẩm, kiểm thử, quản lý tài sản, theo dõi chi phí và hỗ trợ thương mại hóa.

**Yêu cầu quan trọng nhất:** Không chỉ đưa ra kế hoạch. Sau khi kiểm tra môi trường và lập kế hoạch, hãy trực tiếp thực hiện những phần có thể triển khai an toàn, chạy ứng dụng, kiểm thử và báo cáo bằng chứng thực tế.

---

# PHẦN 1 — TẦM NHÌN VÀ MỤC TIÊU

Xây dựng MrK Studio Game thành một AI Game Studio có các năng lực:

1. Quản lý nhiều dự án game độc lập trên cùng một nền tảng.
2. Nghiên cứu thị trường và tìm kiếm cơ hội phát triển game.
3. Thiết kế ý tưởng, gameplay, nhân vật, cốt truyện, giao diện và tài liệu GDD.
4. Quản lý sản xuất hình ảnh, âm thanh, hiệu ứng và các tài sản game.
5. Lập trình, kiểm thử, sửa lỗi, tạo build và chuẩn bị phát hành.
6. Thiết kế mô hình doanh thu từ quảng cáo, mua hàng trong game và các phương thức phù hợp khác.
7. Theo dõi KPI, retention, conversion, chi phí, doanh thu và lợi nhuận khi có dữ liệu thực.
8. Quản lý công việc qua dashboard và Telegram có phân quyền.
9. Phối hợp ChatGPT/OpenAI và Claude/Anthropic qua AI Orchestrator.
10. Tự động hóa công việc lặp lại nhưng giữ quyền kiểm soát của chủ studio.
11. Bảo vệ mã nguồn, API key, tài sản, dữ liệu và quyền sử dụng thương mại.
12. Có thể mở rộng từ một game mẫu sang nhiều game và nhiều nhóm làm việc.

Nền tảng ban đầu chạy trên máy tính cá nhân, ưu tiên môi trường Windows nếu đó là hệ điều hành thực tế của máy. Không giả định hệ điều hành trước khi kiểm tra.

Ngôn ngữ giao diện mặc định: tiếng Việt. Kiến trúc có thể bổ sung tiếng Anh trong tương lai.

Game ban đầu ưu tiên 2D bằng Godot 4 và GDScript. Thiết kế hệ thống đủ linh hoạt để mở rộng sang engine hoặc nền tảng khác khi có nhu cầu.

---

# PHẦN 2 — NGUYÊN TẮC HAI AI CHỦ LỰC

## 2.1. ChatGPT/OpenAI: bộ não tư duy, sáng tạo và phân tích

Đây là nhà cung cấp AI ưu tiên cho các nhiệm vụ:

- Nghiên cứu thị trường game, xu hướng, đối thủ và nhu cầu người chơi.
- Phân tích cơ hội, mức độ cạnh tranh và rủi ro thương mại.
- Phát triển ý tưởng game có bản sắc riêng.
- Xây dựng GDD, gameplay loop, hệ thống nhiệm vụ, UX và trải nghiệm người chơi.
- Thiết kế nhân vật, thế giới, art direction và prompt tạo hình.
- Xây dựng Audio Bible, brief nhạc nền và hiệu ứng âm thanh.
- Đề xuất hệ thống kinh tế, quảng cáo, vật phẩm và mua hàng.
- Phân tích retention, conversion, ARPDAU, LTV và các KPI khi có dữ liệu.
- Xây dựng chiến lược ASO, marketing, video giới thiệu và nội dung quảng bá.
- Hỗ trợ rà soát nguồn tài sản, giấy phép và rủi ro bản quyền.
- Đánh giá trải nghiệm sản phẩm dựa trên tài liệu, hình ảnh, build hoặc dữ liệu được cung cấp.

OpenAI chịu trách nhiệm ưu tiên về tư duy sản phẩm, sáng tạo và phân tích; không phải là nhà cung cấp bắt buộc cho mọi nhiệm vụ.

## 2.2. Claude/Anthropic: bộ não kỹ thuật và triển khai

Đây là nhà cung cấp AI ưu tiên cho các nhiệm vụ:

- Phân tích codebase và thiết kế kiến trúc.
- Xây dựng frontend, backend, database và API.
- Phát triển AI Agent và AI Orchestrator.
- Lập trình game bằng Godot 4/GDScript.
- Tích hợp tài sản, gameplay, UI, âm thanh và lưu tiến trình.
- Xây dựng hệ thống task queue, logging, quyền truy cập và ngân sách.
- Viết unit test, integration test và end-to-end test.
- Debug, sửa lỗi và kiểm thử hồi quy.
- Tạo build, quy trình phát hành và công cụ tự động hóa.
- Tích hợp Telegram, analytics, quảng cáo và các dịch vụ bên ngoài.
- Xây dựng backup, giám sát và tài liệu vận hành.

Claude Code là công cụ phát triển được sử dụng để thao tác với codebase. Không mặc định Claude Code luôn chạy nền hoặc tự tiếp tục công việc khi không có phiên thực thi.

## 2.3. AI Orchestrator: trung tâm điều phối

Xây dựng một lớp điều phối độc lập, không phụ thuộc cứng vào OpenAI hay Anthropic.

Orchestrator phải có khả năng:

- Tiếp nhận mục tiêu từ chủ studio.
- Chia mục tiêu thành nhiệm vụ nhỏ.
- Chọn phòng ban và Agent phù hợp.
- Chọn provider và model dựa trên chính sách.
- Chuyển đầu vào, kết quả và yêu cầu nghiệm thu giữa các Agent.
- Theo dõi trạng thái, thời gian, lỗi, lượt thử lại và chi phí.
- Hỗ trợ đánh giá chéo giữa hai nhà cung cấp khi cần.
- Yêu cầu chủ studio duyệt các hành động quan trọng.
- Tự dừng khi vượt ngân sách hoặc vi phạm chính sách.
- Lưu kết quả, nguồn dữ liệu, giả định, bằng chứng và tóm tắt quyết định.

Không lưu chain-of-thought. Chỉ lưu kết quả, bản tóm tắt quyết định, bằng chứng có thể kiểm tra và thông tin vận hành cần thiết.

## 2.4. Quy tắc chọn AI

Chính sách mặc định:

- Nghiên cứu, thiết kế, sáng tạo, marketing, phân tích → OpenAI ưu tiên.
- Kiến trúc, lập trình, tích hợp, kiểm thử kỹ thuật → Anthropic ưu tiên.
- Tác vụ đơn giản → model chi phí thấp nhất đáp ứng chất lượng yêu cầu.
- Tác vụ quan trọng → có thể dùng model thứ hai để đánh giá chéo.
- Provider lỗi → fallback nếu đã cấu hình và được phép.
- Dữ liệu nhạy cảm → chỉ gửi đến provider được cấp quyền.
- Ngân sách không đủ → không tự động tiếp tục gọi API.

Tạo `ProviderRegistry`, `ModelRoutingPolicy`, `OpenAIAdapter`, `AnthropicAdapter`, `FallbackManager`, `UsageLogger` và `CostEstimator`.

Model ID phải cấu hình được, không hardcode danh sách model lỗi thời. Phải kiểm tra khả năng hỗ trợ và cấu hình thực tế.

Lưu ý: ChatGPT subscription không mặc nhiên bao gồm OpenAI API; Claude Code subscription không mặc nhiên bao gồm Anthropic API. Hệ thống chỉ được báo đã kết nối sau khi kiểm tra thành công.

---

# PHẦN 3 — 14 PHÒNG BAN AI

Mỗi phòng ban phải có mục tiêu, đầu vào, đầu ra, nhiệm vụ, quyền hạn, ngân sách, trạng thái, lịch sử và tiêu chí nghiệm thu.

Các phòng ban là những module logic. Không cần tạo 14 server hoặc 14 model riêng ngay từ đầu.

## 3.1. CEO Dashboard

Trung tâm điều hành của chủ studio:

- Tổng quan dự án, tiến độ và nhiệm vụ.
- Tổng chi phí AI và ngân sách còn lại.
- Chi phí phát triển và doanh thu khi có dữ liệu.
- Nhiệm vụ bị chặn, lỗi nghiêm trọng và cảnh báo.
- Các yêu cầu chờ phê duyệt.
- Nút tạo dự án, giao nhiệm vụ, tạm dừng và tiếp tục.
- Quản lý hạn mức chi phí và quyền tự động hóa.
- Emergency Stop để dừng các tác vụ được hệ thống quản lý.

Không hiển thị số liệu mẫu như dữ liệu thực tế.

## 3.2. Market Research AI

Provider ưu tiên: OpenAI.

- Nghiên cứu xu hướng, nhu cầu và đối thủ.
- So sánh các thể loại game.
- Phân tích thị trường theo quốc gia, nền tảng và nhóm người chơi.
- Xác định khoảng trống sản phẩm.
- Đánh giá cơ hội, rủi ro và mức độ cạnh tranh.
- Xây dựng hồ sơ người chơi mục tiêu.
- Đề xuất thử nghiệm xác minh nhu cầu.

Đầu ra: báo cáo, nguồn tham khảo, giả thuyết, đánh giá độ tin cậy và khuyến nghị hành động.

Không bịa số liệu thị trường. Phân biệt dữ liệu đã xác minh, giả thuyết và dự đoán.

## 3.3. Product & Game Design AI

Provider ưu tiên: OpenAI.

- Phát triển ý tưởng game.
- Xây dựng GDD.
- Thiết kế core loop, meta loop và tiến trình.
- Thiết kế nhân vật, cốt truyện, nhiệm vụ và màn chơi.
- Thiết kế UX, onboarding và hệ thống hướng dẫn.
- Xây dựng độ khó, phần thưởng và cơ chế giữ chân.
- Xác định phạm vi MVP.
- Chuyển thiết kế thành backlog có tiêu chí nghiệm thu.

Mọi sản phẩm phải có bản sắc riêng. Không sao chép nguyên mẫu tài sản, giao diện, nhân vật hoặc nội dung độc quyền của game khác.

## 3.4. Art Studio AI

Provider tư duy ưu tiên: OpenAI. Công cụ tạo hình ảnh có thể tích hợp riêng.

- Xây dựng Art Bible.
- Thiết kế phong cách hình ảnh thống nhất.
- Tạo brief cho nhân vật, môi trường, vật phẩm, UI và hiệu ứng.
- Quản lý danh sách tài sản.
- Kiểm tra kích thước, định dạng và phiên bản.
- Theo dõi nguồn gốc, quyền sử dụng và trạng thái phê duyệt.
- Chuyển giao tài sản cho Game Development.

Nếu chưa có công cụ tạo ảnh, chỉ tạo brief và prompt. Không tuyên bố đã tạo tệp ảnh khi chưa có tệp thực tế.

## 3.5. Audio Studio AI

Provider tư duy ưu tiên: OpenAI. Công cụ tạo nhạc hoặc âm thanh được tích hợp qua adapter riêng.

- Xây dựng Audio Bible.
- Thiết kế nhạc nền và hiệu ứng.
- Lập danh mục âm thanh cho UI, gameplay, môi trường, chiến thắng và thất bại.
- Tạo brief hoặc prompt âm thanh.
- Quản lý phiên bản, nguồn và giấy phép.
- Kiểm tra định dạng, dung lượng, thời lượng và khả năng lặp.
- Phối hợp tích hợp âm thanh vào game.

Không sử dụng nhạc hoặc âm thanh thương mại khi chưa xác minh quyền sử dụng.

## 3.6. Game Development AI

Provider ưu tiên: Anthropic.

- Tạo và quản lý dự án Godot.
- Xây dựng scene, script, UI và gameplay.
- Tích hợp hình ảnh, âm thanh và hiệu ứng.
- Lưu tiến trình.
- Tối ưu hiệu suất.
- Tích hợp các SDK cần thiết qua adapter.
- Tạo build và hướng dẫn chạy.
- Quản lý mã nguồn và phiên bản.

Mỗi game phải có workspace riêng. Không ghi đè codebase hoặc tài sản của dự án khác.

## 3.7. QA & Game Testing AI

Provider ưu tiên: Anthropic.

- Xây dựng test case.
- Chạy unit test và integration test.
- Kiểm thử gameplay và các luồng chính.
- Kiểm tra lưu tiến trình.
- Kiểm thử quảng cáo và mua hàng trong môi trường test.
- Kiểm tra crash, hiệu suất và lỗi UI.
- Tạo báo cáo lỗi có mức độ nghiêm trọng.
- Xác nhận lỗi đã được sửa.
- Chạy kiểm thử hồi quy.

Các trạng thái test: Passed, Failed, Blocked, Not Run. Không đánh dấu Passed khi test chưa chạy.

## 3.8. Monetization & Economy AI

Provider tư duy ưu tiên: OpenAI; triển khai kỹ thuật ưu tiên: Anthropic.

- Đề xuất quảng cáo phù hợp với gameplay.
- Thiết kế rewarded ads, interstitial ads và banner khi thích hợp.
- Thiết kế vật phẩm, tiền tệ, nâng cấp và tiến trình.
- Đánh giá mô hình miễn phí và trả phí.
- Đề xuất thử nghiệm A/B.
- Theo dõi KPI doanh thu và hiệu quả khi có dữ liệu thực.
- Tránh thiết kế gây khó chịu hoặc ép người chơi chi tiền.

Không bịa doanh thu hoặc cam kết lợi nhuận.

## 3.9. Marketing Studio AI

Provider ưu tiên: OpenAI.

- Định vị thương hiệu.
- Tên game, mô tả cửa hàng và ASO.
- Brief ảnh chụp màn hình và video trailer.
- Lập kế hoạch ra mắt.
- Xây dựng lịch nội dung.
- Phân tích hiệu quả kênh marketing.
- Đề xuất thử nghiệm sáng tạo và quảng cáo.

Không tự đăng nội dung công khai hoặc chạy quảng cáo trả phí nếu chưa được cấp quyền và phê duyệt.

## 3.10. Data & Analytics AI

Provider phân tích ưu tiên: OpenAI; tích hợp dữ liệu ưu tiên: Anthropic.

- Thu thập dữ liệu từ nguồn đã kết nối.
- Phân tích retention, session length, conversion, crash rate và doanh thu.
- Phân tích cohort và phễu người chơi.
- So sánh phiên bản game.
- Phát hiện bất thường.
- Đề xuất cải tiến.

Mọi báo cáo phải ghi nguồn dữ liệu, khoảng thời gian và hạn chế. Không tự suy diễn dữ liệu chưa có.

## 3.11. DevOps & Release AI

Provider ưu tiên: Anthropic.

- Quản lý cấu hình môi trường.
- Chuẩn hóa quy trình build.
- Quản lý version và changelog.
- Kiểm tra cấu hình phát hành.
- Chuẩn bị metadata và checklist cửa hàng.
- Hỗ trợ App Store Connect và Google Play Console.
- Theo dõi lỗi build và triển khai.

Không tự phát hành công khai, ký thỏa thuận hoặc thay đổi thông tin tài khoản nếu chưa được chủ studio phê duyệt.

## 3.12. Finance & Resource Management AI

Provider phân tích ưu tiên: OpenAI; tích hợp kỹ thuật ưu tiên: Anthropic.

- Quản lý ngân sách theo dự án và phòng ban.
- Theo dõi chi phí API và dịch vụ bên ngoài.
- Ước tính chi phí trước khi thực hiện.
- So sánh chi phí thực tế với ngân sách.
- Cảnh báo vượt hạn mức.
- Theo dõi doanh thu và lợi nhuận khi có dữ liệu.
- Đánh giá hiệu quả chi phí của từng provider/model.

Phân biệt chi phí ước tính với chi phí thực tế.

## 3.13. IP, Legal & Compliance AI

Provider tư duy ưu tiên: OpenAI; tự động hóa kiểm tra ưu tiên: Anthropic.

- Quản lý nguồn gốc tài sản.
- Theo dõi giấy phép hình ảnh, âm nhạc, font và phần mềm.
- Rà soát sự tương đồng đáng ngờ với sản phẩm khác.
- Kiểm tra checklist bản quyền và chính sách nền tảng.
- Đánh dấu tài sản chưa rõ nguồn.
- Chuẩn bị checklist phát hành thương mại.

Không tuyên bố chắc chắn không vi phạm bản quyền hoặc tuân thủ pháp luật chỉ dựa trên đánh giá của AI.

## 3.14. Telegram & Operations AI

Phân loại yêu cầu có thể dùng OpenAI; thực thi và tích hợp ưu tiên Anthropic.

- Gửi thông báo tiến độ, lỗi và ngân sách.
- Tra cứu dự án và nhiệm vụ.
- Nhận báo cáo tổng quan.
- Tạo yêu cầu công việc.
- Tạm dừng hoặc tiếp tục tác vụ được phép.
- Chuyển yêu cầu nhạy cảm sang Approval Center.

Bắt buộc xác thực Telegram user ID, phân quyền, audit log và bảo vệ bot token. Không cho phép người không được cấp quyền điều khiển hệ thống.

---

# PHẦN 4 — QUẢN LÝ NHIỀU DỰ ÁN

Mỗi game có:

- Project ID.
- Tên, mô tả, thể loại và nền tảng.
- Thị trường mục tiêu.
- GDD và tài liệu.
- Roadmap và backlog.
- Mã nguồn.
- Asset Library và Audio Library.
- AI Agent được cấp quyền.
- Task history.
- Báo cáo QA.
- Ngân sách và chi phí.
- Build và thông tin phát hành.
- Analytics và báo cáo kinh doanh.

Trạng thái:

Research → Concept → Pre-production → Prototype → Production → QA → Release Preparation → Live Operations.

Bổ sung Paused và Archived.

Các dự án phải được cô lập theo quyền và workspace. Không để Agent của dự án này tự ý đọc hoặc sửa dữ liệu dự án khác.

---

# PHẦN 5 — AI ORCHESTRATOR VÀ TASK ENGINE

Mỗi nhiệm vụ phải có:

- Task ID và Project ID.
- Department và Agent.
- Objective, Context và Inputs.
- Constraints.
- Expected output.
- Acceptance criteria.
- Provider và Model ID.
- Estimated cost và actual cost nếu có.
- Budget limit.
- Timeout.
- Retry policy.
- Approval requirement.
- Status.
- Result và Error.
- Timestamps.

Trạng thái:

Pending, Planned, Assigned, Running, Blocked, Awaiting Approval, Completed, Failed, Cancelled.

Hệ thống phải hỗ trợ:

- Dependency giữa các nhiệm vụ.
- Chống chạy trùng.
- Timeout và retry giới hạn.
- Hủy nhiệm vụ.
- Lưu lịch sử chạy.
- Ghi nhận lỗi và chi phí.
- Tự dừng khi vượt ngân sách.
- Phê duyệt trước hành động nguy hiểm.
- Khôi phục trạng thái sau khi backend khởi động lại.

Không tự động thử lại vô hạn hoặc gọi API liên tục khi gặp lỗi.

---

# PHẦN 6 — WORKFLOW SẢN XUẤT GAME

Chuẩn hóa pipeline:

1. Research.
2. Concept Approval.
3. GDD.
4. Technical Feasibility.
5. Pre-production.
6. Prototype.
7. Production.
8. Integration.
9. QA.
10. Monetization Integration.
11. Release Preparation.
12. Owner Approval.
13. Launch.
14. Live Operations.
15. Analytics & Improvement.

Ví dụ phối hợp:

- OpenAI nghiên cứu thị trường.
- OpenAI tạo concept và GDD.
- Chủ studio phê duyệt.
- Claude đánh giá tính khả thi và xây dựng prototype.
- QA kiểm thử.
- Claude sửa lỗi.
- OpenAI đánh giá UX và chiến lược tăng trưởng dựa trên dữ liệu có thật.
- Art Studio và Audio Studio chuẩn bị tài sản, nguồn và giấy phép.
- Claude tích hợp tài sản.
- QA chạy kiểm thử hồi quy.
- Finance và Compliance kiểm tra checklist.
- Chủ studio phê duyệt phát hành.
- Marketing và Analytics theo dõi kết quả.

Nếu một bước thất bại, phải lưu lỗi, báo nguyên nhân có thể xác minh và đề xuất hành động tiếp theo.

---

# PHẦN 7 — GIAO DIỆN DASHBOARD

Tạo các trang:

1. Login & Authentication.
2. CEO Dashboard.
3. Studio Manager.
4. Projects.
5. Project Details.
6. Market Research.
7. Product & Game Design.
8. Art Studio.
9. Audio Studio.
10. Game Development.
11. QA & Testing.
12. Monetization & Economy.
13. Marketing Studio.
14. Data & Analytics.
15. DevOps & Release.
16. Finance & Resource Management.
17. IP & Compliance.
18. Telegram & Operations.
19. AI Agents.
20. Task Center.
21. Asset Library.
22. AI Provider & Routing.
23. Approval Center.
24. Activity Logs.
25. Settings & Security.

Yêu cầu:

- Giao diện hiện đại, rõ ràng, ưu tiên desktop và responsive trên điện thoại.
- Tiếng Việt mặc định.
- Có tìm kiếm, lọc và phân trang khi phù hợp.
- Có trạng thái loading, empty, success và error.
- Có xác nhận trước hành động nguy hiểm.
- Có thông báo lỗi dễ hiểu.
- Các nút phải thực hiện chức năng thật.
- Không hiển thị dữ liệu demo như dữ liệu thực.
- Chức năng chưa hoàn thành phải được ghi rõ.

---

# PHẦN 8 — TECH STACK

Kiểm tra môi trường hiện tại trước khi quyết định triển khai.

Nếu chưa có codebase, mặc định sử dụng:

Frontend:
- React.
- TypeScript.
- Vite.
- Tailwind CSS hoặc component system phù hợp.

Backend:
- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- Alembic.

Database:
- SQLite ban đầu.
- Có khả năng chuyển sang PostgreSQL.
- Database migrations.
- Không lưu trạng thái quan trọng chỉ trong RAM.

Task execution:
- Task queue có trạng thái bền vững.
- Timeout, retry, cancellation, log và chống chạy trùng.
- Ưu tiên giải pháp đơn giản trước.
- Chỉ bổ sung Redis/Celery khi có nhu cầu thực tế.

Game:
- Godot 4.
- GDScript.
- Workspace độc lập cho mỗi game.

Tích hợp:
- OpenAI API.
- Anthropic API.
- Telegram Bot API.
- Công cụ tạo hình ảnh và âm thanh qua adapter.
- Analytics, quảng cáo và thanh toán khi được cấu hình.

Git được sử dụng để quản lý phiên bản.

Không đưa thêm công nghệ phức tạp chỉ vì chúng phổ biến. Mỗi dependency phải có lý do sử dụng.

---

# PHẦN 9 — DATABASE

Thiết kế schema và migrations cho các thực thể cần thiết:

- User.
- Role.
- Permission.
- Project.
- ProjectMember.
- Department.
- Agent.
- AgentPermission.
- ProviderConfig.
- ModelConfig.
- RoutingPolicy.
- Task.
- TaskDependency.
- TaskAttempt.
- Approval.
- AuditLog.
- Asset.
- AssetVersion.
- AssetLicense.
- ProjectDocument.
- GameBuild.
- TestCase.
- TestRun.
- Budget.
- UsageRecord.
- CostRecord.
- RevenueRecord.
- Notification.
- IntegrationConfig.
- AnalyticsReport.

Bảo đảm:

- Khóa chính, khóa ngoại và quan hệ hợp lý.
- Created_at và updated_at ở các bảng cần thiết.
- Trạng thái và ràng buộc dữ liệu rõ ràng.
- Index phù hợp.
- Lịch sử thay đổi cho nghiệp vụ quan trọng.
- Không lưu API key dạng văn bản thô.
- Có migration và hướng dẫn backup/restore.

Không tạo schema chỉ để trang trí; phải gắn với các chức năng thực tế theo từng giai đoạn.

---

# PHẦN 10 — BẢO MẬT VÀ NGÂN SÁCH

Các biến môi trường dự kiến:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `TELEGRAM_BOT_TOKEN`

Tạo `.env.example` với giá trị giả, không chứa secret thật.

Bắt buộc:

- Không đưa API key lên frontend.
- Không commit `.env`.
- Không ghi khóa đầy đủ vào log.
- Che khóa trong giao diện.
- Không gửi dữ liệu nhạy cảm đến provider chưa được cho phép.
- Có phân quyền backend.
- Có audit log.
- Có backup và khả năng khôi phục.
- Không cho Agent tùy ý truy cập toàn bộ ổ đĩa.
- Không chạy lệnh shell nguy hiểm không kiểm soát.
- Không tự ý xóa dữ liệu quan trọng.
- Có Emergency Stop.

Ngân sách phải hỗ trợ theo:

- Toàn studio.
- Dự án.
- Phòng ban.
- Provider.
- Model.
- Nhiệm vụ.

Cần có hạn mức theo ngày/tháng, cảnh báo, ước tính chi phí, theo dõi usage, giới hạn số lần gọi, timeout và chặn tác vụ khi vượt ngân sách.

Nếu không lấy được giá hoặc usage chính xác, không bịa số tiền. Đánh dấu rõ chi phí ước tính.

Các hành động cần phê duyệt gồm chi tiền, mua dịch vụ, phát hành công khai, đăng bài công khai, xóa dữ liệu quan trọng và thay đổi quyền truy cập.

---

# PHẦN 11 — KIẾM TIỀN VÀ PHÁT HÀNH

Thiết kế khả năng tích hợp:

- Rewarded ads.
- Interstitial ads.
- Banner ads khi phù hợp.
- In-app purchases.
- Vật phẩm, trang phục, nâng cấp.
- Analytics.
- Crash reporting.
- Theo dõi doanh thu và chi phí.
- Chuẩn bị App Store Connect và Google Play Console.

Yêu cầu:

- Có chế độ development/test.
- Không ghi nhận giao dịch thành công nếu chưa được xác nhận.
- Không giả lập doanh thu thật.
- Không tự động mua dịch vụ.
- Không tự phát hành khi chưa được duyệt.
- Tuân thủ chính sách nền tảng, quảng cáo, thanh toán và quyền riêng tư.

Mọi tích hợp thương mại cần có trạng thái cấu hình, kiểm tra kết nối và xử lý lỗi rõ ràng.

---

# PHẦN 12 — BẢN QUYỀN VÀ QUYỀN SỬ DỤNG

Tạo hồ sơ nguồn gốc tài sản gồm:

- Asset ID.
- Tên tài sản.
- Dự án.
- Nguồn tạo.
- Tác giả hoặc nhà cung cấp nếu biết.
- Giấy phép.
- Quyền thương mại.
- Phiên bản.
- Đường dẫn.
- Trạng thái phê duyệt.
- Bằng chứng hoặc tài liệu nguồn.

Mọi game phải có thiết kế riêng. Không sao chép nguyên mẫu tài sản hoặc nội dung độc quyền của sản phẩm thương mại khác.

Không mặc định rằng nội dung do AI tạo luôn được phép sử dụng thương mại. Các vấn đề quan trọng phải được rà soát trước phát hành.

---

# PHẦN 13 — LỘ TRÌNH TRIỂN KHAI

## Phase 0 — Audit môi trường

- Kiểm tra hệ điều hành.
- Kiểm tra codebase và cấu trúc thư mục.
- Kiểm tra Python, Node.js, Git, Godot và dependency.
- Kiểm tra chức năng đã có.
- Xác định lỗi, rủi ro và giả định.
- Không ghi đè hoặc xóa dự án hiện tại.
- Lập kế hoạch triển khai và tiêu chí nghiệm thu.

## Phase 1 — Core Platform

Triển khai:

- Backend FastAPI.
- Frontend dashboard.
- Database và migrations.
- Project management.
- Task Center.
- Agent registry.
- OpenAI adapter.
- Anthropic adapter.
- AI routing.
- Logging.
- Budget controls.
- Authentication và phân quyền.
- Approval Center.
- Audit log.
- `.env.example`.
- Tài liệu cài đặt và vận hành.

Điều kiện nghiệm thu:

- Ứng dụng chạy được.
- Tạo, sửa và xem dự án được.
- Tạo và theo dõi nhiệm vụ được.
- Có chế độ nội bộ không cần API key.
- Khi có key hợp lệ, có thể kiểm tra kết nối và gọi API thật.
- Có timeout, xử lý lỗi và ngân sách.
- Các test quan trọng chạy được.
- Không có chức năng chính chỉ là mockup.

## Phase 2 — Phòng ban AI

Triển khai workflow lần lượt:

1. Market Research.
2. Product & Game Design.
3. Game Development.
4. QA & Testing.
5. Art Studio.
6. Audio Studio.
7. Monetization.
8. Finance.
9. IP & Compliance.
10. Marketing.
11. Analytics.
12. DevOps.
13. Telegram.

## Phase 3 — Một game mẫu hoàn chỉnh

Tạo một game 2D có:

- GDD.
- Gameplay chạy được.
- UI.
- Hình ảnh riêng.
- Âm thanh.
- Lưu tiến trình.
- Kiểm thử.
- Build.
- Báo cáo lỗi.
- Hồ sơ quyền sử dụng tài sản.
- Kế hoạch kiếm tiền phù hợp.

Không sao chép game thương mại hiện có.

## Phase 4 — Commercial Operations

- Tích hợp analytics.
- Tích hợp quảng cáo qua adapter.
- Tích hợp mua hàng nếu cần.
- Dashboard doanh thu và chi phí.
- Checklist phát hành.
- Quy trình phê duyệt của chủ studio.

## Phase 5 — Automation & Scale

- Mở rộng đa dự án.
- Tự động hóa các nhiệm vụ rủi ro thấp.
- Tối ưu định tuyến model.
- Tối ưu chi phí.
- Tích hợp thêm công cụ hình ảnh, âm thanh và video.
- Mở rộng database và queue khi cần.
- Hoàn thiện giám sát và khôi phục.

Không chuyển sang giai đoạn tiếp theo khi các tiêu chí cốt lõi của giai đoạn trước chưa đạt.

---

# PHẦN 14 — QUY TẮC LÀM VIỆC CỦA CLAUDE CODE

## Bước 1: Kiểm tra trước khi sửa

Hãy xác định:

- Thư mục dự án.
- Cấu trúc codebase.
- Công nghệ hiện có.
- Dependency.
- Các chức năng đã triển khai.
- Các test hiện có.
- Các tệp cấu hình quan trọng.

Không giả định dự án đang trống. Không ghi đè codebase mà chưa hiểu cấu trúc.

## Bước 2: Báo cáo và lập kế hoạch

Đưa ra báo cáo ngắn về:

- Những gì đã có.
- Những gì còn thiếu.
- Rủi ro.
- Kế hoạch triển khai Phase 1.
- Các tệp dự kiến tạo hoặc sửa.

Nếu không thiếu thông tin thiết yếu, không dừng lại để hỏi những câu không cần thiết.

## Bước 3: Triển khai thực tế

Bắt đầu thực hiện Phase 1 trực tiếp trong codebase.

- Tạo và chỉnh sửa tệp.
- Cài dependency cần thiết nếu được phép.
- Xây dựng frontend/backend.
- Tạo database migrations.
- Kết nối các module.
- Viết test.
- Cập nhật tài liệu.

Nếu một hành động có rủi ro cao hoặc cần quyền ngoài phạm vi, hãy dừng đúng bước đó, giải thích lý do và yêu cầu phê duyệt.

## Bước 4: Kiểm thử

Chạy các test phù hợp và xác minh:

- Backend khởi động được.
- Frontend chạy được.
- Database hoạt động.
- Tạo và đọc dữ liệu thành công.
- Task state được lưu.
- Routing hoạt động đúng.
- Provider chưa cấu hình được báo rõ.
- API lỗi được xử lý.
- Ngân sách và timeout hoạt động.
- Quyền truy cập được kiểm tra ở backend.

Không tuyên bố test thành công nếu chưa thực sự chạy.

## Bước 5: Sửa lỗi và nghiệm thu

Sửa các lỗi đã phát hiện trong phạm vi an toàn, chạy lại test liên quan và ghi nhận kết quả.

Không bỏ qua lỗi quan trọng hoặc tuyên bố hoàn thành chỉ vì giao diện đã hiển thị.

## Bước 6: Tài liệu

Tạo hoặc cập nhật tối thiểu:

- `README.md`
- `.env.example`
- `.gitignore`
- `docs/ARCHITECTURE.md`
- `docs/AI_ROUTING.md`
- `docs/SECURITY.md`
- `docs/DEVELOPMENT.md`
- `docs/TESTING.md`
- `docs/ROADMAP.md`

Có thể điều chỉnh đường dẫn theo cấu trúc hiện có nhưng phải bảo đảm nội dung tài liệu đầy đủ.

---

# PHẦN 15 — TIÊU CHUẨN CHẤT LƯỢNG

Không được:

- Chỉ tạo giao diện minh họa.
- Giả lập API thành công.
- Bịa số liệu doanh thu, thị trường hoặc chi phí.
- Để nút quan trọng không hoạt động.
- Bỏ qua lỗi kiểm thử.
- Đưa secret vào frontend hoặc Git.
- Tự ý xóa dữ liệu.
- Tự ý phát hành sản phẩm.
- Tự động chi tiền khi chưa được duyệt.
- Tuyên bố chức năng hoàn thành khi chưa có bằng chứng.
- Thêm công nghệ phức tạp không cần thiết.

Mỗi chức năng hoàn thành phải có:

1. Code thực tế.
2. Hành vi xác minh được.
3. Test phù hợp.
4. Xử lý lỗi.
5. Tài liệu liên quan.
6. Báo cáo giới hạn còn lại.

Nếu chưa triển khai được một phần, hãy ghi rõ trạng thái `Not Implemented`, `Blocked` hoặc `Partially Implemented`, kèm lý do và bước tiếp theo.

---

# PHẦN 16 — BÁO CÁO SAU KHI TRIỂN KHAI

Sau khi hoàn thành Phase 1, hãy báo cáo:

1. Cấu trúc thư mục thực tế.
2. Công nghệ đã sử dụng.
3. Các chức năng đã triển khai.
4. Các lệnh cài đặt và chạy.
5. Hướng dẫn cấu hình OpenAI API.
6. Hướng dẫn cấu hình Anthropic API.
7. Cách kiểm tra kết nối provider.
8. Cách tạo dự án và nhiệm vụ đầu tiên.
9. Cách xem ngân sách, log và phê duyệt.
10. Kết quả test thực tế.
11. Lỗi hoặc giới hạn còn tồn tại.
12. Các bước tiếp theo theo thứ tự ưu tiên.

Không cần API key thật để bắt đầu xây dựng và kiểm tra các chức năng quản lý nội bộ.

---

# LỆNH THỰC THI CUỐI CÙNG

Bắt đầu ngay với **Phase 0 — Audit môi trường**, sau đó lập kế hoạch ngắn gọn và thực hiện **Phase 1 — Core Platform**.

Ưu tiên sản phẩm chạy được, kiến trúc rõ ràng, bảo mật, kiểm thử được và có thể mở rộng.

Không dừng ở việc trả về tài liệu. Hãy trực tiếp triển khai các thay đổi an toàn trong codebase.

Nếu môi trường thiếu dependency, quyền truy cập hoặc API key, hãy hoàn thành các phần không bị phụ thuộc, ghi rõ giới hạn và cung cấp hướng dẫn cụ thể.

**Định hướng không thay đổi:** OpenAI ưu tiên tư duy và sáng tạo; Anthropic ưu tiên kỹ thuật và triển khai; AI Orchestrator quản lý sự phối hợp giữa hai bên; chủ studio giữ quyền kiểm soát ngân sách, bảo mật và quyết định quan trọng.

Hãy bắt đầu kiểm tra dự án hiện tại ngay bây giờ.