# Kế hoạch

1. Dùng template riêng cho các phần trang chủ; giữ hooks đặt lịch/slideshow.
2. Thêm CSS có phạm vi club, chia palette/chrome và bố cục trang chủ; không
   thêm framework, dịch vụ ảnh, font CDN hay JavaScript nghiệp vụ mới.
3. Giữ ảnh nguyên file. Biểu trưng nghề barber tự vẽ SVG, giới hạn kích thước.
4. Kiểm tra browser, đối chiếu ảnh chụp và sửa vấn đề tương phản/responsive.
5. Cập nhật hướng dẫn, commit source rồi tạo manifest từ commit bất biến.

## Phân tích trước triển khai

Không thay quyền, schema hoặc luồng thu tiền. Rủi ro chính là cascade CSS cũ,
độ tương phản trên ảnh và mất hook popup. Selector club có phạm vi; dùng nền
navy kín sau chữ, giữ selector semantic cũ ở dữ liệu dịch vụ/stylist, chạy lại
các hành trình trước đây. Ảnh tham khảo có nguồn và giới hạn quyền sử dụng tại
docs/NGUON-TAI-NGUYEN.md; không thêm dữ liệu nghiệp vụ từ ảnh.
