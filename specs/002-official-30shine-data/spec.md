# Feature: Dữ liệu có nguồn từ website chính thức 30Shine

**Requested**: 2026-11-06

**Status**: Blocked on official-source network access; preparatory changes implemented.

## User intent

“Hãy giúp tôi thêm các dữ liệu thực tế của các web khác vào không bịa hay để demo nào hết”. Người dùng đã chọn **chỉ website chính thức 30Shine**. Không dùng Fresha, website tổng hợp, bản sao GitHub hoặc trí nhớ của mô hình làm bằng chứng cho bản ghi mới.

## Requirements / acceptance

- Thu thập tên dịch vụ, nội dung gói, giá và điều kiện áp dụng, địa chỉ salon từ trang công khai chính thức đọc được. Mỗi bản ghi có URL nguồn, ngày đối chiếu và phần nội dung làm căn cứ.
- Giữ nguyên thương hiệu/địa chỉ, điều kiện giá “từ”, chương trình và phạm vi. Không gán giá quảng cáo thành giá chung hoặc coi salon bên ngoài là chi nhánh của GENTLEMAN.
- Thông tin không công bố hoặc chưa kiểm chứng được phải để trống/chưa xác minh, không đặt giá 0, giờ mở cửa, thời lượng, ca, số ghế hoặc chuyên môn nhân sự giả để thỏa ràng buộc dữ liệu.
- Không nhập danh tính khách, lịch hẹn, hóa đơn, doanh thu hoặc tồn kho giả. Dữ liệu hoạt động này phải phát sinh từ đơn vị thực tế và đúng quyền quản lý.
- Setup không tự chạy seed_demo, kể cả còn biến môi trường LOAD_DEMO_DATA=1; trang đăng nhập không quảng bá tài khoản/mật khẩu dùng chung.
- Database mới có cách tạo tài khoản quản lý bằng thông tin chủ hệ thống nhập thực tế; không tăng quyền hoặc ghi đè hồ sơ đã có.
- Giữ lịch sử và database hiện có. Phân loại dữ liệu mẫu cũ cần có căn cứ và phương án lưu trữ; không tự xóa chứng từ hoặc bỏ nhãn “mẫu” để biến thành “thật”.

## Network evidence

Ngày 06/11/2026, yêu cầu HTTPS qua proxy của môi trường tới https://30shine.com/ bị từ chối ở CONNECT với HTTP 403. Runtime báo policy restricted/enforced và chưa có host 30Shine. Bản nháp cấu hình có sẵn 30shine.com và www.30shine.com; đã lưu lại giữ nguyên các custom host khác, công cụ xác nhận saved/requires_publish=true. Lưu draft không áp dụng policy cho runtime. Cần người dùng Review/Save và Publish môi trường trước khi đọc nguồn.

Không có bản ghi 30Shine mới được thu thập, kiểm chứng hay nhập trong phần chuẩn bị này.
