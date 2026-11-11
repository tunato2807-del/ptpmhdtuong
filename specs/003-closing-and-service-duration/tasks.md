# Công việc

- [x] Đặc tả phạm vi và phân tích các bất biến trước sửa.
- [x] Tái hiện lỗi bằng kiểm thử RED trên PostgreSQL riêng.
- [x] Sửa chốt sổ và thời gian dịch vụ; kiểm thử GREEN.
- [x] Kiểm tra đường đi HTTP và luồng xử lý tiếp sau khi chốt bị từ chối.
- [x] Chạy toàn bộ kiểm thử và kiểm tra dự án, ghi kết quả thực đo.
- [x] Chuẩn bị mã nguồn và hướng dẫn phát hành source trước, manifest bất biến sau; xác minh GitHub ở bước kết thúc.

## Bằng chứng hội tụ

12 ca hồi quy có RED trước sửa và GREEN sau sửa; tách thành module riêng để giữ bộ kiểm thử cũ nguyên vẹn. Toàn bộ 212 kiểm thử đạt trong 99,279 giây. Chromium kiểm tra form chốt và lưu dịch vụ trên desktop/mobile đạt. Đảo điều kiện biên 480 phút bị kiểm thử phát hiện. Check/migration/static, Ruff và kiểm tra tính toàn vẹn các thư viện workflow đều đạt.

Chi tiết: [Bằng chứng kiểm tra](../../docs/validation/19-CHOT-SO-VA-THOI-GIAN-PHUC-VU.md). Trạng thái phát hành được đối chiếu bằng commit trên GitHub và manifest tải từ remote sau khi push, không suy từ dấu hoàn thành công việc trong file này.

## Giới hạn

Không suy rằng toàn bộ nghiệp vụ thực tế đã được nghiệm thu chỉ từ hai bản sửa này. Không thay đổi dữ liệu ứng dụng hoặc chứng từ cũ.
