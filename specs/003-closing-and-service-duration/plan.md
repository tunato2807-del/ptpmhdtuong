# Kế hoạch

1. Viết kiểm thử PostgreSQL tái hiện hai lỗi trước khi sửa, cùng biên thời gian, chi nhánh, snapshot và rollback.
2. Bổ sung trạng thái đã đặt vào điều kiện chốt, dùng chung nhóm trạng thái chiếm nguồn lực và trạng thái chờ thanh toán.
3. Tính thời gian ngoài dịch vụ từ khoảng đã cấp trừ tổng snapshot hiện tại, chặn dưới ở 0. Cộng phần này vào tổng snapshot sau thay đổi, rồi chạy các kiểm tra nguồn lực hiện có trước mọi ghi dữ liệu.
4. Giữ transaction và khóa chi nhánh trước lịch; không thêm migration hay phụ thuộc runtime.
5. Chạy kiểm thử tập trung, toàn bộ suite, Django check/migration/static và lint. Ghi bằng chứng, commit source, tạo manifest từ commit đó rồi phát hành.

## Phân tích nhất quán trước triển khai

- Bộ lọc chốt giới hạn đúng chi nhánh và ngày hẹn, không dựa trên thời điểm thanh toán.
- Giá/thời lượng cũ lấy từ AppointmentItem; chỉ dịch vụ mới lấy danh mục hiện tại.
- Giữ phần thời gian cộng thêm cho cả gia hạn và check-in muộn, không làm tròn xuống mất thời gian.
- Mốc 480 phút xét toàn bộ khoảng phân bổ, không chỉ các dòng dịch vụ.
- Từ chối diễn ra trước sửa dòng dịch vụ/ghi lịch sử; kiểm thử kiểm tra dữ liệu sau lỗi.
- Dữ liệu chính thức vẫn là mục tiêu riêng trong specs/002-official-30shine-data, không đánh dấu hoàn tất bằng kiểm thử fixture.
