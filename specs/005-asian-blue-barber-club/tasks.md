# Công việc

- [x] Đọc cấu trúc hiện có, quy tắc UI và nguồn ảnh/font.
- [x] Chốt hướng thiết kế từ các ảnh tham khảo; ghi rõ giới hạn truy cập website.
- [x] Dựng trang chủ, biểu trưng, palette và điều hướng; giữ hooks đặt lịch.
- [x] Kiểm tra desktop/mobile, sửa tên truy cập logo và cascade thẻ chi nhánh.
- [x] Gom hai nút nổi trên điện thoại thành một hàng, tăng độ rõ của nút nhanh.
- [x] Chạy 15 kiểm thử browser gồm hành trình khách hàng và cửa sổ thao tác.
- [x] Hoàn tất 212 kiểm thử Django và lưu biên bản, ảnh chụp.
- [x] Chuẩn bị source để commit và tạo manifest bất biến; push/đối chiếu GitHub
  là bước phát hành cuối, được xác minh riêng sau commit.

## Phân tích sau triển khai

Các selector trang chủ có phạm vi `.club-home`, không áp phông Barlow vào
form/bảng. Màu dùng chung qua token; không có migration hoặc thay đổi phân
quyền, thanh toán. Ảnh giữ nguyên file và ghi nguồn. Browser xác nhận nút đặt
lịch giữ dữ liệu chọn, kiểm tra thiếu quyền vẫn chặn ở server, form invalid và
mạng lỗi vẫn có phản hồi. Bộ kiểm tra không gửi email/ngân hàng thật.
