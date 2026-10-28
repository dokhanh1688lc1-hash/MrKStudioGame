# Mẫu báo cáo lỗi

- **Tiêu đề:** (một câu)
- **Mức độ:** low / medium / high / critical (critical = crash, mất dữ liệu, không chơi được)
- **Phiên bản/build:** 
- **Bước tái hiện:** 1… 2… 3…
- **Kết quả thực tế:** 
- **Kết quả mong đợi:** 
- **Tần suất:** luôn / thỉnh thoảng / một lần
- **Môi trường:** hệ điều hành, GPU, độ phân giải
- **Bằng chứng:** ảnh chụp/video/log

Ghi lỗi vào nền tảng: Phòng QA → test case tương ứng → Failed (nhập mô tả + mức độ). Sau khi sửa, chạy lại và ghi Passed để xác nhận.
