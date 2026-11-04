# Feature Specification: Tích hợp GitHub Spec Kit

**Feature Directory**: specs/001-adopt-spec-kit  
**Created**: 2026-11-04  
**Status**: Implemented; local verification recorded in tasks.md  
**Input**: “Hãy bổ sung vào dự án của tôi https://github.com/github/spec-kit”.

## User Scenarios & Testing

### User Story 1 — Dùng Spec Kit trong VS Code (Priority: P1)

Người phát triển mở dự án hiện có và gọi bộ lệnh Spec Kit trong Copilot Chat để viết đặc tả, kế hoạch, công việc và thực hiện một thay đổi. Codex dùng cùng các tài liệu, với skill tương ứng của Codex.

**Independent Test**: Có đủ 9 skill ở mỗi integration; resolver đọc được template; helper xác định đúng thư mục đặc tả/kế hoạch/công việc mà không gọi mô hình bên ngoài.

**Acceptance Scenarios**:
1. Trong Copilot Chat, bộ skill có tên speckit-specify, speckit-plan và các bước liên quan; tài liệu phân biệt lệnh chat và terminal.
2. Trong Codex, cùng quy trình có thể gọi bằng $speckit-specify; không cần ghi lại quy tắc kinh doanh vào một hệ thứ hai.
3. Trên Windows, hướng dẫn dùng interpreter .venv trực tiếp và không yêu cầu py/Python launcher.

### User Story 2 — Giữ nguyên dự án đang có (Priority: P1)

Người phát triển dùng Spec Kit cùng 25 Agent Skills trước đây. Nguyên tắc của GENTLEMAN được chuyển thành constitution để kế hoạch mới bảo vệ quyền, lịch và giao dịch.

**Independent Test**: Kiểm tra SHA256 thư viện cũ; không đổi dependency runtime, schema hoặc template của website; constitution bao phủ các bất biến trong AGENTS.md.

### User Story 3 — Cập nhật đủ file bằng terminal (Priority: P1)

Người dùng chạy công cụ đồng bộ mã hiện có để nhận cả .specify, skill Copilot/Codex và specs.

**Independent Test**: Manifest chấp nhận file công khai của Spec Kit và sao lưu/thay file đúng; từ chối .env, cấu hình xác thực, gói adapter tự thực thi và con trỏ tính năng riêng của máy.

## Requirements

- **FR-001**: Cố định phiên bản upstream, ghi commit, giấy phép MIT và hash các tài nguyên đã cài.
- **FR-002**: Cài đủ 9 lệnh SDD cho Copilot và Codex; dùng helper Python, native events tắt.
- **FR-003**: Có constitution dự án, tôn trọng AGENTS.md và phạm vi ủy quyền trong phiên.
- **FR-004**: Có hướng dẫn tiếng Việt cho quy trình specify/plan/tasks/analyze/implement/converge; có mẫu lời nhắc cho công việc mới.
- **FR-005**: CLI là công cụ riêng, không thêm vào requirements chạy web.
- **FR-006**: Công cụ cập nhật chuyển đủ file công khai và vẫn bảo vệ cấu hình/dữ liệu riêng; có kiểm thử hồi quy cho ranh giới này.
- **FR-007**: Có kiểm tra toàn vẹn và kiểm tra helper ngoại tuyến trong môi trường/thư mục thử riêng.

## Edge Cases

- VS Code chưa nhận skill sau đồng bộ: reload window; kiểm tra phiên bản Copilot có hỗ trợ Agent Skills; không gõ /speckit-* trong PowerShell.
- Máy không có python3/py: dùng .venv interpreter cụ thể như hướng dẫn.
- Chưa có feature pointer hoặc pointer từ checkout khác: chọn SPECIFY_FEATURE_DIRECTORY tường minh; không phát hành .specify/feature.json.
- Gặp file cục bộ có nội dung riêng: updater giữ bản sao lưu; việc nâng cấp Spec Kit cần xem diff và không ép ghi đè constitution.
- Cài thêm extension/agent có thư mục dùng chung: rà soát riêng, không coi việc có trong catalog là đã được kiểm chứng.

## Success Criteria

- **SC-001**: Kiểm tra toàn vẹn xác nhận 18 skill và các file nguồn được ghim.
- **SC-002**: Tạo feature → phân giải template → chuẩn bị plan/tasks → kiểm tra prerequisites thành công trong thư mục tạm với đường dẫn có khoảng trắng, không gọi dịch vụ AI.
- **SC-003**: Kiểm thử cập nhật công khai/riêng tư đạt và kiểm tra cấu hình Django không báo lỗi.
- **SC-004**: Có lệnh cập nhật Windows, vị trí file và ví dụ chat dễ dùng; không cần cài lại dự án.

## Scope / Assumptions

Đây là tích hợp quy trình phát triển; không tự thêm tính năng nghiệp vụ, thay giao diện, chạy thanh toán/email hoặc viết lại toàn bộ đặc tả cũ. Copilot là mặc định vì người dùng làm việc trong VS Code; Codex được cài song song tại thư mục skill riêng. Bản hướng dẫn không xác nhận các lệnh chat đã chạy trên tài khoản/tiện ích VS Code của người dùng.
