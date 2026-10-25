# Triển khai và chạy trực tiếp

## 1. Điều kiện

Python 3.12–3.14 64-bit và PostgreSQL 17. pgAdmin dùng để tạo database và quản lý tài khoản PostgreSQL; ứng dụng kết nối trực tiếp qua host/port trong `.env`. Không cần công cụ container. Đọc README để làm theo từng bước bằng PowerShell trên VS Code.

Trong pgAdmin: kết nối server → Databases → Create → Database, đặt tên `gentleman`, owner là tài khoản PostgreSQL của bạn. Tài khoản migration cần quyền tạo bảng và extension `btree_gist`. Các bảng ứng dụng không tạo bằng tay.

## 2. Windows / VS Code

Mở đúng thư mục có `manage.py`. Trong terminal PowerShell:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Chỉ sao chép khi chưa có `.env`. Giữ file cấu hình cũ khi cập nhật mã. Điền tên database, username, mật khẩu PostgreSQL và port thực tế vào `.env`. Username thường là `postgres`, không phải tên database `gentleman`. Mật khẩu PostgreSQL khác mật khẩu tài khoản web và mật khẩu mở ứng dụng pgAdmin.

```powershell
.\.venv\Scripts\python.exe manage.py check_database
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

Mở `http://127.0.0.1:8000/` trên máy cá nhân. Ctrl+C dừng web. Những lần sau chỉ cần PostgreSQL đang chạy và lệnh runserver. Trong VS Code chọn interpreter `.venv/Scripts/python.exe`; F5 cấu hình GENTLEMAN: Django cũng chạy được sau khi đã cài dependencies và cấu hình DB.

Lệnh hỗ trợ tương đương: `python scripts/dev.py setup`, `python scripts/dev.py start`, `python scripts/dev.py check`. Chúng gọi trực tiếp Python và không quản lý dịch vụ database. Setup tạo `.env` mẫu và dừng nếu thiếu file, không tự đoán mật khẩu.

## 3. Linux / macOS và môi trường cloud

Dùng PostgreSQL đang có, cấu hình `.env`, rồi chạy `python3 scripts/dev.py setup` và `python3 scripts/dev.py start`. Có các wrapper bash trong scripts. Cổng web tùy chọn: `--port 8001`; host tùy chọn cho môi trường phát triển được quản lý: `--host 0.0.0.0`. Mặc định loopback.

Mỗi cloud task đã cách ly, dùng checkout `/workspace/ptpmhdtuong`; không tạo Git worktree khi chưa có yêu cầu. Không giả định process cũ còn chạy. Cấu hình môi trường cloud có hướng dẫn khởi động PostgreSQL native đã chuẩn bị bên ngoài repository. Các binary database và dữ liệu cloud không được đóng gói vào ZIP mã nguồn.

## 4. Nâng cấp và bảo toàn dữ liệu

Dừng web, giữ `.env` và database, cập nhật mã, cài lại requirements, migrate, collectstatic và khởi động lại. Không nạp lại demo để nâng cấp. Bản quản trị riêng không thêm bảng/cột hoặc migration mới. Migration 0002 đổi tên 80 cột nghiệp vụ sang tiếng Việt không dấu, giữ kiểu dữ liệu và dữ liệu. Không sửa migration 0001 đã áp dụng.

`seed_demo` chỉ DEBUG=1, không đổi mật khẩu tài khoản đã có và không nhân đôi lịch mẫu. Chạy lại có thể bổ sung ca làm cho hiện tại và 30 ngày tới. Lịch mẫu cũ vẫn giữ ngày gốc; tạo lịch mới để trình diễn ở ngày hiện tại.

## 5. Sử dụng cổng quản lý riêng

Đăng nhập `admin` → Thiết lập & nhân sự (`/quan-ly/thiet-lap/`). Quản lý trực tiếp dịch vụ, chi nhánh, stylist, ghế, ca làm và tài khoản. Có tìm kiếm, phân trang, tạo, sửa và xác nhận xóa. Quyền dựa vào vai trò manager. Không cần bật staff/superuser hoặc truy cập trang quản trị có sẵn của framework.

Mọi người đăng nhập đều có trang `/tai-khoan/` để sửa họ tên/điện thoại/email và đổi mật khẩu. Đổi mật khẩu yêu cầu mật khẩu hiện tại và giữ phiên đăng nhập hiện tại. Vai trò, điểm và quyền không sửa từ trang cá nhân.

Bản ghi gắn với lịch sử được bảo vệ. Ca làm có lịch hẹn không được xóa/thu hẹp; ghế/stylist có lịch đang hoạt động không ngừng đột ngột; chi nhánh không được đổi giờ làm mất phạm vi phục vụ. Giá danh mục mới không sửa snapshot trong lịch cũ.

## 6. Xử lý lỗi thường gặp

| Thông báo | Kiểm tra |
|---|---|
| Không nhận lệnh py | Dùng `python`, hoặc VS Code → Python: Create Environment → Venv |
| Không nhận python | Chọn interpreter trong VS Code; kiểm tra cài đặt/PATH của Python |
| Password authentication failed | Sửa đúng `.env`, đúng username/password PostgreSQL; không sửa `.env.example` |
| Vẫn dùng username cũ | Kiểm tra biến môi trường POSTGRES_USER/POSTGRES_PASSWORD đang ghi đè file; không in mật khẩu ra terminal |
| Connection refused | Kiểm tra dịch vụ PostgreSQL, host và port |
| Database does not exist | Tạo database gentleman trong pgAdmin |
| Permission denied for extension | Nhờ tài khoản quản trị PostgreSQL tạo btree_gist trong database đích hoặc cấp quyền thích hợp |
| Missing staticfiles manifest entry | Chạy collectstatic sau khi cập nhật mã |
| Cổng 8000 bận | Dùng runserver 8001 hoặc dev.py start --port 8001 |

## 7. Backup và giới hạn

Dùng chức năng Backup/Restore của pgAdmin. Hoặc khi PostgreSQL client nằm trong PATH: `pg_dump -h 127.0.0.1 -U postgres -d gentleman -Fc -f gentleman.dump`; công cụ hỏi mật khẩu riêng. Không đưa backup/mật khẩu vào Git. Chỉ thử restore vào database riêng trước khi dùng với dữ liệu thật. Việc xóa mã nguồn không xóa dữ liệu của máy chủ PostgreSQL.

Đây là bản phát triển/trình diễn. Runserver không phải dịch vụ production. Triển khai công khai cần máy chủ ứng dụng phù hợp, HTTPS, secret riêng, cấu hình host, backup và giám sát; chưa được tuyên bố đã thực hiện.


## Email, điểm và sao lưu

Bản mới cần migrate 0003/0004. Hướng dẫn SMTP/local email, lịch sử/sử dụng điểm, lịch tuần và lệnh backup/restore có đối chiếu tại [Hoàn thiện chức năng](11-HOAN-THIEN-CHUC-NANG.md). Không tự cài SMTP hoặc lịch sao lưu trên máy người dùng.
