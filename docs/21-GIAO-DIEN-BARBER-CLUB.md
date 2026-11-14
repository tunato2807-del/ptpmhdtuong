# GENTLEMAN — Barber Club sắc xanh

Bản giao diện ngày 14/11/2026 lấy cảm hứng từ các ảnh người dùng gửi về
Gentlemen Barber Clubs: biểu trưng nghề barber, tiêu đề cô đọng, nét trang trí
mảnh, ảnh lớn và bộ ảnh bố trí bất đối xứng. Bố cục, biểu trưng, nội dung được
viết riêng cho GENTLEMAN, phối xanh navy/xanh khói với trắng ngà và đồng nhạt.

## Giao diện mới

- Trang chủ có ảnh trò chuyện/tư vấn tại salon Việt Nam, tự chuyển mỗi 5,5 giây.
  Có nút ảnh trước/sau và dừng; tự dừng khi rê chuột, focus, chuyển tab hoặc khi
  ảnh nằm ngoài màn hình. Khi bật giảm chuyển động, chuyển ảnh bằng nút.
- Phần giới thiệu, dịch vụ và giá, câu nhấn, bộ ảnh, stylist và chi nhánh có
  phân cấp rõ. Các nút dịch vụ/stylist/chi nhánh vẫn mở đúng lựa chọn đặt lịch.
- Thanh đặt lịch theo chi nhánh ngay dưới ảnh mở đầu; form và bảng tiếp tục mở
  tại chỗ bằng cửa sổ có thể đóng, quay lại, giữ bộ lọc và vị trí cuộn.
- Điện thoại có hai nút Đặt lịch / Thao tác nhanh cùng một hàng dưới cùng. Nút
  đăng xuất vẫn ở thanh đầu trang; menu mở bằng bàn phím và đóng bằng Esc.
- Phông Barlow Condensed chỉ dùng ở logo và các tiêu đề trang chủ; Lora ở chữ
  nhấn. Form/bảng không chuyển sang phông trang trí. Toàn bộ font tải từ dự án.
- Các trang đặt lịch, tài khoản và quản lý dùng chung bảng màu dịu hơn; giữ
  luồng nghiệp vụ, quyền, trạng thái và bố cục thao tác hiện có.

## Ảnh và nguồn

Dùng lại ảnh chụp salon Việt Nam đã có, không sinh ảnh AI, thay mặt hoặc gán
ảnh người mẫu thành nhân viên GENTLEMAN. Bộ ảnh gốc có kích thước khác nhau,
một số ảnh nhỏ; xem nguồn và giới hạn giấy phép tại
[Nguồn tài nguyên](NGUON-TAI-NGUYEN.md). Nội dung giá, chi nhánh, stylist lấy từ
database của máy đang chạy; cập nhật giao diện không thêm hay thay dữ liệu.

Website tham khảo trả CONNECT 403 trong môi trường phát triển. Các quyết định
thiết kế dựa trên năm ảnh người dùng cung cấp, không phải việc tải lại website.

## Xem ảnh kiểm tra

- [Toàn trang trên máy tính](screenshots/barber-club/home-1440.png).
- [Toàn trang trên điện thoại](screenshots/barber-club/home-320.png).

Ảnh chụp từ database kiểm thử riêng, nên tên Salon A/B, Stylist A/B và giá trong
ảnh là fixture kiểm thử; không được thêm vào database khi người dùng cập nhật.
Các ảnh salon bên trong giao diện là ảnh chụp thật được ghi nguồn ở trên.

## Cập nhật tại VS Code trên Windows

Dừng server bằng **Ctrl+C**, chạy trong thư mục có `manage.py`:

```powershell
.\.venv\Scripts\python.exe scripts\cap_nhat_du_an.py
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

Mở `http://127.0.0.1:8000/`, nhấn **Ctrl+F5**. Bản này không thêm dependency hoặc
migration. Trình cập nhật giữ `.env`, `.venv`, database và sao lưu file thay đổi
vào `.local/cap-nhat-*`.

## File chính

- `templates/public/home.html` và `templates/public/club/`: bố cục trang chủ.
- `templates/partials/club_crest.html`: biểu trưng SVG riêng, kích thước giới hạn.
- `templates/base.html`: logo, favicon, thanh điều hướng/chân trang.
- `static/css/barber-club.css`: màu, logo và các nút thao tác chung.
- `static/css/barber-club-home.css`: bố cục, ảnh và responsive trang chủ.
- `scripts/quick_dialog_browser.py`: kiểm tra trang chủ mới cùng các luồng popup.

Kết quả kiểm tra cụ thể: [Biên bản kiểm chứng](validation/21-GIAO-DIEN-BARBER-CLUB.md).
