# Áp dụng Agent Skills vào GENTLEMAN

## 1. Nguồn và cách dùng trong VS Code

Đã tích hợp đầy đủ 25 skill của [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/aeac41d4d005999432bb7312f7ff06383a91d59d), cố định ở commit `aeac41d4d005999432bb7312f7ff06383a91d59d`. Bản sao có giấy phép MIT, mã kiểm tra SHA256 và các tài liệu tham chiếu đi kèm. Đây là hướng dẫn cho công cụ lập trình; website chạy bằng Django như trước, không cần cài một ứng dụng AI để khách đặt lịch.

- `AGENTS.md`: bối cảnh riêng của dự án, lệnh chạy, phân quyền chi nhánh và quy tắc giữ dữ liệu.
- `.github/copilot-instructions.md`: hướng dẫn cho Copilot trong VS Code.
- `.agents/skills/<tên>/SKILL.md`: quy trình chi tiết, đọc khi công việc cần tới.
- `.agents/references/`: checklist hỗ trợ; `.agents/agent-skills-source.json` ghi nguồn và mã kiểm tra.
- `docs/quality/spec.md`, `plan.md`: phạm vi và sổ theo dõi lượt rà soát này.

Ví dụ yêu cầu trong VS Code: “Đọc AGENTS.md, dùng test-driven-development và security-and-hardening để sửa chức năng đổi lịch; tái hiện lỗi trước khi sửa, kiểm tra đúng phạm vi chi nhánh”. Khả năng tự nhận tên `$skill` tùy tiện ích; luôn có thể yêu cầu đọc trực tiếp đường dẫn `SKILL.md`. Không cần nạp toàn bộ 25 tài liệu vào mỗi lần làm việc.

## 2. Những thay đổi thực tế

### Tài khoản và phân quyền

Email nhận liên kết khôi phục là một phần của danh tính đăng nhập. Lễ tân/quản lý chi nhánh không được thay email của khách đã có mật khẩu, đã có email hoặc có hồ sơ tại chi nhánh khác. Chi nhánh chỉ có thể điền email lần đầu cho khách tại quầy chưa kích hoạt, chưa có email và chỉ có lịch ở chi nhánh đó; vẫn phải xác minh và đánh dấu khách đồng ý. Chủ tài khoản cập nhật liên hệ ở hồ sơ cá nhân; quản trị chuỗi có quyền quản lý tài khoản toàn chuỗi.

Đặt lại mật khẩu khóa và đọc lại tài khoản, kiểm tra lại token và trạng thái hoạt động, sau đó chỉ ghi cột mật khẩu. Thao tác này không ghi đè vai trò, điểm hay thông tin vừa được cập nhật bởi giao dịch khác. Thao tác quản trị chuỗi, tiếp nhận tại quầy và stylist đều kiểm tra lại quyền/phân công sau khi chờ khóa.

Đăng nhập giới hạn 10 lần/15 phút theo IP và tên đăng nhập đã chuẩn hóa khoảng trắng; các biểu mẫu tạo/khôi phục/kích hoạt tài khoản có giới hạn riêng và giới hạn chung 100 yêu cầu xác thực/IP/15 phút. Bộ đếm dùng PostgreSQL nên được chia sẻ giữa các tiến trình, không tin `X-Forwarded-For` tự gửi từ trình duyệt. Khi chạy qua proxy, cấu hình địa chỉ khách ở tầng máy chủ; không bật tin mọi header chuyển tiếp. Yêu cầu email khôi phục cùng địa chỉ có thời gian chờ 60 giây và phản hồi chung cho địa chỉ có/không tồn tại.

### Hoàn tiền và điểm

Ví dụ hóa đơn A tích 10 điểm, hóa đơn B dùng 10 điểm: hoàn A rồi B hay B rồi A đều về cùng số dư/điểm cần thu hồi. Điểm được trả lại sẽ bù phần cần thu hồi trước khi trở thành điểm có thể dùng. Phiếu hoàn ghi riêng điểm cần thu hồi phát sinh và điểm đã đối trừ; sổ điểm giữ biến động thực tế.

Migration `0008` bổ sung trường/ràng buộc; `0009` đối trừ hồ sơ cũ đang đồng thời có điểm khả dụng và điểm cần thu hồi, kèm một bút toán `debt_recovery`. Giá trị ròng được giữ nguyên, không viết lại hóa đơn hoặc bút toán cũ. Chạy lại không cộng/trừ lần hai khi số dư đã chuẩn hóa. `0010` tạo bộ đếm xác thực. Không hoàn tác dữ liệu tài chính bằng cách xóa lịch sử.

### Truy vấn, giao diện và quan sát lỗi

| Trang / dữ liệu kiểm tra | Trước | Sau |
|---|---:|---:|
| Điều hành 12 chi nhánh | 101 truy vấn | 11 truy vấn |
| Danh sách 12 stylist | 16 | 4 |
| Lịch làm việc 12 stylist | 28 | 6 |
| Chi tiết có 30 lần xử lý | 37 | 7 |

Các tổng hợp đọc riêng theo nhóm, tránh nhân số tiền khi ghép nhiều bảng. Lịch sử xử lý có phân trang 20 dòng, tải kèm người thao tác. Không thêm cache vào quyết định sức chứa, quyền hay số dư.

Màu chữ phụ, nút và nhãn được chỉnh theo kết quả đo tương phản. Bảng cuộn có thể nhận focus bằng bàn phím. Font trang trí vẫn giới hạn theo thành phần. Menu điện thoại có trạng thái ban đầu ổn định và phương án khi tắt JavaScript; trình chiếu ưu tiên ảnh đầu, nạp ảnh phụ sau khi trang tải xong, giữ nút dừng/chuyển tay và chế độ giảm chuyển động.

Response có CSP (script chỉ từ cùng nguồn), chống nhúng iframe, giới hạn quyền camera/micro và mã yêu cầu `X-Request-ID`. Trang động dùng `private, no-store`. Nhật ký JSON chứa mã yêu cầu, route mẫu, phương thức, trạng thái và thời gian; không ghi tham số URL, token reset, nội dung form, cookie hoặc thông tin liên hệ. Log lỗi framework chỉ ghi loại lỗi/trạng thái, không ghi thông điệp có thể chứa dữ liệu SQL. Chưa nối dịch vụ telemetry bên ngoài.

## 3. Skill nào đã áp dụng

| Skill / nhóm | Cách áp dụng trong lượt này |
|---|---|
| `using-agent-skills`, `context-engineering` | Định tuyến theo việc, AGENTS riêng, nguồn cố định, không tải tất cả vào ngữ cảnh |
| `spec-driven-development`, `constraint-driven-development`, `planning-and-task-breakdown` | Spec/phạm vi/tiêu chí và kế hoạch; giữ Django/PostgreSQL, Windows, dữ liệu, font cục bộ |
| `incremental-implementation`, `test-driven-development`, `debugging-and-error-recovery` | Tái hiện lỗi RED, sửa nhỏ, chạy GREEN; kiểm tra lỗi nghiệp vụ và giao dịch đồng thời |
| `source-driven-development` | Đọc mã và API Django đang cài; lưu nguồn upstream/SHA256, không coi hướng dẫn ngoài là quyền thao tác hệ thống |
| `doubt-driven-development`, `code-review-and-quality` | Hai lượt rà soát độc lập theo bối cảnh tách biệt; đối chiếu bằng kiểm tra, thử bỏ điều kiện để chứng minh test bắt được lỗi |
| `security-and-hardening`, `api-and-interface-design` | Khôi phục tài khoản, phạm vi chi nhánh, POST/CSRF, giới hạn xác thực, header và hợp đồng dữ liệu hiện có |
| `performance-optimization`, `code-simplification` | Đo truy vấn trước/sau; gom đọc theo nhóm, bỏ truy vấn trong vòng lặp; không tách lớp hình thức |
| `frontend-ui-engineering`, `browser-testing-with-devtools` | Kiểm tra trình duyệt, bàn phím/tương phản/reduced motion và menu/ảnh; dùng Playwright + Chromium CDP vì không có Chrome DevTools MCP trong phiên |
| `ci-cd-and-automation`, `git-workflow-and-versioning` | Lint/format, audit dependencies, PostgreSQL tests, kiểm tra trình duyệt trong workflow; updater khóa theo commit |
| `documentation-and-adrs`, `observability-and-instrumentation` | Cập nhật hướng dẫn, báo cáo, từ điển dữ liệu; request ID và nhật ký an toàn, runbook |
| `interview-me`, `idea-refine` | Có sẵn cho yêu cầu mới; không tổ chức lại phỏng vấn vì phạm vi dự án đã được xác nhận |
| `deprecation-and-migration` | Nâng cấp tương thích qua migration, giữ lịch sử; không loại bỏ API/tính năng đang dùng |
| `shipping-and-launch` | Kiểm tra build/cập nhật mã và hướng dẫn vận hành; không thực hiện triển khai công khai hoặc tự gửi email thật |

Người dùng đã chọn tiếp tục với hai lượt rà soát hiện có, không bổ sung một lượt chạy bằng mô hình/CLI ngoài. Hai người rà soát thuộc cùng họ mô hình; đây không phải đánh giá bởi hai nhà cung cấp mô hình khác nhau. Việc cài đủ thư viện không có nghĩa mọi quy trình đều đã chạy đầy đủ hoặc hệ thống đã đạt chứng nhận bảo mật.

## 4. Cập nhật trên máy Windows hiện có

Dừng server đang chạy trong VS Code. Cập nhật các file từ GitHub bằng công cụ cập nhật mã đang có (hoặc copy từng file), giữ `.env`, `.venv`, `.local` và database. Bản updater mới mang theo các file ẩn `.agents`, `.github`, AGENTS và cấu hình kiểm tra; bản updater cũ nên được thay bằng bản mới trước.

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip==26.2
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py backup_database
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

Nếu sao lưu chưa tìm thấy `pg_dump`, thêm vào `.env` đúng thư mục PostgreSQL đã xác định trên máy bạn:

```dotenv
POSTGRES_BIN=D:/LTGISMAIN/PostgreSQL/18/bin
```

Mở `http://127.0.0.1:8000/`, nhấn Ctrl+F5 để nhận CSS/JS mới. Không cần Docker. Chỉ cài `requirements-quality.txt` khi muốn chạy bộ kiểm tra lập trình; Node/npm và axe chỉ dùng để kiểm tra trình duyệt, không cần cho việc chạy website thông thường.

## 5. Kiểm tra và giới hạn bằng chứng

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-quality.txt
.\.venv\Scripts\python.exe -m ruff check salon config scripts
.\.venv\Scripts\python.exe -m ruff format --check salon config scripts
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
.\.venv\Scripts\python.exe scripts/verify_agent_skills.py
.\.venv\Scripts\python.exe scripts/dev.py check
```

Để chạy kiểm tra truy cập trình duyệt: `npm ci --ignore-scripts --prefix scripts/browser-audit`, cài Chromium bằng Playwright, mở server local rồi chạy `python scripts/quality_browser.py`. Công cụ dùng tài khoản/session kiểm thử riêng, chỉ kết nối localhost, tự dọn dữ liệu mình tạo. Kết quả chỉ lưu route, selector và số đo; không lưu HTML có thông tin khách.

Xem bằng chứng cuối cùng trong `docs/validation/14-AGENT-SKILLS.txt` và các file JSON đi kèm. Đã chạy 179 test PostgreSQL và đối chiếu toàn bộ trường/dòng cũ trong 27 bảng cũ có tiền tố salon_ (gồm cả bảng nối phân quyền) với bản sao lưu đã phục hồi riêng (chỉ bỏ qua last_login do đăng nhập kiểm thử). Đã kiểm tra thực tế trên Python 3.12/PostgreSQL native. CI có cấu hình thêm Python 3.14; chỉ coi job GitHub Actions đạt khi đã xem kết quả chạy đó. Số đo LCP/CLS là phòng thử nghiệm CDP, không phải dữ liệu người dùng thật hoặc INP. Quét axe chỉ bao phủ các route/trạng thái đã ghi, không thay thế kiểm tra thủ công toàn bộ khả năng truy cập. Audit dependency chỉ phát hiện lỗ hổng đã công bố.

## 6. Vận hành khi cần tìm lỗi

Ba câu hỏi nhật ký trả lời: route nào trả lỗi, mã yêu cầu nào cần tra, và thời gian xử lý có tăng không. Khi gặp lỗi, giữ `X-Request-ID` ở Network trong trình duyệt rồi tìm cùng mã trong terminal/log server; không dán password, cookie hay URL đặt lại mật khẩu. Nếu lỗi database, kiểm tra `manage.py check_database`; nếu lỗi sau nâng cấp, kiểm tra migration và static trước. Hóa đơn/hoàn tiền cần đối chiếu sổ, không thử gửi lại thanh toán liên tục.

Bộ đếm chỉ lưu HMAC và số lần/thời hạn; tự dọn tối đa 200 mục hết hạn khi tạo khóa mới. Có thể lên lịch hằng ngày `manage.py prune_auth_limits` để dọn hết mục hết hạn khi ít truy cập. Lệnh này không xóa tài khoản hoặc dữ liệu nghiệp vụ. Log xuất stdout; nếu lưu file, người vận hành đặt rotation/retention phù hợp. Email demo vẫn lưu ở `.local/emails`; không công khai thư mục này, dọn thư thử nghiệm và bảo quản bản sao lưu như dữ liệu riêng tư. Chứng từ tài chính vẫn được bảo toàn; lượt cập nhật này không tự xóa/anonymize hồ sơ khách hoặc đặt chính sách lưu chứng từ thay chủ hệ thống.
