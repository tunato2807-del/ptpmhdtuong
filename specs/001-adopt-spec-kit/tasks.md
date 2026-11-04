# Tasks: Tích hợp GitHub Spec Kit

## Installation

- [x] T001 Đọc tài liệu hiện hành, chọn tag 1.3.0/commit ghim và kiểm tra nguồn trước khi chạy CLI.
- [x] T002 Tạo scaffold trong thư mục tạm; cài Copilot + Codex với helper Python, events false.
- [x] T003 Ghép file mới, giữ nguyên thư viện Agent Skills trước đây; viết constitution theo bất biến hiện có.
- [x] T004 Lưu provenance/hash/giấy phép và kiểm tra ngoại tuyến.

## Source Update / Documentation

- [x] T005 Viết kiểm thử RED cho file Spec Kit công khai và ranh giới credential/trạng thái máy.
- [x] T006 Mở rộng builder/updater có whitelist hẹp và giới hạn manifest; chạy GREEN.
- [x] T007 Viết hướng dẫn VS Code/Windows và cập nhật AGENTS, Copilot instructions, README.

## Verification / Release

- [x] T008 Kiểm tra helper thực tế với thư mục tạm có khoảng trắng; kiểm tra bộ skill cũ, lint/format, Django check.
- [x] T009 Hoàn thiện bằng chứng và diff, chuẩn bị phát hành theo quy trình source/manifest của AGENTS.md.

## Evidence

Kết quả kiểm tra cục bộ ngày 04/11/2026:

| Kiểm tra | Kết quả |
|---|---|
| Cài CLI từ tag/commit ghim và scaffold Copilot/Codex | CLI 1.3.0, thành công trong môi trường công cụ riêng |
| verify_spec_kit.py --smoke | 45 asset, 18 skill; create/resolve/plan/tasks/prerequisites đạt với đường dẫn tiếng Việt/có khoảng trắng |
| verify_agent_skills.py | 39 file upstream của bộ 25 skill cũ vẫn đúng SHA256 |
| Prerequisites của chính 001-adopt-spec-kit | Nhận đúng feature, spec/plan/tasks và quickstart |
| Kiểm thử updater trước sửa (RED) | 2 lỗi tái hiện: từ chối đường dẫn Spec Kit; giới hạn 400 file |
| Kiểm thử updater sau sửa (GREEN) | 7 tests đạt, gồm vận chuyển Spec Kit và giữ feature pointer/.env cục bộ |
| Ruff check / format --check salon config scripts | Đạt; 76 file đã đúng định dạng |
| manage.py check / git diff --check | Đạt |

Môi trường: Linux/Python 3.12. Không chạy lại toàn bộ 182 kiểm thử nghiệp vụ hoặc trình duyệt vì không sửa runtime/UI; không xác nhận đã chạy trực tiếp trên Windows/Python 3.14. Không gọi mô hình bên ngoài, native event handler, email hoặc thanh toán thật.

Phát hành: source được commit trước, builder kiểm tra whitelist rồi tạo manifest từ commit bất biến. Mã commit và kết quả đẩy nguồn được xác nhận trong lịch sử Git; không viết trước một mã commit chưa tồn tại vào tài liệu này.
