# Công việc

- [x] Khảo sát URL, form, JavaScript và chính sách bảo vệ hiện có; chốt tiêu chí.
- [x] Tái hiện thiếu thao tác tại chỗ bằng kiểm thử browser RED.
- [x] Triển khai dialog, menu nhanh và thanh submit cố định.
- [x] Tích hợp khởi tạo đặt lịch/báo giá và kiểm tra GET/POST, Excel/PDF.
- [x] Kiểm tra responsive, bàn phím, mạng/quyền và fallback không JavaScript.
- [x] Hoàn tất checks, suite nghiệp vụ và hướng dẫn cập nhật.
- [x] Chuẩn bị source/manifest để phát hành; đối chiếu GitHub là bước cuối sau commit/push.

## Hội tụ

14 kiểm thử trình duyệt đạt trong 55,560 giây; 212 kiểm thử Django đạt trong 98,294 giây. Có RED trước triển khai và thử đảo điều kiện nhận link trong bộ nhớ để xác nhận test bắt được lỗi. Kiểm tra trạng thái menu/form, quyền, mạng, POST chưa rõ kết quả, upload/download, báo giá, ID/focus, in, cuộn và fallback đều đạt trong phạm vi ghi nhận.

Bằng chứng và giới hạn: [Kiểm chứng](../../docs/validation/20-FORM-VA-BANG-MO-TAI-CHO.md). Trạng thái remote được xác minh riêng từ commit và manifest sau khi push.
