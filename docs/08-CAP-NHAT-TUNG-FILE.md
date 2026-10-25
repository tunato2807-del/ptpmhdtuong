# Cập nhật bằng cách copy từng file trong VS Code

Bản này sửa trang Thiết lập & nhân sự, hồ sơ, kích thước biểu tượng, nút Đăng xuất và giới hạn các thay đổi phông chữ. Đồng thời đưa đầy đủ phần tìm kiếm, phân trang, nhập/xuất Excel, PDF, đổi/hủy lịch lên GitHub.

## Cách lấy mã

Mở file trong GitHub → bấm **Raw** hoặc **Copy raw file** → copy toàn bộ → mở đúng file trong VS Code → thay toàn bộ nội dung → lưu UTF-8. Với file mới, tạo đúng thư mục và tên file. Giữ nguyên phần mở rộng `.css`, `.html`, `.py`; không thêm `.txt`.

Dừng Django bằng Ctrl+C trước khi copy. Hoàn tất toàn bộ các nhóm bên dưới rồi khởi động lại. Không chạy lại script `cap_nhat_logic.py` cũ sau khi cập nhật: các template mới đã được tách ra thành file riêng.

Giữ `.env`, `.venv`, database PostgreSQL và mật khẩu trên máy. Không cần xóa database hoặc chạy lại `seed_demo`. Không copy file từ thư mục `staticfiles`; đó là đầu ra do collectstatic tạo.

## 1. Giao diện: copy đầy đủ cùng nhau

| File | Công dụng |
|---|---|
| [templates/base.html](../templates/base.html) | Nạp đủ CSS/JS, phiên bản cache mới, Đăng xuất luôn ở đầu trang khách hàng |
| [templates/staff/base.html](../templates/staff/base.html) | Đăng xuất bằng chữ trên thanh đầu trang quản lý |
| [templates/partials/icon_arrow.html](../templates/partials/icon_arrow.html) | Biểu tượng có kích thước sẵn, tránh mũi tên khổng lồ |
| [static/css/app.css](../static/css/app.css) | Kiểu nền tảng và nút Đăng xuất |
| [static/css/customer.css](../static/css/customer.css) | Toàn bộ bố cục trang khách hàng |
| [static/css/management.css](../static/css/management.css) | Lưới thiết lập, hồ sơ hai cột, biểu mẫu và bố cục màn hình nhỏ |
| [static/css/motion.css](../static/css/motion.css) | Hiệu ứng chuyển động và trình chiếu |
| [static/js/motion.js](../static/js/motion.js) | Điều khiển ảnh tự chuyển |
| [static/css/typography.css](../static/css/typography.css) | **Thay toàn bộ bản cũ**, chỉ sửa phông ở một số tiêu đề/chữ trang trí |
| [static/js/app.js](../static/js/app.js) | Menu quản lý và đặt lịch |
| [static/js/customer.js](../static/js/customer.js) | Menu khách, hiệu ứng và bộ lọc |
| [salon/apps.py](../salon/apps.py) | Đăng ký kiểm tra file giao diện |
| [salon/checks.py](../salon/checks.py) | Báo chính xác file CSS/JS/font bị thiếu khi khởi động |

Các mẫu trang cũng phải dùng bản cùng phiên bản:

- [templates/auth/login.html](../templates/auth/login.html), [register.html](../templates/auth/register.html).
- [templates/public/home.html](../templates/public/home.html), [booking.html](../templates/public/booking.html), [profile.html](../templates/public/profile.html).
- [templates/public/my_appointments.html](../templates/public/my_appointments.html), [appointment_detail.html](../templates/public/appointment_detail.html), [invoice.html](../templates/public/invoice.html).
- [templates/staff/settings.html](../templates/staff/settings.html).

Các ảnh và phông đã có trong [static/images](../static/images) và [static/fonts](../static/fonts). Nếu thiếu file `.woff2`, tải riêng file bằng **Download raw file** và đặt đúng tên trong `static/fonts`; không dán nội dung nhị phân vào trình soạn thảo.

## 2. Logic và chức năng: dùng trọn bộ cùng phiên bản

| File | Công dụng |
|---|---|
| [requirements.txt](../requirements.txt) | Thư viện Excel/PDF/XML |
| [salon/features.py](../salon/features.py) | Tìm kiếm, phân trang, xem chi tiết, nhập/xuất, đăng ký, đổi/hủy lịch |
| [salon/urls.py](../salon/urls.py) | Kết nối các đường dẫn |
| [salon/services.py](../salon/services.py) | Kiểm tra khung giờ và nghiệp vụ |
| [salon/views.py](../salon/views.py) | Các trang và tìm lịch theo mã |

Tạo/copy **toàn bộ 9 file** trong [templates/features](../templates/features):

- [page.html](../templates/features/page.html)
- [resource_list.html](../templates/features/resource_list.html)
- [resource_detail.html](../templates/features/resource_detail.html)
- [resource_import.html](../templates/features/resource_import.html)
- [reports.html](../templates/features/reports.html)
- [search.html](../templates/features/search.html)
- [appointments.html](../templates/features/appointments.html)
- [cancel.html](../templates/features/cancel.html)
- [reschedule.html](../templates/features/reschedule.html)

Các file gốc như [salon/models.py](../salon/models.py), [forms.py](../salon/forms.py), [management_views.py](../salon/management_views.py), [profile_views.py](../salon/profile_views.py), [config/settings.py](../config/settings.py) đều có đầy đủ trong repository. Nếu trước đây bạn đã tự sửa chúng, đối chiếu trước khi thay để giữ các tùy chỉnh riêng; thông tin kết nối database tiếp tục lấy từ `.env`.

## 3. Chạy lại trên PowerShell của VS Code

Đứng ở thư mục chứa `manage.py`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check_database
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

Dừng tại lệnh lỗi để xử lý trước khi chạy tiếp. Nếu `check` báo `salon.E001`, copy đúng file được nêu trong thông báo. Sau khi server chạy, nhấn Ctrl+F5 trong trình duyệt.

## 4. Kiểm tra kết quả

- `/quan-ly/thiet-lap/`: sáu thẻ thiết lập; màn hình rộng có ba cột; mũi tên nhỏ.
- `/tai-khoan/`: hồ sơ và biểu mẫu chia hai cột trên desktop, một cột trên điện thoại.
- Khi đã đăng nhập, nút **Đăng xuất** nằm trên thanh đầu trang của cả trang khách hàng và trang quản lý; điện thoại vẫn thấy nút mà không cần mở menu.
- Trang thiết lập có Xem, Thêm, Sửa, Xóa, Nhập Excel, Xuất Excel/PDF; nhập Excel cần xem trước và xác nhận.
- Lịch của tôi có tìm kiếm, phân trang, đổi và hủy lịch theo điều kiện nghiệp vụ. Lịch sử/hóa đơn được giữ để tra cứu.

## Phông chữ chỉ ở vị trí được chọn

`typography.css` không đặt font cho `body`, toàn bộ bảng, menu, nút hoặc ô nhập. Nó chỉ nhắm đến phần chữ nhấn trên trang chủ/đăng nhập, tiêu đề trang quản lý/hồ sơ, khối hướng dẫn và lời cảm ơn hóa đơn. Kiểu chữ nền của giao diện vẫn theo các CSS gốc.

Muốn áp dụng riêng cho một cụm chữ khác, thêm class này đúng vào phần tử đó:

```html
<span class="font-vietnamese">Chăm chút từng trải nghiệm</span>
```

Muốn giữ nguyên phông gốc ở một vị trí đang được sửa, bỏ selector tương ứng khỏi `typography.css`.

## Tự kiểm tra bằng mã nguồn

```powershell
python scripts/dev.py check
```

Có thể chạy thêm `scripts/interface_smoke.py` khi đã cài Playwright và trình duyệt. Script dùng database của checkout local DEBUG, kiểm tra bố cục/asset/đăng xuất ở sáu kích thước; chỉ tạo và xóa session kiểm thử, không sửa lịch hẹn hoặc danh mục. Hướng dẫn kiểm tra chức năng nằm trong README.
