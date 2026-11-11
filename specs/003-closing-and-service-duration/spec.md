# Sửa chốt sổ và bảo toàn thời gian phục vụ

## Phạm vi

Sửa hai lỗi đã tái hiện trong rà soát nghiệp vụ: chốt sổ bỏ sót lịch đã đặt và lưu dịch vụ làm mất thời gian gia hạn. Giữ quyền theo chi nhánh, thứ tự khóa, snapshot và lịch sử hiện có. Không thay đổi schema, chứng từ hoặc dữ liệu ứng dụng.

## Quy tắc và nghiệm thu

1. Quản lý chỉ chốt ngày khi chi nhánh không còn lịch đã đặt, đã check-in, đang phục vụ hoặc chờ thanh toán có ngày hẹn nhỏ hơn hoặc bằng ngày chốt. Từ chối phải giữ ngày mở và cho phép tiếp tục xử lý lịch.
2. Lịch tương lai sau ngày chốt, lịch ở chi nhánh khác và lịch kết thúc (đã hủy, không đến, đã thanh toán) không chặn chốt.
3. Khi đổi dịch vụ trước khi hoàn tất phục vụ, giữ thời gian ngoài tổng thời lượng snapshot đã cấp cho lịch (gia hạn hoặc khách đến muộn). Chỉ cộng/trừ thời lượng của dịch vụ được thêm/bỏ; không cập nhật snapshot của dịch vụ giữ lại theo danh mục mới.
4. Tổng thời gian sau sửa không quá 480 phút, vẫn phải nằm trong giờ mở cửa/ca và không trùng stylist, khách hoặc sức chứa ghế. Nếu không hợp lệ, giữ nguyên lịch, dịch vụ và lịch sử.
5. Thông báo chốt sổ giải thích cách xử lý lịch còn tồn; không tự hủy, đánh dấu không đến hoặc kết thúc lịch để ép chốt.

## Ngoài phạm vi

Mở lại sổ đã chốt, sửa lịch sử tài chính và nhập dữ liệu 30Shine. Việc có đủ số bản ghi thật vẫn phụ thuộc nguồn chính thức và dữ liệu vận hành của đơn vị; không tạo dữ liệu để đủ số.
