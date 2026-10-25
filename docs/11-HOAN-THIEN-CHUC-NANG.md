# Hoàn thiện các phần tiếp theo

Bản này bổ sung quên mật khẩu, trang thông báo, nhật ký quản trị, lịch tuần, phân tích hiệu quả, sao lưu/phục hồi và lịch sử/sử dụng điểm. Giữ giao diện quản trị riêng, chạy PostgreSQL trực tiếp, không cần Docker.

## Cập nhật từ bản hiện tại

Dừng server. Trong thư mục chứa `manage.py`:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tunato2807-del/ptpmhdtuong/main/scripts/cap_nhat_du_an.py" -OutFile ".\scripts\cap_nhat_du_an.py"
.\.venv\Scripts\python.exe .\scripts\cap_nhat_du_an.py
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

**Phải chạy migrate trước khi mở trang mới.** Migration `0003` thêm trường thông báo/giảm điểm và bảng lịch sử điểm; `0004` ghi số dư chuyển tiếp từ điểm đang có, không cộng lại hóa đơn cũ, không sửa tổng tiền hóa đơn đã thanh toán. Không chạy lại seed khi cập nhật. Mã và tài liệu cũ được sao lưu; `.env`, `.venv`, database giữ nguyên. Script cũng đồng bộ tài liệu và báo cáo Word cập nhật vào `docs/`.

Nếu copy thủ công, toàn bộ mã có trên GitHub: [operations.py](../salon/operations.py), [models.py](../salon/models.py), [services.py](../salon/services.py), [events.py](../salon/events.py), [views.py](../salon/views.py), [features.py](../salon/features.py), [urls.py](../salon/urls.py), [checks.py](../salon/checks.py), [settings.py](../config/settings.py), [migration](../salon/migrations), [templates/operations](../templates/operations), [templates/auth](../templates/auth), các template base/hồ sơ/hóa đơn/chi tiết, [CSS quản trị](../static/css/management.css), [JS app](../static/js/app.js). Copy trọn bộ cùng phiên bản để không thiếu template.

## Vị trí các chức năng

| Đường dẫn | Hành vi | Quyền |
|---|---|---|
| `/quen-mat-khau/` | Gửi liên kết đặt lại, token hiệu lực 1 giờ; dùng một lần sau khi đổi thành công | Công khai |
| `/thong-bao/` | Lọc đọc/chưa đọc, phân trang, xem lịch, đánh dấu một/tất cả đã đọc | Chỉ thông báo của mình |
| `/diem-tich-luy/` | Quy tắc và lịch sử điểm, số dư sau từng biến động, liên kết hóa đơn | Chỉ điểm của mình |
| `/quan-ly/nhat-ky/` | Tra cứu người thao tác, ngày, nội dung/mã lịch; chỉ đọc | Quản trị |
| `/quan-ly/lich-tuan/` | Bảy ngày từ thứ Hai; tuần trước/sau; lọc chi nhánh, stylist; xem ca và mở lịch | Operator trong phạm vi chi nhánh |
| `/quan-ly/hieu-qua/` | Doanh thu kỳ này/kỳ trước, dịch vụ, stylist, hủy/không đến; Excel/PDF | Operator trong phạm vi chi nhánh |

Các liên kết mới nằm trong menu quản trị, thanh điều hướng khách và hồ sơ. Thông báo cũ vẫn được giữ; chỉ thông báo phát sinh sau cập nhật có FK lịch để dẫn tới chi tiết.

## Email khôi phục mật khẩu

Mặc định khi DEBUG=1, email được lưu thành file trong `.local/emails` để demo trên máy, **không gửi ra hộp thư thật**. Mở file mới nhất để xem liên kết. Không công khai thư mục này hoặc chia sẻ liên kết đặt lại. Tài khoản cần có email, đang hoạt động và có mật khẩu; tài khoản nhập Excel chưa được đặt mật khẩu sẽ không nhận luồng reset cho tới khi quản trị đặt mật khẩu.

Để gửi thật, thêm thông tin SMTP của bạn vào `.env` (không commit mật khẩu):

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=YOUR_EMAIL
EMAIL_HOST_PASSWORD=YOUR_APP_PASSWORD
DEFAULT_FROM_EMAIL=Gentleman <YOUR_EMAIL>
```

Thay giá trị bằng dịch vụ email thực tế rồi khởi động lại. Liên kết dùng domain đang truy cập website; localhost chỉ mở được trên chính máy đó. Các bài kiểm thử dùng email backend trong bộ nhớ, không gửi thư ra ngoài. Cấu hình SMTP cần được xác minh với nhà cung cấp email trên máy triển khai.

Yêu cầu lặp cùng email trong một phút được gộp qua cache mặc định của Django (cache cục bộ theo process). Đưa lên nhiều worker cần dùng cache chung để giới hạn thống nhất. Kết quả không tiết lộ email có tồn tại; token hết hạn/đã dùng bị từ chối, mật khẩu mới đi qua các validator Django.

## Điểm và số tiền thanh toán

- Mỗi 10.000đ thực trả sau giảm được 1 điểm, làm tròn xuống.
- 1 điểm giảm 1.000đ; giảm tối đa 20% giá dịch vụ trên lịch.
- Chỉ dùng điểm đang có trước giao dịch. Lễ tân nhập số điểm theo yêu cầu của khách khi thanh toán; màn hình tính trước số tiền cần thu, server kiểm tra lại.
- Khóa số dư khách trong transaction, không cho hai chi nhánh dùng trùng điểm. Hóa đơn, trừ/cộng điểm, lịch sử điểm và trạng thái lịch cùng thành công hoặc cùng hoàn tác.
- Hóa đơn in/PDF có tiền dịch vụ, giảm điểm và thực thu. Báo cáo sử dụng thực thu. Doanh thu theo dịch vụ phân bổ theo tỷ trọng giá snapshot, phần làm tròn được đưa vào dòng cuối để tổng khớp hóa đơn.
- Lịch sử điểm chỉ đọc. Số dư chuyển tiếp là điểm trước nâng cấp; không dựng lại lịch sử từng hóa đơn mà không có dữ liệu xác nhận.

## Sao lưu và phục hồi PostgreSQL

Chạy trên terminal, không mở chức năng khôi phục qua web. Cần `pg_dump`/`pg_restore` của phiên bản PostgreSQL phù hợp và tài khoản có quyền đọc nguồn; thử phục hồi cần quyền CREATEDB.

Nếu lệnh không tìm thấy công cụ, thêm vào `.env` đúng phiên bản đã cài, ví dụ:

```dotenv
POSTGRES_BIN=C:/Program Files/PostgreSQL/17/bin
```

Sao lưu tạo file `.dump` và `.dump.json` cùng thư mục. Metadata ghi SHA256 và số dòng từng bảng; hai phần lấy cùng snapshot PostgreSQL để không lệch khi có giao dịch mới.

```powershell
.\.venv\Scripts\python.exe manage.py backup_database
```

Hoặc chọn tên mới cho lần sao lưu:

```powershell
.\.venv\Scripts\python.exe manage.py backup_database --output .local/backups/truoc-cap-nhat.dump
```

Giữ cả hai file, sao chép tới nơi lưu trữ riêng. Bản sao lưu chứa dữ liệu ứng dụng và hash mật khẩu nên không đưa lên GitHub. File đích đã tồn tại không bị ghi đè.

Thử phục hồi vào **database mới, chưa tồn tại**:

```powershell
.\.venv\Scripts\python.exe manage.py restore_database --file .local/backups/truoc-cap-nhat.dump --target-db gentleman_phuchoi_thu --confirm gentleman_phuchoi_thu
```

Lệnh từ chối tên database đang dùng, database hệ thống, database đích đã tồn tại hoặc tên xác nhận không khớp. Trước khi phục hồi, đối chiếu SHA256; sau khi phục hồi, đối chiếu số dòng tất cả bảng. Không tự chuyển `.env` sang database mới. Bạn có thể kiểm tra bản phục hồi bằng pgAdmin; chỉ khi đã xác minh mới tự chọn database đó trong cấu hình. Nếu phục hồi lỗi, database gốc giữ nguyên, database thử được giữ để kiểm tra.

Có thể dùng Windows Task Scheduler để chạy `backup_database` theo ngày bằng đường dẫn tuyệt đối của `.venv/Scripts/python.exe` và `manage.py`; đặt **Start in** là thư mục dự án. Lịch tự chạy trên máy người dùng chưa được cài trong phiên làm việc này.


## Bằng chứng kiểm tra và tài liệu

- [Kết quả kiểm tra bản hoàn thiện](validation/11-HOAN-THIEN.txt): 114 tests, 342 lượt trang/kích thước, kiểm tra trình duyệt và phục hồi thử.
- [Màn hình hiệu quả](screenshots/completion/performance.png) và [lịch sử điểm](screenshots/completion/points.png) chụp với dữ liệu demo/fixture kiểm thử.
- [Báo cáo Word cập nhật](BAO_CAO_PHAN_TICH_THIET_KE.docx), [phân tích](01-PHAN-TICH.md), [thiết kế](02-THIET-KE.md), [từ điển dữ liệu](05-TEN-COT-DU-LIEU.md).

Kiểm tra tùy chọn bằng `scripts/operations_smoke.py` sau khi cài Playwright theo README; chỉ chạy trên local DEBUG, script tạo và dọn đúng dữ liệu thử của nó.
