# GENTLEMAN Constitution

## Core Principles

### I. Phát triển từ yêu cầu có thể kiểm chứng

Mỗi thay đổi nghiệp vụ có đặc tả phạm vi, tác nhân, quy tắc, ngoại lệ và tiêu chí nghiệm thu. Theo luồng Spec Kit: specify → clarify khi cần → plan → tasks → analyze → implement → converge. Tính năng hoàn tất phải có bằng chứng kiểm tra tương ứng; tài liệu ghi rõ những gì chưa được kiểm chứng. Không dựng lại toàn bộ dự án chỉ để khớp một template.

### II. Phân quyền theo người dùng và chi nhánh

Khách chỉ xem/sửa hồ sơ và lịch của mình. Lễ tân/quản lý chi nhánh chỉ thao tác trong phạm vi được giao; stylist chỉ vận hành lịch được phân công; manager quản trị toàn chuỗi. Kiểm tra quyền ở server cho từng truy vấn/thao tác, kể cả sau khi chờ khóa. Không dùng việc ẩn nút thay cho phân quyền. Giữ session, CSRF, băm mật khẩu và giới hạn xác thực hiện có.

### III. Lịch hẹn nhất quán với nguồn lực

Giờ trống phải xét giờ mở cửa, ca, nghỉ, stylist, khách và số ghế; kiểm tra lại khi ghi dữ liệu trong transaction. Giữ ràng buộc PostgreSQL chống chồng lấn. Thứ tự khóa: chi nhánh trước lịch/khách/voucher/kho; khóa nhiều chi nhánh theo ID tăng dần. Lịch chuyển trạng thái theo quy trình; đổi/hủy không xóa lịch sử.

### IV. Bảo toàn chứng từ và dữ liệu lịch sử

Tên, giá, thời lượng dịch vụ trong lịch là snapshot. Hóa đơn, biến động kho, điểm và hoàn tiền phải có bút toán/chứng từ truy vết; không sửa/xóa để làm mất lịch sử. Giữ kiểm tra chống thu tiền, cộng điểm, dùng voucher hoặc xuất kho trùng. Thay đổi tài chính, quyền hoặc xác thực cần kiểm thử hồi quy tái hiện lỗi trước khi sửa.

### V. Kiến trúc và trải nghiệm phù hợp dự án

Giữ Django 5.2 LTS, PostgreSQL cài trực tiếp, giao diện HTML/CSS/JavaScript kết xuất phía server và cổng quản lý riêng. Hỗ trợ Python 3.12–3.14; không coi ma trận CI là bằng chứng đã chạy mọi phiên bản. SQL nghiệp vụ dùng cột tiếng Việt viết liền không dấu qua db_column; kiểu dữ liệu và thuộc tính Python theo quy ước hiện có. Phông trang trí có phạm vi, tiếng Việt rõ, SVG có kích thước giới hạn, đăng xuất bằng POST dễ thấy, hỗ trợ bàn phím và reduced motion.

## Dữ liệu và môi trường

Giữ .env, .venv, .local, database và chỉnh sửa của người dùng. Không đưa mật khẩu, token, liên kết reset, cookie, email/điện thoại hay dữ liệu khách thật vào spec, ảnh kiểm thử hoặc log. Không tự gửi email thật, gọi thanh toán thật, chạy công cụ/mô hình tính phí hoặc triển khai công khai từ một mẫu workflow. Phạm vi đã được người dùng giao trong phiên là căn cứ thực hiện; không hỏi lại cho các bước đã được ủy quyền.

Spec Kit là công cụ phát triển, không phải dependency của website. CLI được cài tách biệt nếu cần. Bộ tích hợp này dùng helper Python và tắt native lifecycle events; không bật auto-approve terminal, extension ngoài hoặc chạy agent headless như một bước cài đặt.

## Thực hiện và kiểm tra

- Đọc AGENTS.md và tài liệu nghiệp vụ hiện có trước khi lập kế hoạch. Dùng tiếng Việt cho spec/kế hoạch/giao tiếp người dùng; giữ ID, đường dẫn và cú pháp lệnh đúng công cụ.
- Các ví dụ helper upstream dùng python3: trên Windows thay bằng .\.venv\Scripts\python.exe; Linux/macOS dùng .venv/bin/python từ thư mục dự án. Không yêu cầu launcher py hoặc PowerShell 7 cho bộ helper Python đã chọn.
- Kiểm tra phù hợp thay đổi. Thay đổi runtime: check, migration check, collectstatic và kiểm thử nghiệp vụ liên quan; thay đổi UI: kiểm tra trình duyệt phù hợp. Không chạy email/ngân hàng thật trong kiểm thử. Thay đổi tài liệu/tooling thuần túy không cần chạy lại mọi luồng trình duyệt khi không có thay đổi runtime.
- Thêm migration phải có phương án nâng cấp/khôi phục và kiểm tra dữ liệu; không xóa database để né lỗi. Các thao tác nguy hiểm cần được xem xét theo phạm vi người dùng đã giao.
- Dùng scripts/verify_spec_kit.py để kiểm tra thư viện workflow và scripts/verify_agent_skills.py cho thư viện Agent Skills cũ.
- Cập nhật source trước, tạo manifest sau từ commit bất biến. Khi phát hành giữ nguyên ranh giới file công khai và trạng thái riêng của máy.

## Governance

Constitution này cụ thể hóa AGENTS.md và các yêu cầu đã thống nhất cho Spec Kit; yêu cầu trực tiếp của người dùng có ưu tiên khi có khác biệt. Thay đổi nguyên tắc phải ghi lý do/phạm vi, điều chỉnh spec/plan/tasks liên quan và tăng phiên bản phù hợp. Không thêm bước xin phép chỉ vì một ví dụ template có bước đó nếu công việc hiện tại đã được ủy quyền. Kết quả kiểm tra là căn cứ báo hoàn tất; không tự đánh dấu một chức năng là đã triển khai vì có file spec.

**Version**: 1.0.0 | **Ratified**: 2026-11-04 | **Last Amended**: 2026-11-04
