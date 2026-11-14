# Kiểm chứng Barber Club sắc xanh — 14/11/2026

## Môi trường và phạm vi

Python 3.12.14, Django 5.2.18, PostgreSQL 17.11 native, Chromium headless qua
Playwright. Các kiểm thử ghi dữ liệu trong database test riêng, sử dụng fixture
và email backend cục bộ; không gửi email/thanh toán thật, không thay database
của người dùng. Không coi kết quả này là kiểm chứng Python 3.14 hoặc Windows.

## Kết quả

- `manage.py check`: không có vấn đề.
- `manage.py makemigrations --check --dry-run`: không có thay đổi schema.
- `manage.py collectstatic --noinput`: thành công; browser dùng tài nguyên có hash.
- `manage.py test --noinput`: **212 kiểm thử đạt**.
- `scripts/quick_dialog_browser.py`: **15 kiểm thử đạt**, 62,492 giây.
- Ruff check và format check cho `salon config scripts`: đạt.
- `git diff --check`: đạt.

Browser kiểm tra trang chủ ở 320/768/1024/1440 px: không tràn ngang, một H1,
ảnh local tải được, đăng xuất và nút đặt lịch nhìn thấy; axe không phát hiện lỗi
serious/critical ở cả bốn kích thước. Kiểm tra popup thêm menu/form ở bốn kích
thước cũng đạt. Có kiểm tra đăng nhập/đăng xuất thật trong database test, chọn
dịch vụ/stylist/chi nhánh, lấy giờ trống, đặt/hủy lịch, báo giá/thanh toán kiểm
thử, CRUD, nhập/xuất Excel, xuất PDF, giữ bộ lọc/cuộn, focus, lỗi mạng, quyền,
ngăn gửi POST trùng và trường hợp kết quả POST chưa rõ.

Hành trình khách hàng kiểm tra thêm 24 tổ hợp route/kích thước, slideshow tự
chuyển/dừng/ảnh tiếp theo, reduced motion, menu/Esc và không JavaScript; không
phát hiện lỗi JavaScript hoặc request tài nguyên bên ngoài trong hành trình này.

## Các điểm sửa từ kiểm tra

- Lần đầu axe phát hiện nhãn truy cập logo không chứa toàn bộ chữ hiển thị.
  Sửa tên và khoảng trắng giữa GENTLEMAN / BARBER HOUSE; kiểm tra lại đạt.
- Kiểm tra ảnh điện thoại phát hiện cascade bố cục cũ áp vào chi nhánh đầu
  tiên; chuẩn hóa các thẻ thành cùng một bố cục.
- Nút nhanh chịu kiểu button nền trong suốt từ CSS cũ; thêm màu/nền rõ và
  đặt hai nút nổi trên điện thoại cùng một hàng. Tăng cỡ chữ chú thích bảng giá.
- Thêm favicon SVG riêng, không yêu cầu tải tài nguyên từ website tham khảo.

## Giới hạn và bằng chứng

[Ảnh máy tính](../screenshots/barber-club/home-1440.png) và
[ảnh điện thoại](../screenshots/barber-club/home-320.png) được kiểm tra trực quan.
Đây là ảnh database fixture, không phải dữ liệu thật thêm vào dự án. Ảnh chụp
salon bên trong trang giữ nguồn và giới hạn quyền tại `docs/NGUON-TAI-NGUYEN.md`.

Website tham khảo bị môi trường chặn CONNECT 403; không tải tài nguyên hoặc
copy logo của website đó. Chưa kiểm chứng trình duyệt Safari, thiết bị iOS thật
hoặc chỉ số Web Vitals ngoài thực tế. Các kết quả không có nghĩa website sẽ
không thể phát sinh lỗi trong mọi dữ liệu/môi trường khác.
