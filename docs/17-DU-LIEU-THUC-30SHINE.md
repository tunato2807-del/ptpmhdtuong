# Dữ liệu thực tế từ 30Shine — trạng thái và bước chuẩn bị

Theo yêu cầu ngày 06/11/2026, nguồn được chọn duy nhất là website chính thức **30Shine**. Chưa có bản ghi 30Shine mới được thêm vào dự án trong bản chuẩn bị này: môi trường hiện tại chưa truy cập được nguồn để kiểm chứng giá, dịch vụ và địa chỉ.

## Việc đã làm

- `scripts/dev.py setup` không tự gọi seed_demo nữa, kể cả máy vẫn còn `LOAD_DEMO_DATA=1`. Tham số --no-demo vẫn được nhận để lệnh cũ tiếp tục chạy.
- Trang Đăng nhập không hiển thị danh sách tài khoản/mật khẩu trình diễn dùng chung.
- Với database mới, có thể tạo quản trị chuỗi bằng thông tin chủ hệ thống thực sự nhập:

```powershell
.\.venv\Scripts\python.exe manage.py create_manager
```

Lệnh yêu cầu terminal tương tác, hỏi tên đăng nhập/họ tên/email/mật khẩu. Mật khẩu không hiện khi gõ, được kiểm tra độ mạnh rồi băm; tài khoản có role manager, không tự bật quyền Django superuser. Lệnh không ghi đè hay nâng quyền tài khoản đã tồn tại. Nếu đã có tài khoản quản lý thì tiếp tục dùng tài khoản đó, không cần chạy lại.

Các thay đổi này không xóa bản ghi cũ, không đổi tên/nhãn dữ liệu cũ thành “thực tế” và không tạo thêm khách/nhân viên/lịch/hoá đơn giả. Nhãn nguồn của dữ liệu mẫu cũ không bị bỏ để che nguồn gốc; việc phân loại/lưu trữ dữ liệu cũ sẽ được xử lý cùng phương án dữ liệu chính thức.

## Trở ngại truy cập nguồn

Yêu cầu HTTPS tới https://30shine.com/ qua proxy của môi trường bị từ chối với HTTP 403. Policy runtime đang restricted/enforced và chưa cho host 30Shine. Draft có sẵn `30shine.com` và `www.30shine.com`; đã lưu lại giữ nguyên các miền có trước, công cụ trả về **saved, requires_publish: true**.

Cần mở cấu hình môi trường, Review/Save thay đổi rồi **Publish môi trường**. Lưu draft không mở kết nối cho runtime; sửa file policy trên máy hoặc dùng đường vòng không giải quyết quyền truy cập. Sau khi cấu hình được áp dụng, kiểm tra lại environment_status và yêu cầu HTTPS tới nguồn chính thức.

## Quy tắc khi tiếp tục nhập

1. Mỗi bản ghi có tên thương hiệu gốc, URL trang, ngày đối chiếu và nội dung làm căn cứ.
2. Giá “từ”, giá khuyến mãi, khu vực và điều kiện áp dụng phải được giữ nguyên ý nghĩa. Không chuyển một giá quảng cáo thành giá chung của mọi salon.
3. Thiếu giờ mở cửa, thời lượng, nhân sự, ghế hoặc ca thì để chưa xác minh; không lấy giá trị mặc định giả để làm dữ liệu bên ngoài có thể đặt lịch trong hệ thống.
4. Địa chỉ/dịch vụ công khai không đồng nghĩa quyền quản lý hay xác nhận tích hợp đặt chỗ với 30Shine. Không đổi tên salon thật thành chi nhánh GENTLEMAN.
5. Khách hàng, giao dịch, doanh thu, lịch hẹn và tồn kho phải từ hoạt động thật của bạn; không thể suy ra từ website công khai của doanh nghiệp khác.
6. Không dùng Fresha, bản sao GitHub hay trí nhớ mô hình để điền chỗ thiếu trong yêu cầu chỉ lấy nguồn chính thức.

Kế hoạch và phần còn chờ tại [specs/002-official-30shine-data](../specs/002-official-30shine-data/). Có spec hoặc script chuẩn bị không có nghĩa dữ liệu 30Shine đã được nhập xong.

## Kiểm tra phần chuẩn bị

Đã chạy 189 kiểm thử Django trên PostgreSQL và tất cả đều đạt, gồm 5 kiểm thử mới cho setup/login/tạo manager. Django check, migration drift, collectstatic và Ruff đạt; không có migration mới. Kết quả này chỉ kiểm chứng thay đổi phần mềm, không phải bằng chứng đã xác minh hay nhập dữ liệu 30Shine.
