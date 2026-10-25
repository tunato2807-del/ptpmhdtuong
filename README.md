# GENTLEMAN — Quản lý và đặt lịch chuỗi cắt tóc nam

Dự án tiếng Việt dùng Django 5.2 LTS, PostgreSQL và giao diện riêng bằng HTML/CSS/JavaScript. Có trang khách hàng, trang cá nhân và cổng quản lý với chức năng thêm/sửa/xóa. Toàn bộ danh mục được quản lý tại `/quan-ly/thiet-lap/`; không dùng Django Admin. Chạy trực tiếp trên VS Code, không cần Docker hoặc Node.js.

Xem [bản cập nhật animation và ảnh tự chuyển](docs/09-ANIMATION-VA-ANH-TU-CHUYEN.md) để copy 5 file bổ sung.

## Copy từng file để cập nhật bản đang có

Mở [hướng dẫn cập nhật từng file](docs/08-CAP-NHAT-TUNG-FILE.md). Hướng dẫn có đường dẫn trực tiếp tới toàn bộ CSS, template và Python cần copy, theo đúng thứ tự. Bản này có nút Đăng xuất rõ ràng trên đầu trang khách hàng/quản lý, kiểm tra file giao diện bị thiếu, và chỉnh phông chữ ở một số vị trí cụ thể.

Tìm kiếm, phân trang, xem chi tiết CRUD, nhập Excel có xem trước/xác nhận, xuất Excel/PDF/CSV, đổi và hủy lịch nằm trong `salon/features.py`; HTML được tách đầy đủ trong `templates/features/`. Không cần dùng lại script nâng cấp một file đã gửi trước đó.

## Chạy trên Windows bằng VS Code

Cần Python 3.12–3.14 (64-bit) và PostgreSQL 17 đã chạy. pgAdmin là công cụ quản lý PostgreSQL, không thay thế máy chủ database. Python 3.14 của bạn dùng được; các lệnh dùng `python`, không yêu cầu launcher `py`.

1. Mở thư mục chứa `manage.py` trong VS Code. Chọn Terminal → New Terminal → PowerShell.
2. Trong pgAdmin, tạo database `gentleman`, owner là tài khoản PostgreSQL của bạn (thường là `postgres`).
3. Tạo môi trường và cài thư viện:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Chỉ sao chép khi chưa có `.env`; nếu đã có thì giữ lại và sửa thông tin kết nối. Mở `.env` (cùng thư mục `manage.py`) và điền:

```dotenv
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
POSTGRES_DB=gentleman
POSTGRES_USER=postgres
POSTGRES_PASSWORD=MAT_KHAU_POSTGRES_CUA_BAN
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Thay `MAT_KHAU_POSTGRES_CUA_BAN` bằng mật khẩu PostgreSQL thực tế, không dùng mật khẩu tài khoản web. Nếu PostgreSQL dùng cổng khác, sửa port. File `.env` được bỏ qua trong Git; file `.env.example` chỉ là mẫu. Không gửi mật khẩu vào chat hoặc commit.

4. Kiểm tra và khởi tạo:

```powershell
.\.venv\Scripts\python.exe manage.py check_database
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

Mở `http://127.0.0.1:8000/` trên máy của bạn. Giữ terminal mở; Ctrl+C để dừng. Nếu một lệnh lỗi, xử lý tại lệnh đó trước khi chạy tiếp. Không tạo bảng thủ công: migration tạo bảng và extension `btree_gist` (tài khoản PostgreSQL phải có quyền tạo extension).

Lần sau chỉ cần PostgreSQL đang chạy và lệnh `runserver`. Trong VS Code, Ctrl+Shift+P → Python: Select Interpreter → chọn `.venv/Scripts/python.exe`. Có cấu hình F5 **GENTLEMAN: Django** để chạy/debug sau khi đã thiết lập.

## Lệnh hỗ trợ đa nền tảng

Sau khi đã cấu hình `.env` và database:

```powershell
python scripts/dev.py setup
python scripts/dev.py start
python scripts/dev.py check
```

`setup` chỉ tạo `.venv` khi thiếu, cài thư viện, kiểm tra kết nối, migrate, nạp mẫu và collectstatic. Nếu thiếu `.env`, script tạo bản mẫu và dừng để bạn điền mật khẩu rồi chạy lại. Dùng `--no-demo` để bỏ nạp dữ liệu mẫu. Script không cài hoặc khởi động dịch vụ PostgreSQL của máy bạn.

Trên Linux/macOS, dùng `python3` thay `python`; `bash scripts/setup.sh`, `start.sh`, `check.sh` là các lệnh bọc tương đương. Đổi cổng web bằng `python scripts/dev.py start --port 8001`. Server mặc định chỉ lắng nghe loopback.

## Tài khoản và các màn hình

| Vai trò | Tên đăng nhập | Mật khẩu demo |
|---|---|---|
| Quản trị | `admin` | `Gentleman@2026` |
| Lễ tân Quận 1 | `letan` | `Gentleman@2026` |
| Khách hàng | `khachhang` | `Gentleman@2026` |

Tài khoản mẫu chỉ dùng để trình diễn. `seed_demo` chỉ chạy khi DEBUG=1, không đặt lại mật khẩu tài khoản đã có, không nhân đôi lịch mẫu; chạy lại bổ sung ca cho ngày hiện tại và 30 ngày tới.

| Đường dẫn | Chức năng |
|---|---|
| `/` | Khám phá ảnh thật, dịch vụ, chi nhánh, stylist, đặt lịch nhanh |
| `/tai-khoan/` | Sửa họ tên, điện thoại, email; đổi mật khẩu có xác nhận mật khẩu hiện tại |
| `/dat-lich/` | Chọn nhiều dịch vụ, stylist và khung giờ trống |
| `/lich-cua-toi/` | Lịch hẹn, lịch sử, điểm và thông báo |
| `/quan-ly/` | Tổng quan vận hành và thao tác theo lịch hẹn |
| `/quan-ly/thiet-lap/` | Quản trị riêng: dịch vụ, chi nhánh, stylist, ghế, ca làm, tài khoản |
| `/quan-ly/bao-cao/` | Lọc doanh thu, phân trang và xuất Excel/PDF/CSV |
| `/tim-kiem/` | Tìm dịch vụ, chi nhánh, stylist |

Quản trị viên quản lý nguồn lực bằng nút Thêm, Sửa, Xóa trên giao diện riêng. Quyền dựa vào vai trò `manager`, không cần cờ Django staff/superuser. Lễ tân xem và vận hành trong chi nhánh phụ trách, không được chỉnh thiết lập. Khách chỉ sửa hồ sơ của mình; không tự sửa vai trò hoặc điểm.

Xóa yêu cầu xác nhận và POST/CSRF. Bản ghi có liên kết lịch hẹn/hóa đơn được bảo vệ; có thể ngừng hoạt động khi không còn lịch đang cần phục vụ. Không xóa ca làm đang bao phủ lịch hẹn, không chuyển chi nhánh của stylist/ghế bằng sửa thông tin. Không thể khóa, hạ quyền hoặc xóa tài khoản quản trị đang đăng nhập. Giá/thời lượng trong lịch hẹn là snapshot và giữ nguyên khi sửa danh mục.

## Cập nhật từ phiên bản trước

Giữ `.env` và database hiện có. Dừng web cũ, cập nhật mã, cài lại `requirements.txt`, chạy migrate và collectstatic rồi bật lại web. Không cần xóa database hoặc chạy lại seed để cập nhật. Bản quản trị riêng không thêm migration mới; `0002_vietnamese_column_names` vẫn đổi tên cột tại chỗ khi nâng cấp từ bản rất cũ. Các bảng kỹ thuật đã có trong database được giữ lại, không xóa dữ liệu lịch sử.

Nếu thay thư mục bằng ZIP mới, nhớ sao chép `.env` của bạn vào thư mục mới. Không đặt `.env` trong `.venv`. Dữ liệu PostgreSQL lưu trên máy chủ, không nằm trong ZIP.

## Kiểm thử

```powershell
python scripts/dev.py check
```

81 kiểm thử hiện tại dùng PostgreSQL thực và database test riêng. Tài khoản PostgreSQL chạy tests cần quyền CREATEDB và tạo `btree_gist`. Lệnh check thu thập static trước tests để manifest nhận đủ ảnh/font/CSS mới.

Browser checks tùy chọn, cần server local DEBUG=1 có dữ liệu mẫu. `scripts/interface_smoke.py` kiểm tra bố cục, CSS/font, biểu tượng và đăng xuất ở sáu kích thước màn hình. Các kiểm tra khác:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts/browser_smoke.py
.\.venv\Scripts\python.exe scripts/customer_ui_smoke.py
.\.venv\Scripts\python.exe scripts/management_smoke.py
```

Có thể đặt `BROWSER_EXECUTABLE` nếu đã có Chromium. Browser smoke nghiệp vụ và quản trị tạo dữ liệu riêng rồi dọn đúng bản ghi của nó. Không chạy trên hệ thống production. GitHub Actions dùng PostgreSQL native và ma trận Python 3.12/3.14; trạng thái chạy trên GitHub cần xem tab Actions.

## Tài liệu và cấu trúc

- [Phân tích yêu cầu](docs/01-PHAN-TICH.md), [thiết kế](docs/02-THIET-KE.md), [triển khai](docs/03-TRIEN-KHAI.md), [kiểm thử](docs/04-KIEM-THU.md).
- [80 tên cột tiếng Việt](docs/05-TEN-COT-DU-LIEU.md), [giao diện khách hàng](docs/06-GIAO-DIEN-KHACH-HANG.md), [quản trị và trang cá nhân](docs/07-QUAN-TRI-RIENG.md).
- [Báo cáo Word](docs/BAO_CAO_PHAN_TICH_THIET_KE.docx), [nguồn ảnh/font](docs/NGUON-TAI-NGUYEN.md).

`salon/management_views.py` xử lý CRUD, `salon/profile_views.py` xử lý hồ sơ/mật khẩu, `salon/forms.py` kiểm tra dữ liệu, `salon/services.py` xử lý đặt lịch/thanh toán có transaction. `templates/staff/` chứa cổng quản lý riêng; `static/css/management.css` định dạng các màn hình mới. `scripts/dev.py` chạy được trên Windows/Linux/macOS.

Ứng dụng phục vụ học tập, chưa triển khai công khai. Thanh toán thẻ là mô phỏng; chưa tích hợp ngân hàng, SMS/email, tải lớn hoặc phục hồi mật khẩu qua email. Ảnh chụp là ảnh minh họa trải nghiệm; thông tin demo không đại diện cửa hàng thực.
