# Thiết kế và kế hoạch

- Dùng native dialog và fetch cùng origin, lấy phần main của HTML server. Cấu trúc theo mẫu form/bảng đang có; màu xanh và type scale của Blue Edition. Không nhúng iframe, không đổi chính sách frame-ancestors.
- Tách khởi tạo đặt lịch/báo giá thành hàm nhận vùng DOM; khởi tạo lại khi thay nội dung. Namespace ID/label/ARIA trong dialog để tránh trùng với trang nền.
- Chia phần tải/render, điều khiển trạng thái và thanh submit thành file nhỏ. Đặt listener một lần, chặn gửi lặp, hủy GET cũ và loại phản hồi đến muộn.
- Giữ main navigation; tăng cường link nghiệp vụ và một menu nhanh theo quyền. Danh sách dài cuộn trong dialog; header/footer luôn thấy.
- RED bằng browser test trên database riêng; triển khai, GREEN, kiểm tra bàn phím/axe tại 320/768/1024/1440 và luồng có JavaScript lẫn fallback.
- Chạy checks và suite nghiệp vụ; cập nhật hướng dẫn. Commit source trước, manifest bất biến sau, push và đối chiếu remote.

Phân tích trước triển khai: các thao tác vẫn gọi view hiện có; POST có CSRF và thông báo server. Xuất file dùng điều hướng tải xuống, không parse thành HTML. Script từ HTML trả về không được thực thi; JSON dữ liệu đặt lịch được giữ. Các trường dữ liệu chỉ nằm trong DOM, không lưu storage.
