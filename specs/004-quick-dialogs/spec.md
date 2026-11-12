# Thao tác tại chỗ bằng cửa sổ nổi

## Mục tiêu và phạm vi

Người dùng mở form/bảng từ nút thao tác mà không rời màn hình và không tìm lại vị trí danh sách. Giữ giao diện Blue Edition, cổng quản lý riêng và nghiệp vụ/URL hiện có. Nút Thao tác nhanh luôn sẵn có; menu theo vai trò đưa khách tới lịch/hồ sơ, nhân sự tới lịch/tiếp nhận, quản lý tới kho/chốt sổ/danh mục.

## Tiêu chí nghiệm thu

1. Link form, chi tiết và bảng nghiệp vụ mở một dialog có tên, nút Đóng và Quay lại; nội dung vừa màn hình, chỉ phần nội dung cuộn. Điều hướng chính và đăng nhập/đăng xuất vẫn hoạt động bình thường.
2. Form có thanh hành động ở đáy; dùng lại nút submit thật và HTML validation. Báo lỗi tại chỗ, giữ dữ liệu hợp lệ, không gửi POST trùng hoặc tự thử lại POST khi lỗi mạng.
3. Bộ lọc, phân trang, xem trước/xác nhận Excel và tải Excel/PDF vẫn dùng endpoint cũ. Form đặt lịch vẫn tải stylist/giờ trống; báo giá thanh toán vẫn do máy chủ tính.
4. Đóng bằng nút/Esc, trả focus về nút mở. Nhắc khi có dữ liệu chưa lưu; khi đang gửi giữ cửa sổ đến khi nhận kết quả hoặc hết hạn chờ. Sau thao tác có thể thay đổi dữ liệu, đóng sẽ tải lại trang nền và phục hồi vị trí cuộn/bộ lọc URL.
5. Không có dialog lồng nhau; chuyển nội dung trong cùng một dialog. GET lỗi có thể thử lại/mở trang riêng; lỗi quyền giữ nguyên quyết định của server. Tắt JavaScript thì link/form vẫn dùng được.
6. Kiểm tra desktop/mobile, bàn phím/focus, reduced motion, lỗi mạng, CRUD, giờ trống và quyền. Không sửa dữ liệu ứng dụng hoặc gửi thư/thanh toán thật khi kiểm thử.

## Bất biến

Giữ CSRF, CSP, chặn iframe, khóa/transaction và kiểm tra quyền. Không thêm framework/dependency. Không lưu thông tin form, mật khẩu, token hoặc nội dung khách vào storage/log. Storage chỉ giữ tọa độ cuộn cho việc tải lại.
