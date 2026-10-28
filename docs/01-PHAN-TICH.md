# Phân tích yêu cầu

## 1. Cơ sở và mục tiêu

Nguồn đầu vào: `1250080221_To_Hoang_Tuan.docx`, đề tài “Xây dựng hệ thống quản lý và đặt lịch tại chuỗi cắt tóc nam”. Tài liệu có phần mở đầu, khung chương và bảy bảng dữ liệu ban đầu; chưa có mã nguồn, use case chi tiết hoặc bằng chứng build. Những tuyên bố hoàn thành trong bản thảo được xem là mục tiêu cần kiểm chứng.

Vấn đề cần giải quyết: khách phải chờ giờ cao điểm, stylist trùng lịch, lễ tân thiếu thông tin phân ghế, quản lý khó đối soát doanh thu nhiều chi nhánh. Mục tiêu của bản xây dựng lại là đi hết một vòng phục vụ, từ chọn dịch vụ đến hóa đơn và đánh giá, với dữ liệu nhất quán.

Tên thương hiệu GENTLEMAN, địa chỉ, tên nhân viên, giá và lịch hẹn mẫu được đặt để trình diễn, không đại diện doanh nghiệp đang vận hành. Đây là giả định triển khai, không phải dữ liệu khảo sát thực tế.

## 2. Các bên sử dụng

| Tác nhân | Mục tiêu | Phạm vi |
|---|---|---|
| Khách vãng lai | Tìm chi nhánh, dịch vụ, stylist; tạo tài khoản | Thông tin công khai |
| Khách hàng | Đặt/hủy, xem lịch, hóa đơn, đánh giá | Lịch hẹn của chính mình |
| Lễ tân | Đón khách, phân ghế, điều phối, thanh toán | Chi nhánh được phân công |
| Quản trị viên | Quản lý toàn chuỗi, danh mục, ca làm và doanh thu | Toàn hệ thống; cổng quản trị riêng kiểm tra vai trò manager |

Stylist có cổng lịch/ca và cập nhật phục vụ của chính mình. Quản lý chi nhánh có quyền quản trị nguồn lực, tài khoản nhân sự và đối soát trong chi nhánh phụ trách. Cổng thanh toán mô phỏng là thành phần nội bộ, không phải ngân hàng bên ngoài.

## 3. Yêu cầu chức năng và tiêu chí nghiệm thu

| Mã | Yêu cầu | Tiêu chí có thể kiểm tra |
|---|---|---|
| FR01 | Tài khoản và phân quyền | Khách không vào trang điều hành; lễ tân không xem lịch khác chi nhánh |
| FR02 | Danh mục và tra cứu | Chỉ dịch vụ, stylist, chi nhánh đang hoạt động xuất hiện trong lựa chọn đặt |
| FR03 | Xem giờ trống | Dựa vào ca làm, tổng thời lượng, giờ mở cửa và lịch đã giữ chỗ |
| FR04 | Đặt nhiều dịch vụ | Lưu bản chụp giá/thời lượng; hai yêu cầu đồng thời cùng stylist chỉ thành công một |
| FR05 | Hủy lịch | Lịch khách hủy phải chưa check-in và còn đủ thời gian đổi/hủy theo chi nhánh; chỗ được giải phóng |
| FR06 | Check-in, phân ghế | Trong ngày hẹn; ghế đúng chi nhánh và không đang bận |
| FR07 | Phục vụ và thanh toán | Đúng thứ tự trạng thái, một hóa đơn, một lần cộng điểm |
| FR08 | Phản hồi | Chỉ chủ lịch đã hoàn thành được đánh giá 1–5 sao, một lần |
| FR09 | Nhân sự và ca làm | Ca không chồng lấn; không sửa ca làm mất khả năng phục vụ lịch đang giữ |
| FR10 | Doanh thu | Thực thu sau giảm, theo ngày thanh toán; lọc chi nhánh; Excel/PDF/CSV |
| FR11 | Thông báo và nhật ký | Mỗi thay đổi nghiệp vụ tạo thông báo cho khách và nhật ký người thao tác |
| FR12 | Lễ tân đặt hộ | Phải chọn khách trong phạm vi cho phép, ghi đúng người tạo trong nhật ký |
| FR13 | Khôi phục mật khẩu | Token 1 giờ, dùng một lần; không tiết lộ email tồn tại; local email/SMTP cấu hình |
| FR14 | Thông báo đầy đủ | Lọc/phân trang, đọc một/tất cả chỉ POST, liên kết lịch và quyền sở hữu |
| FR15 | Tra cứu nhật ký | Chỉ manager, lọc actor/ngày/nội dung/mã lịch, không sửa/xóa nhật ký |
| FR16 | Lịch tuần | Bảy ngày, ca làm và lịch; lọc chi nhánh/stylist theo quyền |
| FR17 | Hiệu quả hoạt động | So kỳ trước, tỷ lệ hủy/không đến, dịch vụ và stylist; doanh thu phân bổ khớp thực thu |
| FR18 | Điểm tích lũy | 1 điểm/10.000đ thực trả; đổi 1.000đ/điểm tối đa 20%; ledger, khóa số dư, không dùng trùng |
| FR19 | Sao lưu/phục hồi | Dump cùng snapshot, SHA256, phục hồi database mới và đối chiếu số dòng |
| FR20 | Đổi lịch và nhập/xuất | Giữ mã/giá snapshot khi đổi; Excel xem trước/xác nhận nguyên tử; lọc và phân trang |

## 4. Phi chức năng

| Nhóm | Thiết kế đáp ứng | Giới hạn kiểm chứng |
|---|---|---|
| Nhất quán | PostgreSQL transaction, row lock, GiST exclusion, unique/check constraints | Có kiểm thử hai yêu cầu đồng thời; chưa có benchmark tải lớn |
| Bảo mật | Password hashing Django, session, CSRF, autoescape, object-level permissions | Chưa đánh giá xâm nhập độc lập; cần rate limiting khi công khai |
| Khả dụng | Health endpoint và lệnh check_database kiểm tra PostgreSQL | Chưa có high availability hoặc SLA |
| Dễ sử dụng | Tiếng Việt, bộ lọc, trạng thái rõ ràng, responsive, label bàn phím | Đã kiểm tra desktop/mobile; chưa nghiệm thu với người dùng doanh nghiệp |
| Bảo trì | Models / services / forms / views / events; migration và test | Một Django application, phù hợp quy mô đồ án |
| Khả năng tái lập | Requirements ghim phiên bản, setup/start đa nền tảng | Cần cài và cấu hình PostgreSQL trên máy đích |

## 5. Use case chính

### UC01 — Đặt lịch

**Tiền điều kiện:** khách đã đăng nhập; có chi nhánh, dịch vụ đang hoạt động và ca làm. **Kích hoạt:** chọn “Đặt lịch”.

1. Chọn chi nhánh và một hoặc nhiều dịch vụ/combo.
2. Hệ thống lọc stylist thuộc chi nhánh, tính tổng thời lượng và giá dự kiến.
3. Chọn ngày trong số ngày nhận đặt trước của chi nhánh (mặc định 30); API trả về giờ còn trống theo bước 15 phút.
4. Chọn giờ, nhập ghi chú, xác nhận.
5. Server khóa chi nhánh và khách, đọc lại dữ liệu, kiểm tra xung đột, lưu lịch và các dòng dịch vụ.
6. Phát sự kiện, ghi audit và thông báo trong cùng transaction; trả về mã lịch.

**Ngoại lệ:** dịch vụ vừa ngừng, không có ca, thời gian đã qua, trùng stylist/khách, vượt giờ đóng cửa. Thất bại không để lại lịch hoặc thông báo dở dang. Giờ trống trên màn hình chỉ là thông tin tham khảo cho đến khi transaction xác nhận thành công.

### UC02 — Hủy lịch

Chủ lịch mở chi tiết, chọn hủy và xác nhận. Server kiểm tra quyền, trạng thái và hạn giờ được cấu hình ở chi nhánh. Chuyển sang `cancelled`, phát thông báo và trả chỗ cho lịch khác. Lễ tân có quyền hủy lịch chưa check-in thuộc chi nhánh mình, không áp dụng hạn giờ được cấu hình ở chi nhánh.

### UC03 — Đón khách và phục vụ

Lễ tân tìm khách bằng tên/điện thoại, mở lịch trong ngày, chọn ghế. Server kiểm tra ghế đúng chi nhánh và không bận; chuyển `booked → checked_in`. Khi stylist sẵn sàng, chuyển `checked_in → in_service`; không cho stylist bắt đầu hai khách đồng thời.

### UC04 — Thanh toán

**Tiền điều kiện:** lịch `in_service`. Lễ tân kiểm tra dịch vụ, chọn tiền mặt hoặc thẻ mô phỏng. Thẻ yêu cầu xác nhận rõ. Sau khi stylist/lễ tân hoàn tất phục vụ chuyển sang `awaiting_payment`, server khóa lịch, lấy tổng từ các dòng snapshot, tạo hóa đơn unique, trừ điểm theo yêu cầu (tối đa 20%), cộng điểm từ thực thu, ghi ledger và hoàn thành lịch và phát sự kiện. Bất kỳ bước nào lỗi đều rollback. Không thu thập số thẻ, OTP hoặc thông tin ngân hàng.

### UC05 — Quản lý ca làm

Quản trị mở Thiết lập & nhân sự → Ca làm, chọn stylist, bắt đầu và kết thúc. Ca phải trong một ngày và giờ mở cửa; PostgreSQL từ chối ca chồng lấn. Khi sửa ca, không được bỏ phạm vi chứa lịch đang đặt. Chỉ xóa ca khi không còn lịch hẹn đang cần phục vụ trong ca; mọi thao tác ghi dữ liệu qua cổng quản trị riêng.

### UC06 — Báo cáo

Chọn từ/đến (tối đa 366 ngày) và chi nhánh được phép. Truy vấn hóa đơn theo `paid_at`, tổng doanh thu, số hóa đơn, trung bình; hiển thị bảng theo chi nhánh và từng giao dịch. CSV có BOM cho Excel và xử lý ký tự có thể kích hoạt công thức.

## 6. Phạm vi bản hoàn thành

Bao gồm website khách hàng, cổng điều hành, quản trị danh mục, reset mật khẩu, nhật ký/thông báo/lịch tuần, phân tích hiệu quả, điểm tích lũy và công cụ sao lưu/phục hồi, database migration, dữ liệu mẫu, bộ kiểm thử, hướng dẫn chạy trực tiếp và tài liệu. Đã bổ sung kho vật tư, chuyển kho, hoa hồng, voucher, hoàn tiền toàn bộ và chốt sổ theo chi nhánh. Không bao gồm mobile native, mạng xã hội, SMS, kiểm chứng SMTP bên ngoài, thanh toán ngân hàng thật, bán lẻ sản phẩm, bảng lương/thuế, hoàn tiền một phần, AI và HA. Các nội dung này là hướng phát triển sau, không được mô tả là đã thực hiện.

## 7. Đối chiếu thiết kế ban đầu

| Thiết kế trong tài liệu | Bổ sung/điều chỉnh | Lý do |
|---|---|---|
| Khách hàng, nhân viên chưa có đăng nhập/phân quyền | `User` có role và chi nhánh phụ trách; `Employee` tách khỏi tài khoản | Chặn lộ lịch/khách chi nhánh khác |
| Ngày hẹn, giờ hẹn riêng | `start_at`, `end_at` aware datetime | Có tổng thời lượng, xử lý chồng lấn và múi giờ |
| Lịch hẹn thiếu dịch vụ chi tiết | `AppointmentItem` lưu snapshot | Một lịch nhiều dịch vụ và lịch sử giá ổn định |
| Chưa có ghế và ca làm | `Chair`, `Shift` | Khả dụng phụ thuộc nguồn lực thực |
| Hóa đơn tổng tiền chưa rõ nguồn | Unique invoice, từ các dòng snapshot | Chống thanh toán/cộng điểm hai lần |
| Thiếu nhật ký/thông báo | `AuditLog`, `Notification`, Observer | Truy vết và phản hồi khách |
| Mô tả SQL NVARCHAR chung | Migration PostgreSQL với varchar/text, timestamptz, GiST | Triển khai đúng hệ quản trị đã chọn |

## 8. Vận hành nhiều chi nhánh

Yêu cầu mở rộng FR21–FR32 và tiêu chí nghiệm thu tại [Nghiệp vụ nhiều chi nhánh](13-NGHIEP-VU-NHIEU-CHI-NHANH.md): tiếp nhận và kích hoạt hồ sơ tại quầy; sức chứa ghế; nghỉ/điều phối; dịch vụ phát sinh/gia hạn; phục vụ và thu tiền riêng; email outbox; vai trò quản lý chi nhánh/stylist; voucher; kho/chuyển kho; hoa hồng; hoàn tiền/thu hồi điểm; chốt sổ và đối soát theo thời điểm giao dịch.
