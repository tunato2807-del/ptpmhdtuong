# Kiểm thử và kết quả build

## 1. Môi trường thực thi

Python 3.12.14, Django 5.2.18, psycopg 3.3.6, PostgreSQL 17.11 native (Debian 17.11-0+deb13u1). Kiểm thử nghiệp vụ dùng PostgreSQL thực, không thay bằng SQLite hoặc mock database. Browser smoke dùng Playwright 1.62.0 và Chromium headless cài riêng.

## 2. Kết quả thực tế

| Kiểm tra | Kết quả | Bằng chứng / phạm vi |
|---|---|---|
| `python scripts/dev.py setup --no-demo` | Đạt | Cài dependencies, kiểm tra PostgreSQL native, không có migration mới, collectstatic thành công; không nạp lại dữ liệu |
| `manage.py check` | Đạt | 0 vấn đề |
| `makemigrations --check --dry-run` | Đạt | No changes detected |
| `manage.py test salon.tests --noinput` | Đạt | 179 test đã thực thi, 0 failed, 0 errors, 0 skipped |
| Migration tên cột tiếng Việt | Đạt | 80 cột/12 bảng; kiểu dữ liệu và toàn bộ bản ghi giữ nguyên; kiểm tra cả nâng cấp và hoàn tác |
| `collectstatic --noinput` | Đạt | Static và manifest tạo thành công; chạy lại giữ nguyên tài nguyên không đổi |
| `scripts/start.sh` | Đạt | Dùng PostgreSQL native đang chạy, kiểm tra migration và bật Django; không quản lý database qua container |
| Browser smoke local | Đạt | Đi hết đăng ký/đặt/hủy/check-in/phục vụ/thanh toán mô phỏng/hóa đơn/đánh giá/CSV |
| Responsive | Đạt | Giao diện khách hàng 320/360/390/768/1024/1440 px; không tràn ngang; menu mobile/Escape hoạt động |
| Customer UI smoke | Đạt | Bộ lọc, bộ sưu tập, preselect dịch vụ/stylist/chi nhánh, đăng nhập giữ lựa chọn, reduced motion, không JavaScript, ảnh/font local |
| Quản trị và hồ sơ | Đạt | Tạo/sửa/xóa sáu nhóm, phân quyền manager, xác nhận xóa, sửa hồ sơ, xác thực mật khẩu hiện tại, đăng nhập lại; 320–1440 px |
| Schema | Đạt | 0003–0007 thêm trường và bảng nghiệp vụ; 192 cột/25 bảng, cột cũ giữ nguyên kiểu |
| JavaScript | Đạt | Không có pageerror trong luồng browser smoke |
| `check --deploy --fail-level WARNING` | Đạt với cấu hình production thử nghiệm | DEBUG=0 và secret ngẫu nhiên tạm thời; không phải bằng chứng đã bật HTTPS hoặc public deployment |
| GitHub Actions | Chưa xác minh kết quả trên GitHub | Đã có workflow test/build; xem tab Actions của repository để theo dõi |
| Ngân hàng/SMS, SMTP thật, tải lớn, restore production | Chưa thực hiện | Email giả lập và restore database thử đã kiểm tra; tích hợp bên ngoài chưa cấu hình |

Bản quản trị riêng được kiểm tra trên PostgreSQL native, ứng dụng kết nối trực tiếp qua TCP. Chuyển dữ liệu cloud sang database native bằng pg_dump/pg_restore có backup; đối chiếu số dòng và SHA256 nội dung của cả 12 bảng trước/sau trùng nhau. Database nguồn được giữ nguyên. Đây là kiểm chứng chuyển môi trường phát triển, không thay cho diễn tập khôi phục production.

Bộ test mới phát hiện trường hợp ca làm có giờ kết thúc trước giờ bắt đầu khiến TSTZRANGE lỗi ngay trong bước kiểm tra form. Mã đã sửa: trả lỗi theo trường trước khi gửi khoảng không hợp lệ xuống PostgreSQL. Test đồng thời đóng hẳn connection của từng worker trước khi kết thúc để runner dọn được database test. Toàn bộ tests và bước dọn database chạy lại thành công. Script check thu thập static trước tests để manifest có đủ tài nguyên mới. Kết quả tại `docs/validation/custom-management.txt`.

## 3. Các nhóm kiểm thử nghiệp vụ

| Nhóm | Trường hợp tiêu biểu | Yêu cầu liên quan |
|---|---|---|
| Đặt lịch | Nhiều dịch vụ, tổng thời lượng, snapshot không đổi sau sửa giá | FR03, FR04 |
| Khả dụng | Ca làm, giờ mở/đóng, thời gian quá khứ, số ngày nhận trước theo chi nhánh, bước 15 phút | FR02, FR03 |
| Xung đột | Stylist trùng, hai lịch sát giờ, khách trùng ở chi nhánh khác, bypass service bị DB chặn | FR04 |
| Migration cột | So sánh dữ liệu và kiểu PostgreSQL trước/sau, hoàn tác rồi nâng cấp lại, giữ FK và nhóm quyền đăng nhập | Toàn vẹn schema |
| Đồng thời | Hai thread với hai connection cùng đặt một stylist/giờ, chỉ một lịch được ghi | FR04 |
| Hủy/no-show | Hủy giải phóng chỗ; hạn 2 giờ; no-show sau thời gian chờ muộn theo chi nhánh | FR05 |
| Lễ tân | Đặt hộ đúng khách, actor đúng; khách ngoài phạm vi bị từ chối | FR01, FR12 |
| Đón khách | Check-in đúng ngày; từ chối ghế khác chi nhánh hoặc ghế bận | FR06 |
| Checkout | Không nhảy trạng thái; một hóa đơn/một lần điểm; mock phải xác nhận | FR07 |
| Ca làm | Không sửa/xóa ca làm mất phạm vi phục vụ lịch đã đặt; từ chối ca đảo giờ/trùng giờ | FR09 |
| CRUD riêng | Sáu nhóm tài nguyên, chặn khách/lễ tân, không cần staff/superuser, FK PROTECT và CSRF | FR09, FR12 |
| Cá nhân | Chỉ sửa thông tin liên hệ của mình, không sửa vai trò/điểm; đổi mật khẩu cần mật khẩu hiện tại và giữ phiên | FR01 |
| HTTP/Auth | Trang yêu cầu login; khách không vào quản lý; chủ khác nhận 404; CSRF; POST-only; chống open redirect | FR01 |
| Báo cáo | Render thống kê, CSV chống công thức, hóa đơn chỉ đúng người xem | FR10 |
| Đánh giá | Chỉ sau completed; số sao hợp lệ; không đánh giá hai lần | FR08 |
| Sự kiện | Đặt lịch có audit/notification; đặt hộ lưu actor thực | FR11 |

## 4. Kiểm tra thủ công có thể lặp lại

1. Đăng nhập khách, chọn stylist không có ca tại ngày sau phạm vi được cấp; không có giờ để đặt.
2. Chọn hai dịch vụ rồi đổi sang một dịch vụ; danh sách giờ và tổng được cập nhật, giờ chọn cũ bị bỏ.
3. Gửi cùng một form đặt hai lần; yêu cầu sau không tạo lịch trùng.
4. Lễ tân đăng nhập Quận 1 và thay ID URL sang lịch Quận 3; không xem được đối tượng.
5. Thanh toán mô phỏng không tick xác nhận; không có hóa đơn và điểm mới.
6. Thanh toán xong rồi tải lại/gửi lại; không có hóa đơn thứ hai.
7. Chọn ngày báo cáo không có giao dịch; tổng 0, không hiển thị tăng trưởng giả.

Không xem PID hoặc port mở là tiêu chí đủ; browser smoke kiểm tra hành vi đến tận hóa đơn và đánh giá. Script browser dọn đúng dữ liệu của tài khoản smoke vừa tạo; bộ Django test dùng database riêng.

## 5. Hình minh họa

![Trang chủ desktop](screenshots/home-desktop-top.png)

![Tổng quan vận hành desktop](screenshots/dashboard-desktop.png)

![Biểu mẫu đặt lịch](screenshots/booking-desktop.png)

![Tổng quan trên mobile](screenshots/dashboard-mobile.png)

Ảnh chụp từ bản chạy với dữ liệu mẫu. Số liệu trong ảnh phản ánh thời điểm chụp, không phải doanh thu của một cửa hàng thực.

## 6. Kết luận nghiệm thu bản phát triển

Quy trình phát triển và trình diễn cốt lõi chạy trực tiếp với Python và PostgreSQL native, có hướng dẫn VS Code/Windows và script đa nền tảng. Mã nguồn và tài liệu được lưu trong checkout và đã đẩy lên nhánh main của repository GitHub tunato2807-del/ptpmhdtuong theo yêu cầu người dùng. Ứng dụng chưa được triển khai thành dịch vụ công khai. Cấu hình môi trường cloud được lưu nháp để người dùng xem và publish; việc publish và phục hồi ở task mới là bước riêng, chưa được tuyên bố đã kiểm chứng.


## 8. Kiểm tra phần hoàn thiện

160 tests bao gồm reset mật khẩu (email giả lập, token hết hạn/dùng lại, CSRF, gộp yêu cầu), thông báo và lịch sử điểm đúng chủ sở hữu, nhật ký chỉ manager, lịch tuần/báo cáo đúng scope, phân bổ doanh thu sau giảm, ràng buộc database và hai chi nhánh thanh toán đồng thời không dùng trùng điểm. Migration opening giữ nguyên số dư cũ, không cộng lại hóa đơn.

Kiểm tra trình duyệt ở sáu chiều rộng trên bản mới bao phủ thêm thông báo, điểm, lịch tuần, hiệu quả, nhật ký và trang quên mật khẩu. Công cụ backup/restore đã chạy trên PostgreSQL native: 22 bảng phục hồi vào database thử mới có số dòng khớp snapshot, thử phục hồi lần hai bị từ chối; database thử được dọn sau kiểm tra, database nguồn giữ nguyên. Email SMTP thật và Windows Task Scheduler cần cấu hình trên máy triển khai, không được mô tả là đã xác minh trong phiên cloud.

## 9. Nghiệm thu nghiệp vụ nhiều chi nhánh (28/10/2026)

160 tests đã thực thi gồm phân quyền quản lý chi nhánh/stylist, sức chứa ghế theo sweep-line, ca/nghỉ/chốt sổ, tiếp nhận và kích hoạt hồ sơ khách tại quầy, dịch vụ phát sinh và rollback, phục vụ xong/chờ thu, quote voucher/điểm, hoàn tiền và điểm cần thu hồi, hoa hồng snapshot, chốt sổ, kho và outbox. Kiểm thử đồng thời bao gồm một ghế cho hai stylist, lượt voucher cuối giữa hai chi nhánh, hai yêu cầu xuất cùng tồn, đặt trùng và dùng trùng điểm.

Trình duyệt kiểm tra thêm 48 trang/kích thước cho khu vận hành ở 320/390/768/1024/1440/1920px, không tràn trang, lỗi JavaScript hoặc thiếu tài nguyên. Kịch bản `scripts/business_smoke.py` dùng dữ liệu riêng và đi hết tiếp nhận → check-in → stylist bắt đầu → thêm dịch vụ → hoàn tất → voucher/thu tiền → PDF → nhập/chuyển kho → nghỉ/đổi stylist → hoàn tiền → chốt sổ. `scripts/interface_smoke.py` tiếp tục kiểm tra 342 lượt trang/kích thước của giao diện hiện có.

Bằng chứng chi tiết và giới hạn tại [validation/13-NGHIEP-VU.txt](validation/13-NGHIEP-VU.txt). Email kiểm thử dùng locmem/file; không gửi Gmail/SMTP thật. Python thực thi cloud là 3.12, có workflow 3.14 nhưng chưa xác minh kết quả Actions mới. Chưa benchmark tải sản xuất hoặc cài Task Scheduler trên máy Windows người dùng.

Sao lưu/phục hồi bản mở rộng: 34 bảng được phục hồi và đối chiếu số dòng. Đã phục hồi bản trước migration vào database thử rồi so sánh toàn bộ bản ghi/cột cũ của 13 bảng nghiệp vụ với database mới: trùng nhau, ngoại trừ last_login cập nhật do kiểm tra đăng nhập. Hai database thử đã được dọn.


## Rà soát Agent Skills

Bộ kiểm tra mới có 179 test PostgreSQL đạt, gồm phân quyền sau khóa, tài khoản/khôi phục mật khẩu, hoàn điểm theo cả hai thứ tự, nâng cấp số dư cũ, bộ đếm xác thực đồng thời và ngân sách truy vấn. 342 kiểm tra route/viewport và 48 màn hình vận hành đạt. Quét axe gồm 22 cặp trang/kích thước ở desktop/mobile, 0 vi phạm trong các quy tắc đã chạy. Định dạng 61 file Python có AST giống trước/sau; lint/build đạt. Chi tiết giới hạn và số đo CDP xem [tài liệu 14](14-AGENT-SKILLS.md), bằng chứng tại `validation/14-AGENT-SKILLS.txt`.
