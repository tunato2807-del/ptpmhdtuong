# Kiểm tra bản sửa giao diện và bổ sung chức năng

Ngày kiểm tra: 25/10/2026. Môi trường local cloud: Python 3.12, Django 5.2, PostgreSQL 17 cài trực tiếp, Chromium headless. Không dùng Docker. GitHub Actions đã có cấu hình Python 3.12 và 3.14; kết quả ở đây là các lần chạy local, không phải kết quả của runner Windows.

## Kết quả

- Django check: không có lỗi; migration drift: không có thay đổi; collectstatic thành công.
- 81 kiểm thử trong `salon.tests`: đạt. Có kiểm tra phân quyền, CSRF, chống trùng lịch đồng thời, CRUD, nhập Excel nguyên tử/xem trước/hết hạn/chống gửi lại, dữ liệu lỗi, bộ lọc doanh thu và PDF tiếng Việt.
- `scripts/interface_smoke.py`: 270 lượt trang/kích thước, rộng 320/390/768/1024/1440/1920. CSS/font trả về thành công; không có JavaScript error hoặc trang tràn ngang; biểu tượng nhỏ đúng kích thước; lưới thiết lập và hồ sơ chia cột đúng; nút Đăng xuất nhìn thấy ở mọi kích thước cho cả khách/lễ tân/quản trị. POST đăng xuất kết thúc session; hồ sơ yêu cầu đăng nhập lại.
- `scripts/browser_smoke.py`: đăng ký, đặt/hủy, lễ tân check-in, bắt đầu dịch vụ, thanh toán mô phỏng, hóa đơn, đánh giá, CSV, menu và màn hình nhỏ: đạt.
- Kiểm tra bổ sung trên trình duyệt: Excel có dòng sai hoàn tác toàn bộ; xem trước chưa ghi dữ liệu; xác nhận nhập thành công; tải Excel/PDF theo bộ lọc; đọc lại chữ tiếng Việt từ PDF bằng pdftotext; tải hóa đơn/báo cáo; đổi lịch giữ mã và hủy có xác nhận: đạt.
- Đọc UTF-8 các template/CSS không có ký tự thay thế U+FFFD; tất cả link file trong hướng dẫn copy trỏ đến file có thật.

## Hình chụp sau khi sửa

- [Thiết lập — desktop](../screenshots/interface/quan-ly-thiet-lap-1440.png)
- [Thiết lập — điện thoại](../screenshots/interface/quan-ly-thiet-lap-390.png)
- [Hồ sơ — desktop](../screenshots/interface/tai-khoan-1440.png)
- [Hồ sơ — điện thoại](../screenshots/interface/tai-khoan-390.png)

Phông chữ bổ sung chỉ áp dụng cho các selector cụ thể trong `static/css/typography.css`. Không có rule đổi font cho toàn bộ body/table/input trong file này. Cả hai giao diện có nút Đăng xuất bằng chữ trên đầu trang; không phụ thuộc vào việc cuộn đến cuối sidebar hoặc mở menu điện thoại.

Kiểm tra bao phủ dữ liệu mẫu và các tình huống được mô tả trong tests; máy người dùng cần copy đủ các file cùng phiên bản, cài requirements và cấu hình kết nối PostgreSQL riêng theo README.
