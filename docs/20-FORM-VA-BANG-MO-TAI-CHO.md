# Form và bảng mở tại chỗ — 12/11/2026

## Cách sử dụng

Nút **Thao tác nhanh** luôn nằm ở góc màn hình. Bấm để mở menu theo quyền tài khoản: đặt lịch/hồ sơ cho khách; tiếp nhận/lịch/khách cho nhân sự; kho, chốt sổ và danh mục cho quản lý. Trên điện thoại, menu dùng các ô gọn; trên desktop chia ba cột.

- Bấm Thêm, Xem, Sửa, Xóa, đặt/đổi/hủy lịch hoặc mở bảng nghiệp vụ để thao tác trong cửa sổ nổi.
- Nút lưu/xác nhận nằm ở thanh dưới cùng. Form dài chỉ cuộn bên trong; tiêu đề, nút Đóng và nút lưu luôn sẵn có.
- Bấm **←** để quay lại nội dung trước trong cùng cửa sổ; bấm **Đóng** hoặc **Esc** để đóng. Nếu đã nhập mà chưa lưu, chọn giữ lại hoặc bỏ thay đổi ở lời nhắc.
- Lỗi nhập liệu hiện ngay trong form. Trong lúc gửi, chờ kết quả rồi mới tiếp tục; nếu mất phản hồi, kiểm tra lại dữ liệu trước khi gửi thêm.
- Sau thao tác có thể thay đổi dữ liệu, đóng cửa sổ sẽ tải lại danh sách nền và phục hồi vị trí cuộn. Bộ lọc/trang của URL nền được giữ.
- Tìm kiếm, phân trang, xem trước/xác nhận Excel dùng ngay trong cửa sổ; Excel/PDF vẫn tải thành file. Hóa đơn có thể in phần nội dung đang mở.
- Với hồ sơ cá nhân, bấm Thông tin cá nhân hoặc Đổi mật khẩu để tới đúng form và đúng nút lưu. Có thể dùng **Mở trang riêng** trên màn hình rộng khi cần.

Điều hướng chính vẫn chuyển mục như trước; đăng nhập/đăng xuất dùng luồng riêng. Tắt JavaScript vẫn sử dụng được link và form theo trang thông thường. Màn hình nhỏ giới hạn nội dung theo chiều cao; bảng rộng cuộn trong vùng bảng.

## Cập nhật từ VS Code trên Windows

Dừng server bằng **Ctrl+C**, mở terminal tại thư mục có `manage.py`:

```powershell
.\.venv\Scripts\python.exe scripts\cap_nhat_du_an.py
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

Nhấn **Ctrl+F5** trong trình duyệt. Không thêm dependency hay migration trong bản giao diện này. Trình cập nhật sao lưu file bị thay trong `.local`, giữ `.env`, `.venv` và database.

## Ảnh kiểm tra giao diện

Ảnh chụp từ database kiểm thử cô lập, không phải dữ liệu khách hàng hay giao dịch thực tế.

- [Menu thao tác nhanh trên desktop](screenshots/dialogs/tools-1440.png)
- [Menu trên màn hình 320 px](screenshots/dialogs/tools-320.png)
- [Form thêm dịch vụ trên điện thoại](screenshots/dialogs/form-320.png)
- [Chọn giờ và xác nhận đặt lịch](screenshots/dialogs/booking-390.png)

## Thiết kế và giới hạn

Native dialog giữ focus và chặn thao tác nhầm vào nền. Fetch cùng origin dùng session/CSRF và view hiện có; không thêm quyền bằng JavaScript. Script từ HTML trả về không được chạy; dữ liệu JSON đặt lịch được dùng bởi bộ khởi tạo có phạm vi. ID/label/ARIA trong nội dung mở được đổi tên để không trùng trang nền. Đọc thuộc tính form bằng `getAttribute` để các trường `action`/`method` không làm sai URL/phương thức gửi.

Đóng cửa sổ xóa DOM của form. Storage chỉ giữ hai tọa độ cuộn cho lần tải lại, không giữ dữ liệu nhập. Không tự thử lại POST hoặc ghi giao dịch khi chỉ mở form. Kiểm tra mạng/quyền vẫn thuộc server; không đổi CSP hay cho phép iframe.

Kiểm thử tự động: sau `collectstatic`, chạy `BROWSER_EXECUTABLE=/usr/bin/chromium .venv/bin/python scripts/quick_dialog_browser.py` trên Linux có Chromium sẵn; bỏ biến này nếu đã cài Chromium của Playwright. Công cụ dùng database test riêng và gọi cả bộ kiểm tra hành trình khách hàng cũ trên database đó. Cần `requirements-quality.txt` và `npm ci --ignore-scripts --prefix scripts/browser-audit` cho axe; đây là công cụ phát triển, không cần khi chỉ chạy web.

Đặc tả: [Thao tác tại chỗ](../specs/004-quick-dialogs/spec.md). Bằng chứng: [Kiểm tra giao diện và nghiệp vụ](validation/20-FORM-VA-BANG-MO-TAI-CHO.md).
