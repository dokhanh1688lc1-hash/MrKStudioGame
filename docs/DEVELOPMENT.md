# Phát triển

```
cd backend && python -m uvicorn app.main:app_factory --factory --reload      # API :8000
cd frontend && npm run dev                                                    # UI :5173, proxy /api → :8000
```
- Cấu hình: `.env` (xem `.env.example`). `DATABASE_URL` đổi được sang PostgreSQL (cần cài driver); chưa kiểm thử trên PostgreSQL.
- **Migrations (Alembic)**: schema do `backend/migrations/` quản lý, tự chạy `upgrade head` khi khởi động. Database cũ tạo trước khi có Alembic được `stamp` về baseline `0001`. Khi sửa `app/models.py`:
  ```
  cd backend && python -c "from sqlalchemy import create_engine; from alembic import command; from app.migrate import make_config; e=create_engine('sqlite:///tmp_mig.db'); c=e.connect(); command.upgrade(make_config(c),'head'); command.revision(make_config(c), message='mo ta', autogenerate=True); c.commit()"
  ```
  rồi kiểm tra file sinh ra trong `migrations/versions/`. Test `test_migration_matches_models` sẽ fail nếu models và migration lệch nhau. Ứng dụng tự sao lưu database trước khi migrate.
- Thêm provider: kế thừa `providers.base.Provider` (xem `providers/cli_providers.py`), đăng ký trong `ProviderRegistry`, thêm tên vào danh sách `ProviderConfig` ở `seed.py`.
- Thêm phòng ban: thêm vào `DEPARTMENTS` trong `services/seed.py`.
- Mỗi dependency có lý do: fastapi/uvicorn (web), sqlalchemy + alembic (DB), pytest (test); python-multipart (nhận tệp tải lên). Không dùng Redis/Celery vì hàng đợi đơn giản trong DB là đủ ở quy mô hiện tại.
