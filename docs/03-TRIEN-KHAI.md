# Triển khai và trình diễn

## 1. Cài đặt môi trường phát triển

Từ thư mục repository với Python 3.12 và Docker Compose v2:

```bash
bash scripts/setup.sh
bash scripts/start.sh
```

Script setup tạo `.local` trước khi Docker tạo bind mount, tránh thư mục cha thuộc root. PostgreSQL service dùng port 5432 chỉ bind loopback. Nếu cổng đang bận, cấu hình `POSTGRES_PORT` đồng nhất cho Compose và Django (qua `.env` hoặc environment). Tệp `.env` không tự thực thi shell.

Khi đã có database ngoài, không cần container db: điền POSTGRES_* và chạy lần lượt pip, migrate, collectstatic. Quyền quản trị CSDL cần tạo extension `btree_gist` lần đầu; quyền chạy test cần tạo database test. Không chuyển sang SQLite vì ứng dụng dùng các ràng buộc PostgreSQL để chống xung đột.

### Bản Docker

```bash
mkdir -p .local
docker compose up -d --build --wait
docker compose exec web python manage.py seed_demo
docker compose logs --tail=50 web
```

Một số cloud sandbox không có DNS/proxy bên trong build container. Khi đó `bash scripts/build-cloud.sh` tải wheel qua pip trên host với TLS bình thường, sau đó build bằng `PIP_NO_INDEX=1` từ wheel local. Script đã kiểm chứng cho Linux/Python 3.12 cùng kiến trúc CPU với image; không tắt TLS hoặc bỏ kiểm tra checksum. Sau build dùng `docker compose up -d web`.

### Các lệnh hằng ngày

```bash
.venv/bin/python manage.py test salon.tests --noinput
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py collectstatic --noinput
docker compose stop
```

`seed_demo` idempotent: không đặt lại mật khẩu, không nhân đôi lịch mẫu; bổ sung ca cho ngày hiện tại và 30 ngày tới. Lịch mẫu có thời điểm tương đối ở lần nạp đầu; sau nhiều ngày, tổng quan có thể không có lịch mẫu hôm nay nhưng lịch sử vẫn còn. Không xóa dữ liệu để làm mới demo; có thể đặt lịch mới qua giao diện. Không chạy `docker compose down -v` hoặc xóa `.local/pgdata` nếu chưa có backup.

## 2. Kịch bản bảo vệ đồ án khoảng 10 phút

1. Giới thiệu vấn đề chờ đợi, trùng lịch và đối soát doanh thu; chỉ ra ba vai trò.
2. Mở trang chủ, xem ba chi nhánh và bảng giá dịch vụ.
3. Đăng nhập `khachhang`, chọn combo, stylist và ngày; chỉ ra thời lượng ảnh hưởng giờ trống; đặt và xem mã lịch.
4. Mở hai cửa sổ/khách khác nhau cùng chọn một stylist/giờ. Xác nhận một lịch rồi thử lịch còn lại; giải thích server kiểm tra lại khi ghi và DB có exclusion constraint. Có bộ test concurrency thay cho biểu diễn thủ công nếu không muốn tạo nhiều dữ liệu.
5. Tạo một lịch trong ngày, đăng nhập `letan` tại Quận 1, check-in ghế trống, bắt đầu, chọn thẻ mô phỏng và xác nhận. Mở/in phiếu dịch vụ nội bộ.
6. Trở lại đúng tài khoản khách, đánh giá sau hoàn thành; thử thanh toán/đánh giá lặp để thấy bị chặn.
7. Đăng nhập `admin`, xem toàn chuỗi, lọc chi nhánh/ngày, báo cáo và CSV; mở quản trị ca làm, dịch vụ.
8. Đối chiếu kết quả test, ERD, sequence và điểm mở rộng. Nêu rõ dữ liệu và thanh toán là mẫu/mô phỏng.

## 3. Cấu hình production cần hoàn tất

Không coi bản demo đã được vận hành công khai. Trước public deployment:

- Dùng database riêng và mật khẩu đủ mạnh; không nạp seed demo; tạo quản trị viên riêng và phân role/quyền qua Admin.
- Đặt `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` riêng, `DJANGO_ALLOWED_HOSTS` theo domain; có thể thêm `DJANGO_CSRF_TRUSTED_ORIGINS` cho origin HTTPS hợp lệ. Secrets đi qua cơ chế secure settings của hạ tầng, không ghi vào repository.
- Chạy Gunicorn sau reverse proxy HTTPS. Cookies secure và HSTS bật trong chế độ production. Cấu hình trusted proxy header chỉ khi proxy do mình quản lý; nếu chưa trust proxy, kết nối backend HTTPS hoặc cấu hình redirect ở proxy phù hợp.
- Chạy migrate/collectstatic trước khi chuyển traffic, cấp user DB quyền cần thiết rồi thu hồi quyền superuser/CREATEDB ở tài khoản runtime. Tạo extension bằng tài khoản migration có quyền.
- Bổ sung rate limiting đăng nhập, password reset/email xác minh, backup định kỳ, restore test, logging/monitoring và đo tải. Không đưa database ra Internet.

Ví dụ kiểm tra cấu hình (cần các biến production hợp lệ): `python manage.py check --deploy`. Đây là kiểm tra cấu hình, không thay thế kiểm tra bảo mật độc lập hoặc nghiệm thu triển khai thực tế.

## 4. Sao lưu và phục hồi

```bash
mkdir -p .local/backups
docker compose exec -T db pg_dump -U gentleman -d gentleman -Fc > .local/backups/gentleman.dump
```

Lệnh ví dụ giả định tên DB/user mặc định; dùng tên đã cấu hình nếu khác. Backup chứa dữ liệu cá nhân, cần giữ ngoài Git, hạn chế quyền và mã hóa theo hạ tầng. Khôi phục vào database riêng để kiểm tra trước khi tác động database đang dùng. Quy trình khôi phục thực tế chưa được nghiệm thu trong phạm vi lần build này.

## 5. Bảo trì và mở rộng

Muốn thêm VNPay/MoMo cần tách PaymentTransaction, trạng thái pending/success/failure, chữ ký callback, idempotency key, đối soát và chính sách hoàn tiền; không đổi tên MockPayment rồi coi là thanh toán thật. Muốn thông báo email/SMS cần transactional outbox và worker. Muốn đổi lịch cần một use case nguyên tử kiểm tra lịch mới và giữ lịch cũ khi thất bại. Muốn stylist chuyển chi nhánh cần lịch sử phân công thay vì sửa FK của nhân sự đang có lịch sử.

## 6. Tài liệu tham khảo kỹ thuật

1. Django Software Foundation, Django 5.2 documentation: https://docs.djangoproject.com/en/5.2/
2. Django PostgreSQL constraints: https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/constraints/
3. PostgreSQL, Range Types: https://www.postgresql.org/docs/17/rangetypes.html
4. PostgreSQL, Explicit Locking: https://www.postgresql.org/docs/17/explicit-locking.html
5. Docker Compose documentation: https://docs.docker.com/compose/
6. Playwright Python documentation: https://playwright.dev/python/

Các liên kết là nguồn tham chiếu kỹ thuật của công nghệ triển khai, không phải số liệu khảo sát doanh nghiệp. Tài liệu đầu vào do người dùng cung cấp là cơ sở phạm vi nghiệp vụ.
