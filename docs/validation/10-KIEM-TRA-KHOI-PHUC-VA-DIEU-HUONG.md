# Kiểm tra sửa thiếu template, điều hướng và các thao tác

Kiểm tra local ngày 25/10/2026 với Python 3.12, PostgreSQL 17 và Chromium. Ba log Windows của người dùng đều xác định thiếu cùng template `features/page.html`; đường dẫn template đã cấu hình đúng. File này cùng tám template chức năng được đưa vào danh sách kiểm tra bắt buộc và danh sách đồng bộ nguồn.

## Kết quả kiểm tra

- **94 tests đạt**: toàn bộ `salon.tests`, bao gồm các kiểm thử mới tái hiện ngày năm 0001/9999, mã chi nhánh/ghế sai, đăng ký trùng khi lưu, thiếu shared template, lỗi cú pháp template và khôi phục nguồn khi cập nhật thất bại.
- Kiểm tra liên kết trong HTML cho khách chưa đăng nhập, khách hàng, lễ tân và quản trị: mở các href nội bộ nhìn thấy trên các trang, kiểm tra đích form; các trang/chức năng hợp lệ trả 200/302. Các quyền truy cập bị từ chối được kiểm tra riêng, không bỏ phân quyền để làm tests đạt.
- **270 lượt trang/kích thước** của `scripts/interface_smoke.py` đạt, tại 320/390/768/1024/1440/1920px; không có lỗi JavaScript hoặc asset; bố cục không tràn ngang.
- `scripts/management_smoke.py` đạt: tạo/sửa/xóa sáu nhóm nguồn lực, sửa hồ sơ, từ chối mật khẩu cũ sai, đổi mật khẩu và đăng nhập lại; dọn dữ liệu thử.
- Kiểm tra trình duyệt bổ sung đạt: Excel có dòng sai hoàn tác toàn file; xem trước chưa ghi, xác nhận nhập ghi đúng; xuất Excel/PDF theo bộ lọc, đọc được tiếng Việt trong PDF; đổi lịch giữ mã, hủy có xác nhận; dọn dữ liệu thử.
- `manage.py check`, `makemigrations --check --dry-run`, `collectstatic --noinput`: thành công, không thêm migration.

## Cập nhật nguồn

Script đồng bộ có kiểm thử độc lập: từ chối đường dẫn vượt thư mục và ghi `.env`; khôi phục template thiếu; sao lưu file cũ; chạy lần hai không thay file; dữ liệu tải về sai hash không thay bất kỳ file nguồn nào; lỗi khi thay file hoàn tác các file đã thay. Bản cũ của cấu hình riêng và database không phải đầu vào của script, cũng không được gửi ra mạng.

Hướng dẫn chạy/copy thủ công: [sửa template và đồng bộ file](../10-SUA-LOI-TEMPLATE-VA-DONG-BO-FILE.md).
