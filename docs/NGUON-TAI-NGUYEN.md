# Nguồn ảnh và font

## Ảnh chụp barber

Nguồn trực tiếp: [codewithsadee/barber](https://github.com/codewithsadee/barber), commit `676333fc328cfcdb4988c1a4ed7d5fe2e2912387`, thư mục `assets/images/`.

README nguồn, mục License, ghi: “This project is **free to use** and does not contains any license.” Đây là tuyên bố của tác giả repository; nguồn không kèm tên nhiếp ảnh gia hoặc giấy phép riêng cho từng ảnh. Không gắn nhãn các ảnh này là MIT/Unsplash hoặc khẳng định đã xác minh quyền thương mại của từng ảnh. Bộ ảnh dùng minh họa trong đồ án; khi triển khai thương hiệu thực tế nên thay bằng ảnh cửa hàng sở hữu hoặc ảnh có giấy phép riêng đã xác minh.

| File local | File nguồn |
|---|---|
| barber-hero.webp | hero-banner.jpg |
| barber-detail.webp | pricing-bg.jpg |
| precision-cut.webp | gallery-1.jpg |
| beard-care.webp | gallery-2.jpg |
| modern-fade.webp | gallery-3.jpg |
| hair-styling.webp | gallery-4.jpg |

Ảnh là ảnh chụp, không phải ảnh được tạo bằng AI. Xử lý tài nguyên chỉ giảm kích thước và nén WebP (quality 85), không thay đổi chủ thể. Giao diện dùng object-fit để hiển thị theo khung. Ảnh không đại diện chân dung của stylist, địa điểm thực hay kết quả của một dịch vụ cụ thể trong dữ liệu demo. Thông tin này được ghi ở phần chi nhánh và cuối trang.

Không dùng hình ảnh, logo hoặc nội dung tải từ Fresha/30Shine.

## Font

Be Vietnam Pro, tác giả The Be Vietnam Pro Project Authors. Nguồn đóng gói: npm `@fontsource/be-vietnam-pro@5.3.0`. Giấy phép SIL Open Font License 1.1 được giữ nguyên tại `static/fonts/LICENSE`.

Các subset latin, latin-ext, vietnamese; các trọng lượng 400/500/600/700/800. Font tải từ file WOFF2 trong dự án; không gửi yêu cầu tới Google Fonts.

## Biểu tượng

Biểu tượng SVG đường nét được viết trực tiếp trong template; không dùng thư viện icon bên ngoài. Minh họa SVG cũ `static/images/barber.svg` được giữ lại để tương thích tài liệu lịch sử, không còn là ảnh hero khách hàng.
