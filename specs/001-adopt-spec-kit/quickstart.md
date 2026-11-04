# Quickstart

Xem [hướng dẫn tiếng Việt đầy đủ](../../docs/16-SPEC-KIT.md). Trong Copilot Chat mở tại repository:

```text
/speckit-specify Bổ sung danh sách chờ theo từng chi nhánh khi không có giờ trống. Không tự tạo hoặc hủy lịch khách.
```

Đây là ví dụ tính năng tương lai, chưa được triển khai. Đọc kết quả trước khi chuyển bước plan/tasks/implement. Cùng yêu cầu trong Codex dùng $speckit-specify. Các lệnh này ở ô chat; lệnh kiểm tra Python và cập nhật chạy trong terminal.

Kiểm tra hồ sơ tích hợp mẫu bằng PowerShell (chọn feature tường minh, không phụ thuộc tên branch Git):

```powershell
$env:SPECIFY_FEATURE_DIRECTORY = "specs/001-adopt-spec-kit"
.\.venv\Scripts\python.exe .specify\scripts\python\check_prerequisites.py --json --require-spec --require-tasks --include-tasks
Remove-Item Env:SPECIFY_FEATURE_DIRECTORY
```

.specify/feature.json là con trỏ riêng của checkout, không nằm trong bản phát hành.
