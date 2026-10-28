# Mẫu 3 — The Blue Edition

Bản giao diện được triển khai từ mẫu 3 đã chọn: xanh cobalt, xanh navy, nền giấy sáng, bố cục tạp chí và các chi tiết dạng phiếu hẹn. Website vẫn chạy bằng Django/PostgreSQL, không cần Docker, Node.js hoặc tải lại cả dự án.

## Những gì đã thay đổi

| Khu vực | Giao diện và hành vi thực tế |
|---|---|
| Trang chủ | Tiêu đề lớn, ảnh salon thật tự chuyển, hai ảnh nghiêng, dấu tròn đặt lịch, phiếu chọn chi nhánh; bảng dịch vụ dạng danh sách đánh số |
| Đặt lịch | Ba phần có liên kết điều hướng; chọn nhiều dịch vụ; phiếu bên cạnh cập nhật chi nhánh, stylist, ngày/giờ, thời lượng và giá tạm tính; đổi lựa chọn sẽ bỏ giờ cũ để kiểm tra lại khả dụng |
| Tài khoản | Thẻ thành viên, điểm, lịch hẹn sắp tới của chính khách đang đăng nhập; liên kết đổi/hủy/xem chi tiết; sửa hồ sơ và đổi mật khẩu |
| Điều hành | Thanh điều hướng dọc gọn, bộ lọc ngày/chi nhánh/khách/trạng thái, chỉ số thu ròng và lịch hẹn, các cột lịch riêng theo chi nhánh; thẻ mở trang xử lý lịch thật |
| Các trang còn lại | Đồng bộ màu, nút, bảng, biểu mẫu, trạng thái, báo cáo, kho, thiết lập, trang xác thực; giữ các đường dẫn và quyền xử lý hiện có |
| Điện thoại và bàn phím | Menu đóng bằng Escape hoặc bấm bên ngoài; nút Đăng xuất hiển thị ngoài menu; biểu tượng SVG giới hạn kích thước; điều hướng vẫn có thể mở khi tắt JavaScript |

Bảng điều hành phân trang **toàn bộ danh sách đã lọc**, sau đó đặt các lịch trên trang hiện tại vào đúng chi nhánh. Con số “lịch trên trang” khác “lịch trong ngày”; chuyển trang để xem phần còn lại. Thu ròng là số thu hóa đơn trừ hoàn tiền trong ngày/phạm vi được chọn. Bộ lọc khách/trạng thái chỉ lọc thẻ lịch, không thay đổi tổng ngày; xuất Excel/PDF tại đây là báo cáo tổng chi nhánh.

Phông nền cho nội dung, bảng và biểu mẫu là Segoe UI/Arial của máy. Be Vietnam Pro dùng cho tiêu đề, Lora italic dùng ở các câu nhấn được đánh dấu; file phông được phục vụ cục bộ. Không áp một phông trang trí lên toàn bộ chữ. Ảnh giữ nguồn tham khảo 30Shine, có ghi chú rõ trên trang, không gán ảnh tham khảo thành ảnh nhân viên/chi nhánh trong database.

Ảnh tự chuyển có nút trước/sau và dừng/bật. Hệ thống ngừng tự chuyển khi người dùng tương tác, tab bị ẩn hoặc ảnh ra khỏi vùng xem; `prefers-reduced-motion` chuyển sang điều khiển thủ công. Các phần nội dung hiện nhẹ khi cuộn và vẫn đọc được khi tắt JavaScript.

## Xem ảnh thực tế

Các ảnh chụp từ website chạy tại máy kiểm thử với dữ liệu mẫu/tài khoản thử, không phải ảnh dựng của bản preview:

- [Trang chủ — máy tính](screenshots/blue/home-1440.png) · [điện thoại](screenshots/blue/home-390.png)
- [Đặt lịch — máy tính](screenshots/blue/booking-1440.png) · [điện thoại](screenshots/blue/booking-390.png)
- [Tài khoản — máy tính](screenshots/blue/account-1440.png) · [điện thoại](screenshots/blue/account-390.png)
- [Điều hành — máy tính](screenshots/blue/board-1440.png) · [điện thoại](screenshots/blue/board-390.png)

Trang điều hành có thể hiện trạng thái trống nếu ngày đang chọn không có lịch; không sinh thêm lịch giả để lấp đầy giao diện.

## Cập nhật trong terminal VS Code trên Windows

Mở terminal PowerShell tại thư mục chứa `manage.py`. Nhấn **Ctrl+C** để dừng server, rồi chạy từng lệnh. Nếu một lệnh lỗi, xử lý lỗi đó trước khi chạy tiếp.

```powershell
.\.venv\Scripts\python.exe scripts\cap_nhat_du_an.py
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

Mở `http://127.0.0.1:8000/` và nhấn **Ctrl+F5**. Màn hình quản lý theo mẫu 3 nằm ở `http://127.0.0.1:8000/quan-ly/van-hanh/`, cũng có thể mở từ nút **Quản lý / Điều hành**.

Bản này không thêm migration hay thư viện runtime; lệnh migrate giúp máy đang dùng bản cũ áp dụng những migration còn thiếu, phiên bản mới nhất vẫn là `0010`. Công cụ cập nhật kiểm tra SHA256, tải đủ file rồi mới thay; bản nguồn cũ được sao lưu vào `.local/cap-nhat-.../sao-luu`. `.env`, `.venv` và database không bị công cụ cập nhật ghi đè. Không cần chạy lại `seed_demo` để nhận giao diện mới.

Nếu chưa có công cụ cập nhật hoặc đang giữ bản rất cũ, lấy bản mới vào thư mục tạm, rồi chạy với đường dẫn dự án hiện tại:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tunato2807-del/ptpmhdtuong/main/scripts/cap_nhat_du_an.py" -OutFile "$env:TEMP\gentleman-update.py"
.\.venv\Scripts\python.exe "$env:TEMP\gentleman-update.py" --project .
```

Sau đó chạy các lệnh migrate, collectstatic, check và runserver ở trên. Nếu còn thư viện thiếu do bỏ qua các bản cập nhật trước, chạy `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

## File để xem hoặc copy riêng

- [CSS của Blue Edition](../static/css/blue-edition.css), [JavaScript giao diện](../static/js/blue-edition.js), [logic phiếu đặt lịch](../static/js/app.js), [điều hướng khi tắt JavaScript](../static/css/no-js.css).
- [Khung chung](../templates/base.html), [trang chủ](../templates/public/home.html), [đặt lịch](../templates/public/booking.html), [tài khoản](../templates/public/profile.html).
- [Khung quản lý](../templates/staff/base.html), [cột lịch chi nhánh](../templates/business/blue_board.html), [workspace](../templates/business/workspace.html), [khung tính năng](../templates/features/page.html), [SVG](../templates/partials/blue_icon.html).
- [Dữ liệu điều hành](../salon/business_views.py), [dữ liệu hồ sơ](../salon/profile_views.py), [kiểm tra thiếu file](../salon/checks.py).

Các CSS nền cũ vẫn cần cho những màn hình dùng chung; `blue-edition.css` được nạp sau để phối giao diện thống nhất. Không chỉ copy CSS mới rồi bỏ qua template hoặc Python đi kèm.

## Nguồn thiết kế và kiểm tra

Áp dụng [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/28b3b8dee8c976df4fa3e94aed4e092ad43fcb03/.claude/skills/ui-ux-pro-max/SKILL.md) ở commit `28b3b8dee8c976df4fa3e94aed4e092ad43fcb03`: chọn hướng Editorial Grid/Magazine, phối màu xanh theo yêu cầu, bảo đảm tương phản, trạng thái tương tác, responsive, focus, reduced motion và SVG nhất quán. Các quy tắc đó được chuyển thành mã Django/CSS/JS trong dự án; người dùng website không phải cài skill.

Bằng chứng kiểm tra trên Python 3.12, Django 5.2, PostgreSQL 17 và Chromium:

- 182 kiểm thử Django đạt; gồm kiểm tra lịch sắp tới chỉ thuộc đúng khách, dữ liệu cột lịch không vượt quyền chi nhánh và bộ lọc không làm sai tổng ngày.
- `check`, `makemigrations --check --dry-run`, `collectstatic`, Ruff lint/format đạt; không thêm migration.
- 342 lượt trang/độ rộng từ 320 đến 1920 px: không tràn ngang, không lỗi tải tài nguyên/JavaScript; SVG có kích thước giới hạn; đăng xuất bằng POST hoạt động cho khách/lễ tân/quản lý.
- 48 lượt giao diện nghiệp vụ; tiếp nhận, chuyển trạng thái, voucher/thu tiền, hóa đơn, kho/chuyển kho, nghỉ đột xuất, hoàn tiền/chốt sổ và xuất dữ liệu đạt.
- Luồng đăng ký → đặt lịch → hủy lịch → tiếp nhận → phục vụ → thanh toán mô phỏng → hóa đơn → đánh giá và xuất CSV đạt. Script tạo chi nhánh/nhân sự riêng để kiểm tra tiếp nhận ngoài giờ mở cửa của dữ liệu demo, rồi dọn những bản ghi mình tạo.
- 24 lượt giao diện khách cùng đăng nhập/đăng xuất thật, giữ lựa chọn qua đăng nhập, giờ trống, phiếu cập nhật/bỏ giờ cũ, trình chiếu, menu, bàn phím, ảnh và chế độ không JavaScript đạt.
- 22 lượt axe WCAG A/AA trên 11 màn hình × hai độ rộng: không phát hiện vi phạm, lỗi JavaScript hoặc tràn ngang. Đây là kiểm tra tự động, không phải chứng nhận tiếp cận đầy đủ.
- Bảng điều hành 12 chi nhánh vẫn dùng 11 truy vấn trong kiểm thử. Đo lab trang chủ trên Chromium, mạng 1,6 Mbps/độ trễ 150 ms và CPU chậm 4 lần: LCP trung vị khoảng 2,94 giây, CLS khoảng 0,002; không phải Web Vitals từ người dùng thật.

Báo cáo axe/CDP đã lưu tại [blue-edition-browser.json](validation/blue-edition-browser.json).

Các script nằm trong `scripts/customer_ui_smoke.py`, `interface_smoke.py`, `business_smoke.py`, `browser_smoke.py`, `quality_browser.py`. Chỉ chạy trên database demo local; tài khoản/dữ liệu thử do script tạo được dọn sau khi chạy. CI có kiểm tra Django cho Python 3.12/3.14; kết quả local không thay thế việc xác nhận lần chạy CI hoặc thử trên máy Windows của bạn. Không thực hiện triển khai công khai, SMTP thật hoặc giao dịch thanh toán thật trong đợt này.
