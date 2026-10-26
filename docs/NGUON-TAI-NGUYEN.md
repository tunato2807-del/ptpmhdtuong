# Nguồn ảnh, phông chữ và biểu tượng

## Bộ ảnh giao diện salon Việt Nam (26/10/2026)

Các ảnh đang dùng là ảnh chụp tham khảo hoạt động salon 30Shine tại Việt Nam, được lưu nguyên file trong dự án, không tạo bằng AI và không thay khuôn mặt. Nguồn/bối cảnh được xác định từ repository và nội dung website tham khảo, không suy đoán quốc tịch của từng người từ khuôn mặt. Chân trang ghi nguồn 30Shine và đồ án độc lập; ảnh không đại diện nhân viên, khách hàng hoặc chi nhánh Gentleman trong dữ liệu mẫu.

Máy chủ ảnh `storage.30shine.com` không truy cập được trong lần cập nhật này. Hai repository tham khảo công khai sau chứa các file sử dụng:

- **Nguồn A:** [AbigalChulchill/30shine_react](https://github.com/AbigalChulchill/30shine_react/tree/33379d3f04279dc38915620615a7bad135dad357/react/src/assets/img), commit `33379d3f04279dc38915620615a7bad135dad357`.
- **Nguồn B:** [Doanh-Dinh-7/30shine-web-django-reactjs](https://github.com/Doanh-Dinh-7/30shine-web-django-reactjs/tree/503e83e3b78e406f922d78e06e200007b2b73b0c/frontend/src/images), commit `503e83e3b78e406f922d78e06e200007b2b73b0c`.

| File tại `static/images/photos/` | Nguồn / đường dẫn tương đối | Kích thước gốc |
|---|---|---|
| consultation.jpg | A / langnghetantam/lang-nghe-tan-tam-1.jpg | 765 × 766 |
| salon-lounge.jpg | A / langnghetantam/lang-nghe-tan-tam-3.jpg | 700 × 700 |
| salon-interior.jpg | A / khonggianthietbi/30shinecon-cept-khong-gian-rong-lon-1.jpg | 475 × 475 |
| hair-care.jpg | A / antamtintuong/30shine-so-1-ve-an-toan-4.jpg | 1000 × 1000 |
| precision-cut.png | B / service-1.png | 369 × 468 |
| grooming.png | B / service-2.png | 361 × 215 |
| hair-wash.png | B / service-3.png | 361 × 215 |

Các file được sao chép nguyên byte, không xóa logo hoặc sửa nội dung ảnh. CSS `object-fit` điều chỉnh khung hiển thị. Một số ảnh gốc có độ phân giải nhỏ; chưa có bản gốc độ phân giải cao hơn.

**Quyền sử dụng:** các repository không cung cấp giấy phép riêng đã xác minh cho từng ảnh. README nguồn B có nhãn MIT cho dự án phần mềm, không đủ để khẳng định ảnh thương hiệu được cấp quyền MIT. Ghi nguồn không thay thế sự cho phép sử dụng; trước khi triển khai thương mại cần có quyền dùng ảnh từ chủ sở hữu hoặc thay bằng ảnh salon tự chụp. Bộ ảnh trước từ `codewithsadee/barber` đã được gỡ khỏi giao diện; các screenshot/tài liệu lịch sử có thể vẫn chứa giao diện cũ.

## Phông chữ

Người dùng cung cấp [fonttiengviet.com](https://fonttiengviet.com/) làm hướng tham khảo. Website trả 403 trong phiên truy cập, vì vậy không khẳng định đã xem được danh mục hoặc tải font từ website đó. Bộ phông có giấy phép SIL Open Font License 1.1:

| Phông | Nguồn | Vai trò | Giấy phép trong dự án |
|---|---|---|---|
| Be Vietnam Pro | `@fontsource/be-vietnam-pro@5.3.0` | Nội dung khách hàng, biểu mẫu; tiêu đề quản lý được chọn | `static/fonts/LICENSE` |
| Lora | [Google Fonts / Lora](https://github.com/google/fonts/tree/main/ofl/lora) | Chữ nghiêng nhấn trong tiêu đề, câu chào và lời nhắn cuối trang; italic 500 | `static/fonts/lora-LICENSE.txt` |
| Barlow Condensed | [Google Fonts / Barlow Condensed](https://github.com/google/fonts/tree/main/ofl/barlowcondensed) | Nhãn trang trí ngắn, số thứ tự; normal 600 | `static/fonts/barlow-condensed-LICENSE.txt` |

Be Vietnam Pro dùng các subset latin, latin-ext, vietnamese hiện có. Lora và Barlow Condensed dùng bản đầy đủ ký tự từ Google Fonts, chuyển sang WOFF2 bằng FontTools; Lora variable được cố định tại weight 500. Bản đầy đủ giữ cả dấu tổ hợp U+0302/U+0306/U+031B thường thiếu trong subset. Không cần FontTools khi chạy ứng dụng. `editorial-fonts.css` khai báo hai họ font mới; `typography.css` giới hạn vị trí áp dụng. Không dùng `* { font-family: ... }`; không đổi phông toàn bộ khu quản trị. Không yêu cầu Google Fonts, Fontsource CDN hoặc website tham khảo khi người dùng mở app.

## Biểu tượng

SVG đường nét viết trực tiếp trong template, có kích thước giới hạn. `static/images/barber.svg` là tài nguyên lịch sử không còn được dùng trên giao diện khách hàng.
