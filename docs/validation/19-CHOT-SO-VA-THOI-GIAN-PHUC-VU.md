# Kiểm chứng sửa chốt sổ và thời gian phục vụ — 12/11/2026

## Kết quả

- Chốt sổ từ chối khi chi nhánh còn lịch đã đặt, đã check-in, đang phục vụ hoặc chờ thanh toán có ngày hẹn đến ngày chốt. Lịch tương lai sau ngày chốt và lịch ở chi nhánh khác không chặn chốt.
- Sau khi chốt bị từ chối, lịch vẫn check-in, phục vụ, thu tiền và chốt lại bình thường.
- Lưu cùng danh sách dịch vụ, thêm hoặc bỏ dịch vụ đều giữ phần thời gian cộng thêm do gia hạn/check-in muộn. Dịch vụ giữ lại tiếp tục dùng snapshot giá/thời lượng cũ.
- Toàn bộ khoảng phân bổ, gồm thời gian cộng thêm, được kiểm tra giới hạn 480 phút và xung đột nguồn lực/khách. Từ chối không đổi dịch vụ, thời gian hoặc lịch sử.

## Bằng chứng thực đo

Môi trường: Python 3.12.14, Django 5.2.18, PostgreSQL 17.11. Database kiểm thử riêng; không sửa dữ liệu ứng dụng và không gửi email/thanh toán thật.

| Kiểm tra | Kết quả |
|---|---|
| RED trước sửa, 52 kiểm thử nghiệp vụ gồm 12 ca mới | 10 thất bại đúng các hành vi lỗi; 3,222 giây |
| GREEN sau sửa, cùng 52 kiểm thử | Đạt; 3,811 giây |
| Tách 12 ca mới thành `salon/tests/test_closing_and_service_duration.py` | Đạt; 1,331 giây; bộ kiểm thử cũ giữ nguyên |
| Toàn bộ suite sau khi tách file | 212/212 đạt; 99,279 giây |
| Chromium qua Playwright, database test riêng | Đạt; 4,446 giây; không có JavaScript page error |
| Django check / migration drift / collectstatic | Đạt; không cần migration mới |
| Ruff check và format cho `salon config scripts` | Đạt; 83 file Python đúng định dạng |
| Thư viện Agent Skills / Spec Kit smoke | Agent Skills: 39 file; Spec Kit: 45 file được xác minh; helper chạy trong đường dẫn Unicode/có khoảng trắng |

Kiểm thử Chromium bấm form chốt sổ ở viewport 1365×900, nhận thông báo lịch chưa xử lý và xác nhận không tạo bản chốt. Sau đó check-in/bắt đầu/gia hạn 30 phút, bấm lưu cùng dịch vụ ở viewport 390×844, xác nhận chuyển về chi tiết lịch và giờ kết thúc không bị rút ngắn.

Thử đảo điều kiện giới hạn từ `> 480` thành `>= 480` trong bộ nhớ tiến trình kiểm thử: ca chấp nhận đúng 8 giờ thất bại như dự kiến. File nguồn không bị sửa bởi thử nghiệm này. Đây là bằng chứng kiểm thử nhận ra lỗi ở biên, không phải lỗi còn tồn tại của bản phát hành.

## Rà soát và giới hạn

Rà soát diff về tính đúng, khả năng đọc, kiến trúc, quyền và chi phí truy vấn: giữ transaction/khóa chi nhánh trước lịch, kiểm tra quyền sau khóa và kiểm tra xung đột trước khi ghi; không thêm dependency, truy vấn dữ liệu cá nhân hay vòng lặp truy vấn mới. Tính thời gian cộng thêm từ các snapshot đã đọc.

Không tự mở lại sổ cũ, sửa chứng từ hoặc suy đoán thời gian gia hạn đã bị mất bởi các lần lưu trước đây. Không phải bằng chứng nghiệm thu toàn bộ hoạt động salon thực tế, gửi SMTP thật hoặc chạy trên Python 3.14. Dữ liệu 30Shine chưa được nhập trong bản sửa này; mục tiêu nguồn thật trong `specs/002-official-30shine-data/` vẫn chưa hoàn tất.

Chi tiết quy tắc và cách vận hành: [Nghiệp vụ nhiều chi nhánh](../13-NGHIEP-VU-NHIEU-CHI-NHANH.md); đặc tả: [Sửa chốt sổ và thời gian phục vụ](../../specs/003-closing-and-service-duration/spec.md).
