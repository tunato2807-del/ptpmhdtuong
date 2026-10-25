# Sửa TemplateDoesNotExist và đồng bộ đầy đủ mã nguồn

Ba log tại Báo cáo, Dịch vụ và Ca làm đều thiếu `features/page.html`. Django đã tìm đúng `D:/DO_AN/HDT/ptpmhdtuong-main/templates`; cần bổ sung file vào `templates/features/page.html`, cùng tám template chức năng khác. Đây là lỗi thiếu file trong bản đang chạy, không phải do Python 3.14 hoặc PostgreSQL.

## Cách đồng bộ từng file, có sao lưu

Không cần tải lại ZIP dự án. Script lấy danh sách file và SHA256 từ repository này, tải đúng từng file của một commit cố định, kiểm tra toàn bộ trước khi thay thế. File cũ được sao lưu trong `.local/cap-nhat-.../sao-luu`. Nếu không tải đủ hoặc sai hash, mã nguồn cũ chưa bị thay. Nếu thay file thất bại, script hoàn tác các file vừa thay.

Script đồng bộ mã nguồn Python/HTML/CSS/JS, ảnh/font và requirements; **không thay `.env`, `.venv` hoặc database**, không tự chạy migrate, không gửi thông tin máy lên GitHub. Các tùy chỉnh mã nguồn riêng sẽ có trong bản sao lưu để bạn đối chiếu.

Dừng server bằng Ctrl+C. Trong PowerShell của VS Code, đứng ở thư mục chứa `manage.py`:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tunato2807-del/ptpmhdtuong/main/scripts/cap_nhat_du_an.py" -OutFile ".\cap_nhat_du_an.py"
.\.venv\Scripts\python.exe .\cap_nhat_du_an.py
```

Chỉ tiếp tục khi script báo cập nhật thành công hoặc mã nguồn đã đủ phiên bản. Nếu báo lỗi mạng, chạy lại; không tiếp tục khởi động với bản copy dở.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check_database
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

Nhấn Ctrl+F5 trong trình duyệt. Không cần chạy lại seed hoặc xóa dữ liệu.

Muốn chỉ xem những file còn thiếu/khác, không thay thế:

```powershell
.\.venv\Scripts\python.exe .\cap_nhat_du_an.py --check-only
```

## Nếu muốn tự copy bằng VS Code

Vẫn có thể mở từng file trên GitHub → Raw / Copy raw file → thay toàn bộ nội dung đúng đường dẫn. Đừng chỉ copy `features.py`: file đó cần đầy đủ các template dưới đây.

- [templates/features/page.html](../templates/features/page.html)
- [templates/features/resource_list.html](../templates/features/resource_list.html)
- [templates/features/resource_detail.html](../templates/features/resource_detail.html)
- [templates/features/resource_import.html](../templates/features/resource_import.html)
- [templates/features/reports.html](../templates/features/reports.html)
- [templates/features/search.html](../templates/features/search.html)
- [templates/features/appointments.html](../templates/features/appointments.html)
- [templates/features/cancel.html](../templates/features/cancel.html)
- [templates/features/reschedule.html](../templates/features/reschedule.html)

Các file sửa thêm trong bản rà soát này:

- [salon/checks.py](../salon/checks.py): kiểm tra thiếu template/CSS/JS/font và cú pháp template khi chạy `manage.py check`/runserver. `salon.E002` nêu rõ vị trí file thiếu; `salon.E003` nêu template sai cú pháp.
- [salon/features.py](../salon/features.py), [salon/views.py](../salon/views.py): kiểm tra dữ liệu đầu vào, báo lỗi trên bộ lọc báo cáo, xử lý đăng ký trùng đồng thời, điều kiện hiển thị nút đổi/hủy lịch.
- [templates/public/appointment_detail.html](../templates/public/appointment_detail.html): giải thích khi lịch đã sát giờ hẹn.
- [static/css/management.css](../static/css/management.css), [templates/base.html](../templates/base.html): bố cục bộ lọc và phiên bản cache mới.

[Danh sách đầy đủ các file của dự án và hướng dẫn copy](08-CAP-NHAT-TUNG-FILE.md).

## Cải thiện các chi tiết sử dụng

- Báo cáo: tên trường rõ ràng, báo lỗi cạnh ô nhập, giữ dữ liệu đã nhập, nút đặt lại bộ lọc; không xuất báo cáo khi bộ lọc sai.
- Danh mục/tìm kiếm: số kết quả và nút xóa bộ lọc; phân trang giữ điều kiện tìm kiếm.
- Lịch cá nhân: hiện dịch vụ và tổng tiền; khi sát giờ, hướng dẫn liên hệ chi nhánh thay vì đưa nút đổi/hủy không còn đáp ứng điều kiện. Kiểm tra phía server vẫn được giữ nguyên.
- Excel: thông báo xem trước chưa lưu và cần xác nhận; file có dòng sai không lưu bất kỳ dòng nào.
- Đăng ký: tên bị đăng ký trùng đúng lúc lưu được báo ở trường tên đăng nhập.
- Bộ lọc ngày và mã chi nhánh/ghế không hợp lệ được kiểm tra trước khi truy vấn; không chuyển thành lỗi ValueError/OverflowError.

Các yêu cầu không đúng quyền, bản ghi không tồn tại hoặc thao tác vi phạm nghiệp vụ vẫn bị từ chối theo đúng quyền của tài khoản; các bài kiểm tra không thay thế những quy tắc đó.
