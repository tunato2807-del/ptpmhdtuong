# Barber Club — sắc xanh, tinh thần Á Đông

## Yêu cầu và hướng thiết kế

Dựa trên năm ảnh tham khảo người dùng gửi từ gentlemen-barberclubs.de: ảnh lớn,
biểu trưng nghề barber ở trung tâm, tiêu đề cô đọng, họa tiết phân cách, nền sáng
xen kẽ nền tối và bộ ảnh bất đối xứng. Website gốc trả CONNECT 403 từ môi trường;
không khẳng định đã xem được nội dung trực tiếp. Tạo bố cục và biểu trưng riêng.

Xanh navy, xanh khói là chủ đạo; trắng ngà và đồng nhạt làm điểm nhấn. Ảnh chụp
salon Việt Nam đã lưu trong dự án, ghi đúng nguồn, không gán ảnh người mẫu thành
nhân viên thực tế. Không thêm danh tính, giá hay đánh giá giả.

## Hợp đồng giao diện

- Trang chủ giúp xem trải nghiệm, dịch vụ và chọn chi nhánh để đặt lịch.
- Ảnh mở đầu tự chuyển có nút dừng/trước/sau. Tôn trọng reduced motion.
- Nội dung tiếng Việt, font Barlow chỉ ở wordmark/tiêu đề trang chủ; Lora ở câu
  nhấn; biểu mẫu và bảng giữ phông dễ đọc. Font có sẵn ký tự tiếng Việt, tải local.
- Khối giới thiệu sáng, bảng dịch vụ rõ giá, câu nhấn ngắn, bộ ảnh nhiều kích
  thước, khu stylist/chi nhánh. Không biến trang nghiệp vụ thành trang quảng cáo.
- Các liên kết đặt lịch vẫn giữ service/branch/employee; popup, CSRF, đăng xuất
  POST, focus và phản hồi lỗi hoạt động như trước.
- 320/768/1024/1440 px không tràn ngang; nút chạm tối thiểu 44 px; chữ/ảnh không
  đè nhau; ảnh có alt và kích thước. JavaScript tắt vẫn truy cập liên kết.
- Dữ liệu rỗng có thông báo; không thay database hoặc migration.

## Nghiệm thu

Kiểm tra Django, migration drift, collectstatic, regression nghiệp vụ; chạy
browser journey và popup trong database test riêng. Kiểm tra ảnh, font, axe,
slideshow, reduced motion và ảnh chụp desktop/mobile trước khi phát hành.
