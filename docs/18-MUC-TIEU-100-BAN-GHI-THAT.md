# Mục tiêu 100 bản ghi thật cho mỗi bảng

Yêu cầu “mỗi bảng 100 dữ liệu” được hiểu là mục tiêu số lượng, đồng thời giữ yêu cầu trước đó: chỉ lấy từ website chính thức 30Shine, không bịa và không dùng dữ liệu mẫu làm dữ liệu vận hành.

Website công khai có thể cung cấp danh mục salon, dịch vụ và sản phẩm. Khách hàng, nhân viên nội bộ, ghế/ca, lịch hẹn, hóa đơn, hoàn tiền, kho và sổ điểm cần dữ liệu thực tế của đơn vị quản lý hoặc phát sinh từ hoạt động thật. Nhật ký, thông báo và bộ đếm xác thực cũng phải phát sinh đúng sự kiện; không tạo 100 dòng cho đủ bảng. Chỉ có đủ số dòng không chứng minh chúng là dữ liệu thật.

## Công cụ đã thêm

### 1. Kiểm đếm tất cả bảng của ứng dụng

Trong terminal PowerShell tại thư mục chứa manage.py:

```powershell
.\.venv\Scripts\python.exe manage.py audit_data_targets --target 100 --output .local\data-targets.json
```

Lệnh chỉ đọc số dòng của 26 bảng ứng dụng và ghi báo cáo: tên bảng, số đang có, số thiếu so với 100, loại nguồn cần bổ sung. Không in tên, điện thoại, email, giá trị hóa đơn hay nội dung bản ghi. `verified_real_rows: null` có nghĩa chưa kiểm chứng nguồn của các dòng đang có; không phải đã xác nhận chúng là thật hoặc là giả. Lệnh không tạo, sửa hoặc xóa dữ liệu.

### 2. Thu thập danh mục công khai từ máy Windows của bạn

Nếu máy của bạn truy cập được website chính thức:

```powershell
.\.venv\Scripts\python.exe scripts\collect_30shine.py --target 100 --max-pages 300 --output .local\30shine
```

Kết quả ở `.local/30shine/catalogue.json`; các bản nguồn nằm trong `.local/30shine/sources/`. Công cụ cố gắng thu tối đa 100 mục duy nhất cho mỗi nhóm `branches`, `services`, `products`, giữ nguyên URL, thời điểm đọc, SHA256 và vị trí dữ liệu có cấu trúc. Bản ghi lặp không được dùng để tăng số lượng. Nếu một nhóm chỉ có 12 mục đọc được thì báo 12/100, thiếu 88; không tạo thêm 88 dòng.

Công cụ dùng JSON-LD công khai do trang nguồn cung cấp, theo liên kết danh mục/sitemap và quy tắc robots.txt; không đăng nhập, không gọi API riêng, không đọc tên khách/review/đơn hàng để làm dữ liệu. Chỉ nhận HTTPS trên `30shine.com` hoặc `www.30shine.com`, không theo chuyển hướng sang tên miền khác, không dùng proxy thay thế hoặc bỏ kiểm tra TLS. Không cần Playwright, Docker hay dependency runtime mới; XML dùng defusedxml đã có trong requirements.

Nếu muốn bắt đầu từ trang danh mục công khai cụ thể, có thể thêm `--url` với URL chính thức bạn đang xem. Không điền một URL đoán là có dữ liệu hoặc URL tài khoản/đặt lịch. Trang phải cung cấp cấu trúc được hỗ trợ; JavaScript phía trình duyệt hoặc cấu trúc khác có thể cần đối chiếu thủ công trước khi viết bộ đọc bổ sung.

### 3. Phân biệt gói nguồn và bản ghi vận hành

`catalogue.json` là gói thu thập để đối chiếu, **chưa phải lệnh nhập vào database**. Các trường không được công bố sẽ không có trong gói. Giá `lowPrice`, khoảng giá, thời hạn và các điều kiện trong offers được giữ dưới dạng gốc; không biến giá “từ” thành một đơn giá cố định. Không đoán thời lượng/giờ mở cửa/số ghế để ép bản ghi đi qua validation của hệ thống.

Một salon bên ngoài có địa chỉ công khai không có nghĩa được phép nhận đặt lịch qua GENTLEMAN. Sau khi kiểm tra gói nguồn, cần chốt mô hình dữ liệu tham khảo/phạm vi vận hành trước khi nhập. Bảng cần dữ liệu nội bộ chỉ có thể nhận file Excel/CSV thật của bạn hoặc dữ liệu phát sinh thật trong ứng dụng.

Mã thoát của collector:

- `0`: đã thu đủ số mục duy nhất yêu cầu ở cả ba nhóm; vẫn cần đối chiếu nội dung/trường thiếu trước khi nhập.
- `2`: chưa đủ số lượng hoặc có nguồn bị chặn; xem counts/shortfalls/errors trong catalogue.json.
- `1`: tham số hoặc thư mục đầu ra không hợp lệ.

Nếu số lượng bằng 0 nhưng nguồn trả thành công, website có thể không cung cấp JSON-LD thuộc nhóm được hỗ trợ. Không sửa số lượng trong file hoặc tự điền dữ liệu. Gửi gói nguồn đọc được để đối chiếu cấu trúc, hoặc cung cấp bản xuất dữ liệu công khai từ trang chính thức. Không gửi mật khẩu, cookie hoặc file chứa dữ liệu cá nhân không cần thiết.

## Trạng thái thực hiện ngày 06/11/2026

- Audit đã đọc được số dòng của 26 bảng, không ghi vào database và không xác nhận giả định nguồn của các dòng cũ.
- Đã chạy collector với mục tiêu 100 tại môi trường cloud. Truy cập nguồn chính thức vẫn bị proxy từ chối; kết quả thực là **0 chi nhánh, 0 dịch vụ, 0 sản phẩm**, `targets_met=false`, `database_written=false`. Không có bản ghi 30Shine mới được nhập.
- Draft có `30shine.com` và `www.30shine.com` nhưng runtime chưa áp dụng. Cách áp dụng tại [trạng thái nguồn](17-DU-LIEU-THUC-30SHINE.md). Bạn cũng có thể chạy collector trực tiếp trên máy Windows đang truy cập được nguồn, theo lệnh trên.
- Kiểm thử parser/collector sử dụng fixture tạm, không phải nguồn thật và không được seed vào ứng dụng. Mục tiêu kiểm thử là không tạo số liệu bù, không tăng số bằng trùng lặp, giữ điều kiện giá, bảo vệ tên miền và báo rõ thiếu dữ liệu.

Báo cáo và bằng chứng nguồn được giữ dưới `.local`, không đưa dữ liệu máy bạn lên GitHub bằng công cụ cập nhật nguồn.

## Bằng chứng kiểm tra công cụ

Ngày 06/11/2026: 200 kiểm thử Django đạt trên PostgreSQL, gồm 11 kiểm thử mới cho thu thập/kiểm đếm; check, migration drift, collectstatic và Ruff đạt. Không có migration mới. Bộ thử trực tiếp nguồn thật vẫn thu được 0 mục do CONNECT 403, được báo thiếu với mã thoát 2; database không bị ghi. Các con số kiểm thử không phải số lượng bản ghi thật đã thu thập.
