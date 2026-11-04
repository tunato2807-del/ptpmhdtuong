# Implementation Plan: Tích hợp Spec Kit

**Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

## Summary

Tạo scaffold bằng Specify CLI 1.3.0 trong thư mục tạm, sau đó ghép các file mới vào repository. Tích hợp Copilot và Codex, dùng script Python và tắt native events. Giữ thư viện Agent Skills cũ; thêm constitution, hồ sơ nguồn và hướng dẫn riêng. Mở rộng whitelist updater có kiểm thử cho file công khai, giữ trạng thái máy/credential ở ngoài.

## Technical Context

**Language/Version**: Python 3.12–3.14 của dự án; CLI 1.3.0 yêu cầu Python >=3.11.

**Dependencies**: Specify CLI trong môi trường công cụ riêng; helper được cài dùng thư viện chuẩn.

**Storage**: File Markdown/JSON; không có thay đổi PostgreSQL hoặc migration.

**Testing**: kiểm tra nguồn/hash, helper trong thư mục tạm, Django SimpleTestCase cho updater, check/lint.

**Platform**: Windows PowerShell trong VS Code; kiểm tra trực tiếp trên Linux/Python 3.12.

**Scope**: 9 skill/integration × 2 integration; một bộ template/helper dùng chung.

## Constitution Check

- Quyền chi nhánh, lịch và ledger: ghi rõ nguyên tắc; không sửa runtime.
- Bảo vệ dữ liệu: updater không nhận credential/feature pointer, công cụ kiểm tra không đọc .env.
- Kiểm thử vừa phạm vi: kiểm tra CLI/helper/updater; không chạy lại toàn bộ luồng thanh toán/UI cho thay đổi tooling này.
- Ủy quyền: tích hợp và phát hành mã theo yêu cầu đang có; không chạy agent bên ngoài hay lifecycle hook.

## Project Structure

- .specify/: constitution, template, helper, cấu hình integration, giấy phép và nguồn.
- .github/skills/speckit-*/: 9 skill Copilot.
- .agents/skills/speckit-*/: 9 skill Codex; skill cũ được giữ lại.
- specs/001-adopt-spec-kit/: hồ sơ chính thay đổi này.
- scripts/verify_spec_kit.py: kiểm tra ngoại tuyến.
- scripts/cap_nhat_du_an.py, build_update_manifest.py: vận chuyển đủ file công khai.
- docs/16-SPEC-KIT.md: hướng dẫn Windows và lệnh chat.

## Decisions / Alternatives

Dùng bản phát hành 1.3.0 tại commit 34a0d388eac671d656eb05b125ad3ed6056168ed thay vì nhánh main đang phát triển. Không đưa toàn bộ mã CLI vào ứng dụng; chỉ cài scaffold upstream có nguồn rõ ràng. Dùng helper Python để Windows không phụ thuộc Bash hay PowerShell 7. Không chạy init --here --force trực tiếp trên bản người dùng đang chỉnh; giữ khả năng xem xét diff trước khi nâng cấp.

## Validation / Delivery

Ghi lệnh/kết quả tại tasks.md và docs/16-SPEC-KIT.md. Commit source trước; tạo update_manifest.json từ source commit; commit manifest và đẩy GitHub theo quy trình hiện có. Không ghi địa chỉ thư mục tạm hoặc credential vào hồ sơ phát hành.
