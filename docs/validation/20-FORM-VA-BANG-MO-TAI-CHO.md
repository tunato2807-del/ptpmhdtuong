# Kiểm chứng form/bảng mở tại chỗ — 12/11/2026

## Kết quả thực đo

Môi trường: Python 3.12.14, Django 5.2.18, PostgreSQL 17.11 và Chromium qua Playwright. Các kiểm thử ghi dữ liệu chỉ chạy trên database test riêng. Không thay đổi dữ liệu ứng dụng, gửi email thật hoặc thực hiện thanh toán ngân hàng.

| Kiểm tra | Kết quả |
|---|---|
| Browser RED trước triển khai | Ca mở bảng tại chỗ thất bại như dự kiến, trang bị chuyển thay vì mở dialog |
| Browser sau triển khai | 14/14 đạt; 55,560 giây; không có JavaScript page error |
| Suite Django hiện có | 212/212 đạt; 98,294 giây |
| Django check / migration drift / collectstatic | Đạt; không có migration mới |
| Ruff check/format cho salon, config, scripts | Đạt; 84 file đúng định dạng |
| Kiểm tra cú pháp Node cho 6 file JavaScript thay đổi/thêm | Đạt |
| Tính toàn vẹn Agent Skills / Spec Kit smoke | 39 file Agent Skills, 45 file Spec Kit và helper cô lập đạt |

## Các hành vi đã kiểm tra trong trình duyệt

1. Mở bảng từ thiết lập, giữ URL nền, đóng bằng Esc và trả focus đúng nút mở.
2. Thêm/sửa/xóa qua form thật; gửi giá không hợp lệ đến server, giữ tên đã nhập; lọc kết quả và tải Excel/PDF khi dialog vẫn mở.
3. Đóng form chưa lưu: có thể giữ bản nhập hoặc xác nhận bỏ; không tạo dữ liệu khi bỏ.
4. GET bị đứt mạng: hiển thị thử lại, tải được sau khôi phục và đóng bình thường.
5. Menu và form ở 320/768/1024/1440 px: vừa màn hình, thanh submit hiển thị, vùng nội dung không tràn ngang, Tab nằm trong dialog. Axe không có lỗi serious/critical tại 8 trạng thái menu/form. Reduced motion tắt animation dialog.
6. Khách mở đặt lịch từ hồ sơ: tải stylist/giờ trống, đặt và hủy lịch thật trong database test; DOM không có ID trùng.
7. Nhập file Excel multipart: tải mẫu đúng tên cột SQL tiếng Việt, xem trước, xác nhận và tạo đúng một dòng trong database test.
8. Không JavaScript: link bảng và form vẫn chuyển trang hoạt động.
9. Báo giá thanh toán: voucher sai làm nút thu tiền bị khóa, xóa voucher tải lại báo giá hợp lệ; xác nhận tiền mặt một lần và hóa đơn đúng số. In dialog chỉ hiển thị hóa đơn, ẩn nền/thanh thao tác ở print media.
10. Mất phản hồi sau khi server đã tạo dịch vụ: hai lệnh submit liên tiếp chỉ gửi một POST, không tự gửi lại; thông báo chưa xác nhận kết quả. Server chỉ có một bản ghi.
11. Lưu từ danh sách có bộ lọc và vị trí cuộn: phân trang trong dialog hoạt động; đóng tải lại đúng URL nền và phục hồi tọa độ cuộn.
12. Khách tự tạo link quản lý: server vẫn trả trang thiếu quyền và không có form quản lý.
13. Chạy lại customer_ui_smoke.py trên database test: đăng nhập/đăng xuất, tham số chọn trước từ dịch vụ/stylist/form nhanh, cập nhật giờ trống và phiếu tạm tính, slideshow/ảnh, 24 trạng thái responsive, menu di động, reduced motion và fallback không JavaScript đạt; không có yêu cầu tới nguồn ngoài.
14. Mở lại hồ sơ khi trang nền cũng có form: label trỏ đúng input trong dialog, ID không trùng; chuyển giữa thông tin cá nhân/mật khẩu cập nhật đúng nút submit cố định.

Thử vô hiệu hóa điều kiện nhận link dialog trong bộ nhớ trình duyệt kiểm thử: ca mở bảng thất bại đúng như dự kiến trong 7,485 giây; file nguồn không bị thay đổi. Đây là kiểm tra sức phát hiện hồi quy của test, không phải lỗi còn trong bản phát hành.

## Rà soát và giới hạn

Rà soát tính đúng, khả năng đọc, kiến trúc, quyền và chi phí: dùng native dialog, fetch cùng origin, endpoint và CSRF hiện có. Không thay đổi CSP/chính sách iframe hoặc giao dịch nghiệp vụ. Tách các bộ khởi tạo theo vùng DOM, kiểm tra thuộc tính action/method bằng getAttribute để tránh trùng tên trường. Observer bị ngắt khi đổi form; trail tối đa 20 mục, GET cũ bị hủy và phản hồi đến muộn bị bỏ. Không cache form hoặc lưu nội dung nhập vào storage.

Ảnh đã được xem lại để chỉnh độ gọn menu, tiêu đề và trạng thái chọn giờ; chỉ dùng dữ liệu kiểm thử. [Hướng dẫn và ảnh](../20-FORM-VA-BANG-MO-TAI-CHO.md).

Chưa phải bằng chứng đã thử mọi nút với mọi tập dữ liệu thực tế hoặc mọi trình duyệt. Kiểm tra cục bộ dùng Python 3.12/Chromium; cấu hình CI có Python 3.14 không có nghĩa đã quan sát kết quả job đó. Điều hướng mục chính và đăng nhập/đăng xuất vẫn chuyển trang; bảng dài chỉ cuộn bên trong cửa sổ. Nguồn dữ liệu thật 30Shine là công việc riêng, không được đánh dấu hoàn tất bởi các kiểm thử này.
