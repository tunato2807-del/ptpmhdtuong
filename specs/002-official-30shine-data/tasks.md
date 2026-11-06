# Tasks

## Preparatory work

- [x] Xác định duy nhất nguồn 30Shine theo câu trả lời của người dùng.
- [x] Kiểm tra chính sách và lỗi truy cập thực tế; lưu draft giữ các miền đã có, xác định requires_publish.
- [x] Tái hiện việc setup tự seed và trang đăng nhập lộ tài khoản dùng chung bằng kiểm thử RED.
- [x] Ngừng auto-seed và bỏ khối tài khoản trình diễn khỏi trang đăng nhập; giữ dữ liệu cũ.
- [x] Thêm create_manager để chủ hệ thống nhập danh tính/mật khẩu; kiểm thử không tăng quyền tài khoản cũ và không nhận mật khẩu yếu.
- [x] Hoàn thành kiểm tra và chuẩn bị phát hành phần chuẩn bị.

## Official data — pending access, not complete

- [ ] Runtime áp dụng allowlist tới website 30Shine sau Review/Save/Publish.
- [ ] Đọc trang chính thức, ghi lại căn cứ và xác định các trường thật sự được công bố.
- [ ] Hoàn thiện phương án lưu provenance và phân biệt danh mục tham khảo với nguồn lực được quản lý/cho đặt lịch.
- [ ] Chuẩn bị bộ dữ liệu chỉ gồm thông tin có căn cứ; đối chiếu từng giá, điều kiện, địa chỉ.
- [ ] Thêm nhập dữ liệu idempotent và kiểm thử; thông tin thiếu không được tự điền giả.
- [ ] Chuyển dữ liệu mẫu cũ ra khỏi phần sử dụng thực tế theo phương án bảo toàn lịch sử, sau khi đã nhận diện được nguồn gốc.
- [ ] Xác minh giao diện/danh sách/đặt lịch và phát hành bộ dữ liệu thật.

Không đánh dấu phần thu thập/nhập là hoàn tất khi nguồn còn bị chặn. Không dùng bản sao website hoặc proxy khác để vượt chính sách mạng.

## Validation of preparatory changes

- 5 kiểm thử mới: RED xác nhận auto-seed, quảng bá tài khoản chung và thiếu bootstrap manager; GREEN sau sửa.
- Toàn bộ 189 kiểm thử Django đạt trên PostgreSQL thực trong 97,296 giây; database test riêng được dọn sau khi chạy.
- Django check, migration drift, collectstatic và Ruff check/format đạt. Không thêm migration.
- Không nhập/đổi/xóa dữ liệu trong database ứng dụng. Kết quả kiểm thử không phải xác minh dữ liệu 30Shine.
- Chính sách runtime được kiểm tra lại sau phần chuẩn bị, vẫn chưa cho phép host 30Shine. Nguồn và dữ liệu chính thức vẫn đang chờ.

## Tools for the 100-record target

- [x] Thêm audit_data_targets cho 26 bảng, chỉ đọc và không suy số thật từ tổng số dòng.
- [x] Thêm collector chính thức dùng được từ Windows, giới hạn 100 mục/nhóm, lưu source/hash/thời điểm và báo thiếu thay vì đệm số.
- [x] Kiểm thử chặn tên miền ngoài, robots, không đọc người/review, thiếu nguồn, giữ giá và loại trùng/quota.
- [ ] Thu thập và xác minh 100 bản ghi thật cho các bảng có nguồn công khai; chưa hoàn thành vì nguồn cloud vẫn bị chặn.
- [ ] Nhận dữ liệu thật của đơn vị cho các bảng không có nguồn công khai; không tạo khách/lịch/chứng từ để đủ số.

Collector đã được thử với nguồn thực: 0/100 ở cả ba nhóm, errors=1, không ghi database. Kết quả kiểm thử fixture không được mô tả là 100 bản ghi thật đã có.

Validation for tooling: full suite 200 tests passed in 101.615s on PostgreSQL; 11 new parser/collector/count tests. Check/migration drift/static build/Ruff passed. The 26-table audit was executed read-only. Live collector reported zero, exit 2, source unavailable; no operational rows were created. Source collection/import goals above remain incomplete.
