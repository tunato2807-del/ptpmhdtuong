# Animation và ảnh tự chuyển

Bản cập nhật thêm trình chiếu ba ảnh thật ở đầu trang chủ. Ảnh tự chuyển mỗi 5,5 giây, chuyển mờ trong 850 ms và phóng nhẹ. Có nút ảnh trước/sau và Dừng/Bật tự chuyển. Chọn ảnh bằng tay sẽ dừng tự chuyển để giữ ảnh đang xem.

Ảnh tự tạm dừng khi rê chuột vào, dùng bàn phím trong khung ảnh, chuyển tab hoặc cuộn khung ảnh ra khỏi màn hình. Khi hệ điều hành bật giảm chuyển động, ảnh chỉ chuyển bằng tay. Không có JavaScript thì ảnh đầu tiên vẫn hiển thị, các nút tự động được ẩn.

Các thẻ dịch vụ/chi nhánh xuất hiện lần lượt khi cuộn; tiêu đề xuất hiện nhẹ, thẻ và nút phản hồi khi rê/bấm. Bản cập nhật không thêm phông chữ hoặc thay đổi nghiệp vụ.

## Copy vào bản dự án đã cập nhật trước đó

Dừng server. Mở từng link, chọn Raw / Copy raw file và thay **toàn bộ nội dung** đúng file trong VS Code:

1. [static/css/motion.css](../static/css/motion.css) — file mới, hiệu ứng và nút trình chiếu.
2. [static/js/motion.js](../static/js/motion.js) — file mới, điều khiển ảnh, dừng/chạy và giảm chuyển động.
3. [templates/public/home.html](../templates/public/home.html) — ba ảnh và nút điều khiển.
4. [templates/base.html](../templates/base.html) — nạp hai file mới, cập nhật phiên bản cache.
5. [salon/checks.py](../salon/checks.py) — báo lỗi rõ ràng nếu copy thiếu CSS/JS mới.

Ảnh sử dụng các file WebP đã có trong `static/images/photos`. Nếu chưa có bản sửa bố cục/đăng xuất, làm theo [hướng dẫn cập nhật đầy đủ](08-CAP-NHAT-TUNG-FILE.md) trước.

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

Nhấn Ctrl+F5 khi mở lại website. Không cần migrate hoặc cài thêm thư viện cho bản animation này.

## Tùy chỉnh tốc độ

Trong `static/js/motion.js`, `5500` là thời gian mỗi ảnh (mili giây). Đổi thành `7000` nếu muốn chuyển chậm hơn. Trong `static/css/motion.css`, `850ms` là thời gian chuyển mờ; `scale(1.045)` là mức phóng ảnh nhẹ. Các hiệu ứng chỉ tác động vào opacity/transform, không thay đổi kích thước bố cục.

## Kiểm tra bản cập nhật

Đã kiểm tra trên Chromium: chuyển ảnh theo thời gian, dừng không tự chạy lại, chuyển tay/quay vòng, bật lại tự chuyển, giảm chuyển động và ảnh dự phòng khi tắt JavaScript. Bố cục đạt ở 320/390/768/1024/1440px, không phát sinh lỗi JavaScript. Ở 320px, các nút nhận click đúng; rê chuột/cuộn ảnh ra ngoài màn hình dừng tự chạy và trở lại màn hình tiếp tục chạy. Django check và collectstatic thành công.
