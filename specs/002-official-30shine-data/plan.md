# Plan: nguồn chính thức 30Shine

Phần đầu đã triển khai là ngừng dữ liệu tự sinh trong setup, bỏ quảng bá tài khoản mẫu và cho phép tạo người quản trị bằng thông tin chủ hệ thống nhập. Không thay đổi schema hoặc nội dung các bảng đang dùng.

Phần nhập dữ liệu chưa được thiết kế tới mức schema vì chưa đọc được nguồn chính thức. Sau khi nguồn truy cập được, kiểm kê trường công bố và điều kiện giá trước, rồi mới chọn mô hình lưu trữ. Mô hình hiện có bắt buộc thời lượng dịch vụ/giờ chi nhánh; không được tự đoán các trường này để nhét dữ liệu bên ngoài vào luồng đặt lịch.

Bản ghi công khai của 30Shine cần giữ tên thương hiệu và nguồn; lịch/ghế/nhân sự vận hành phải có xác nhận quản lý. Không mặc định có quan hệ tích hợp/đặt chỗ với 30Shine chỉ vì có dữ liệu công khai.

Kiểm tra phần chuẩn bị: RED/GREEN cho setup/login và tạo manager; Django check, migration drift, static build và bộ kiểm thử. Không xóa dữ liệu hiện có, không nhập hồ sơ khách thật, không liên hệ doanh nghiệp hoặc gửi email/thanh toán trong đợt này.
