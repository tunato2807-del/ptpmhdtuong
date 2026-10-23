# GENTLEMAN — Hệ thống quản lý và đặt lịch chuỗi cắt tóc nam

Bản web tiếng Việt được xây dựng lại từ đầu dựa trên đề tài của Tô Hoàng Tuấn (1250080221). Django 5.2 LTS, Python 3.12+, PostgreSQL 17; giao diện responsive bằng Django Templates, CSS và JavaScript thuần. Không cần Node.js để chạy ứng dụng.

## Chạy nhanh

Yêu cầu: Python 3.12+, Docker Engine và Docker Compose v2. Máy Windows nên chạy trong WSL2 hoặc dùng cách Docker bên dưới. Chạy từ thư mục repository:

```bash
bash scripts/setup.sh
bash scripts/start.sh
```

`setup.sh` tạo virtualenv, cài phiên bản thư viện đã ghim, bật PostgreSQL, migrate, nạp dữ liệu mẫu và collectstatic. `start.sh` khởi động PostgreSQL và Django trên cổng 8000, có tự tải lại khi sửa mã. Truy cập cổng 8000 trên máy của bạn. Kiểm tra sức khỏe bằng `curl -fsS 127.0.0.1:8000/health/`.

Trong Codex Cloud, dùng checkout đang có tại `/workspace/ptpmhdtuong`. Mỗi task đã được cách ly; không cần tạo Git worktree. Quy trình khởi động đã được lưu riêng trong cấu hình môi trường. Không coi tiến trình của task cũ là còn chạy.

### Tài khoản demo

| Vai trò | Tên đăng nhập | Mật khẩu mẫu |
|---|---|---|
| Quản trị hệ thống | `admin` | `Gentleman@2026` |
| Lễ tân Quận 1 | `letan` | `Gentleman@2026` |
| Khách hàng | `khachhang` | `Gentleman@2026` |

Đây là thông tin công khai dành riêng cho dữ liệu trình diễn. Không dùng tài khoản/mật khẩu mẫu trên hệ thống công khai. `seed_demo` chỉ chạy khi `DJANGO_DEBUG=1`, không đặt lại mật khẩu của tài khoản đã tồn tại. Các khách `demo-customer-*` không có mật khẩu đăng nhập.

### Docker toàn bộ ứng dụng

```bash
mkdir -p .local
docker compose up -d --build --wait
docker compose exec web python manage.py seed_demo
```

Web dùng Gunicorn 2 workers, PostgreSQL lưu ở `.local/pgdata`, static được phục vụ bởi WhiteNoise. Trong cloud sandbox nếu Docker không ghi được cache ở thư mục người dùng, dùng `export DOCKER_CONFIG="$PWD/.local/docker"` trước khi build. Không chạy đồng thời web Docker và Django local trên cùng cổng 8000; dừng tiến trình local trước, hoặc chỉ khởi động service `db` khi phát triển bằng virtualenv.

## Chức năng đã xây dựng

**Khách hàng:** đăng ký/đăng nhập/đăng xuất; xem chi nhánh, dịch vụ và stylist; chọn nhiều dịch vụ/combo, stylist, ngày và giờ trống; đặt/hủy lịch; xem lịch sử, thông báo nội bộ, điểm thành viên; xem/in phiếu dịch vụ; đánh giá sau khi hoàn thành.

**Lễ tân:** xem lịch, khách hàng, báo cáo thuộc chi nhánh phụ trách; đặt cho khách đã từng có lịch tại chi nhánh; check-in và phân ghế; bắt đầu phục vụ; thanh toán tiền mặt hoặc thẻ mô phỏng; ghi nhận khách không đến. Khách lần đầu có thể tự đăng ký và đặt lịch. Lễ tân không được chỉnh danh mục hoặc xem dữ liệu chi nhánh khác.

**Quản trị:** tổng quan toàn chuỗi; bộ lọc ngày/chi nhánh/trạng thái/tên hoặc điện thoại; ca làm và lịch stylist; báo cáo doanh thu thực thu, giá trị trung bình hóa đơn, xuất CSV. Tài khoản quản trị hệ thống có giao diện Django Admin để quản lý chi nhánh, ghế, nhân viên, ca làm, danh mục và tài khoản. Lịch hẹn, hóa đơn và nhật ký chỉ đọc trong Admin; thay đổi trạng thái qua luồng nghiệp vụ để giữ tính nhất quán.

**Toàn vẹn:** transaction và khóa theo chi nhánh; PostgreSQL GiST exclusion constraints chống trùng stylist, ghế, ca làm; kiểm tra khách trùng lịch giữa các chi nhánh; lưu giá và thời lượng lúc đặt; một hóa đơn/một đánh giá cho mỗi lịch; điểm chỉ cộng một lần. Giá là số nguyên VNĐ; thời gian lưu UTC, hiển thị Asia/Ho_Chi_Minh.

## Quy tắc nghiệp vụ

- Đặt tối đa 30 ngày tới, bước 15 phút; toàn bộ dịch vụ phải nằm trong giờ mở cửa và một ca làm của stylist.
- Nhiều dịch vụ được cộng giá và thời lượng. Combo là một dịch vụ gói có giá/thời lượng riêng, không tự tách thành dịch vụ con.
- Khoảng hẹn là `[bắt đầu, kết thúc)`: hai lịch sát nhau được phép. Chỉ `booked`, `checked_in`, `in_service` giữ chỗ.
- Chỉ check-in lịch trong ngày; ghế phải thuộc chi nhánh và không đang được sử dụng. Một stylist không bắt đầu phục vụ hai khách cùng lúc, kể cả khi lịch cũ kéo dài quá giờ.
- Chỉ thanh toán từ trạng thái đang phục vụ; giao dịch, trạng thái, điểm và sự kiện được lưu nguyên tử. Thanh toán lặp bị từ chối.
- Khách chỉ hủy lịch chưa check-in, trước ít nhất 2 giờ. Lễ tân có thể hủy lịch chưa check-in trong phạm vi mình phụ trách. Không đến chỉ được ghi nhận sau giờ kết thúc dự kiến.
- Báo cáo dùng thời gian thanh toán, không lấy giá danh mục hiện hành. Không có thuế/chiết khấu/hoàn tiền trong phiên bản này.
- Mỗi 10.000 ₫ thanh toán nhận 1 điểm, làm tròn xuống theo hóa đơn. Điểm hiện chỉ ghi nhận thành viên, chưa đổi quà.

## Kiểm thử và build

```bash
bash scripts/check.sh
docker compose build web
```

Các kiểm thử dùng database `test_gentleman` riêng, không xóa dữ liệu phát triển. User PostgreSQL chạy test cần quyền `CREATEDB` và tạo extension `btree_gist` (image demo đã có). Xem kết quả đã thực thi trong `docs/04-KIEM-THU.md`.

Kiểm tra giao diện/luồng trình duyệt tùy chọn:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/browser_smoke.py
```

Ứng dụng ở cổng 8000 phải đang chạy với dữ liệu demo. Có thể đặt `BROWSER_EXECUTABLE` để dùng Chromium cài sẵn. Script tạo tài khoản kiểm thử riêng, kiểm tra luồng đặt, hủy, check-in, thanh toán, hóa đơn, đánh giá và responsive; sau đó xóa đúng các bản ghi do tài khoản này tạo trong database local. Không chạy script này với một hệ thống production.

## Tài liệu

Bản Word tổng hợp: [Báo cáo phân tích, thiết kế và triển khai](docs/BAO_CAO_PHAN_TICH_THIET_KE.docx). Trong Word, cập nhật trường để tạo mục lục/số trang theo máy đang dùng. File nguồn được xuất bằng `scripts/export_report.py` (cần python-docx 1.2.0 và các ảnh sơ đồ PNG).

1. [Phân tích yêu cầu, phạm vi và use case](docs/01-PHAN-TICH.md)
2. [Thiết kế kiến trúc, dữ liệu, UML và giao diện](docs/02-THIET-KE.md)
3. [Hướng dẫn triển khai và trình diễn](docs/03-TRIEN-KHAI.md)
4. [Kết quả kiểm thử](docs/04-KIEM-THU.md)
5. [80 tên cột tiếng Việt và kiểu dữ liệu](docs/05-TEN-COT-DU-LIEU.md)

Sơ đồ Mermaid gốc nằm trong `docs/diagrams/`, ảnh giao diện trong `docs/screenshots/`. Bộ báo cáo và mã nguồn là hai phần của cùng một dự án; các mô tả tính năng dựa trên mã hiện có, không coi các khẳng định hoàn thành trong tài liệu đầu vào là kết quả kiểm thử.

## Tên thuộc tính trong bảng dữ liệu

Cột PostgreSQL trong 12 bảng nghiệp vụ dùng tiếng Việt viết liền không dấu: `hoten`, `sodienthoai`, `machinhanh`, `thoigianbatdau`, `trangthai`… Kiểu dữ liệu và dữ liệu hiện có được giữ nguyên. Django dùng `db_column` để ánh xạ, vì vậy tên thuộc tính Python và giao thức đăng nhập/API vẫn tương thích. Các bảng kỹ thuật của Django giữ quy ước framework.

Nếu đã cài bản trước, chạy `.venv/bin/python manage.py migrate --noinput` để áp dụng `0002_vietnamese_column_names`. Migration đổi tên tại chỗ, có thể hoàn tác; không xóa database hoặc nạp lại dữ liệu. Chi tiết và kiểu dữ liệu từng cột có trong `docs/05-TEN-COT-DU-LIEU.md`.

## Cấu trúc

```text
config/                  Cấu hình Django, URL gốc, WSGI
salon/models.py          Mô hình dữ liệu và ràng buộc PostgreSQL
salon/services.py        Đặt lịch, chuyển trạng thái, thanh toán
salon/events.py          Publisher + Observer (nhật ký, thông báo)
salon/forms.py           Kiểm tra dữ liệu nhập
salon/views.py           Quyền truy cập, truy vấn và HTTP
salon/admin.py           Quản trị danh mục và ca làm
salon/tests/             Kiểm thử nghiệp vụ, HTTP, concurrency
templates/ static/       Giao diện và tài nguyên local
scripts/                 Setup, startup, kiểm tra, browser smoke
docs/                    Phân tích, thiết kế, triển khai, kiểm thử
```

## Cấu hình và giới hạn

`.env.example` liệt kê biến; có thể sao chép thành `.env` và sửa. Không commit `.env`, secret, dữ liệu PostgreSQL hoặc bản backup. Development tạo secret ngẫu nhiên tại `.local/django.secret`. Production bắt buộc đặt `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, host database và mật khẩu riêng; bật HTTPS. Nếu đứng sau reverse proxy, cấu hình trust proxy và CSRF origin đúng hạ tầng, không tin header proxy từ Internet trực tiếp.

Phiên bản này phục vụ học tập và trình diễn; ứng dụng chưa được triển khai thành dịch vụ công khai. Cần thêm rate limiting đăng nhập, quy trình khôi phục mật khẩu/email xác minh, giám sát, backup và kiểm tra tải theo hạ tầng trước vận hành thật. Thẻ chỉ mô phỏng; chưa tích hợp VNPay/MoMo, SMS/email, ứng dụng mobile, AI gợi ý tóc, hoàn tiền hoặc lịch đổi ca nhiều ngày. Thông báo hiện lưu trong ứng dụng, không gửi ra bên ngoài.
