# Phát triển

```
cd backend && python -m uvicorn app.main:app_factory --factory --reload      # API :8000
cd frontend && npm run dev                                                    # UI :5173, proxy /api → :8000
```
- Cấu hình: `.env` (xem `.env.example`). `DATABASE_URL` đổi được sang PostgreSQL (cần cài driver); chưa kiểm thử trên PostgreSQL.
- **Migrations**: Phase 1 tạo bảng bằng `Base.metadata.create_all`. Chưa có Alembic migrations — *Partially Implemented*. Trước khi thay đổi schema ở dữ liệu thật, thêm Alembic (`alembic init`, autogenerate từ `app.models.Base`).
- Thêm provider: kế thừa `providers.base.Provider`, đăng ký trong `ProviderRegistry`, thêm dòng `ProviderConfig` ở `seed.py`.
- Thêm phòng ban: thêm vào `DEPARTMENTS` trong `services/seed.py`.
- Mỗi dependency có lý do: fastapi/uvicorn (API), sqlalchemy (DB), httpx (gọi provider + test), pytest (test). Không dùng Redis/Celery vì hàng đợi đơn giản trong DB là đủ ở quy mô hiện tại.
