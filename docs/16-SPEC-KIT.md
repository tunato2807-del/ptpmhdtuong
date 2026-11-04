# GitHub Spec Kit trong GENTLEMAN

Đã tích hợp [github/spec-kit](https://github.com/github/spec-kit) bản **v1.3.0**, commit `34a0d388eac671d656eb05b125ad3ed6056168ed`, giấy phép MIT. Đây là bộ quy trình giúp công cụ lập trình viết đặc tả, lập kế hoạch và triển khai theo yêu cầu. Việc thêm Spec Kit không tự sinh thêm tính năng hoặc làm đổi giao diện website.

## Đã cài những gì

| Vị trí | Mục đích |
|---|---|
| `.specify/memory/constitution.md` | Nguyên tắc riêng của dự án: chi nhánh, đặt lịch, chứng từ, bảo mật, giao diện và kiểm thử |
| `.specify/templates/` | Mẫu spec, plan, tasks, checklist, constitution |
| `.specify/scripts/python/` | Helper tạo feature, chuẩn bị plan/tasks, kiểm tra đầu vào và phân giải template; dùng trên Windows/Linux |
| `.github/skills/speckit-*/SKILL.md` | 9 skill cho Copilot Chat trong VS Code |
| `.agents/skills/speckit-*/SKILL.md` | 9 skill tương ứng cho Codex; giữ nguyên 25 skill đã có |
| `.specify/integration.json` | Copilot mặc định, Codex cài song song, helper Python, native events tắt |
| `.specify/workflows/speckit/` | Định nghĩa workflow đi kèm upstream; chỉ là file, không tự chạy |
| `.specify/LICENSE`, `.specify/source.json` | Giấy phép, phiên bản, commit, nguồn tạo và SHA256 của 45 tài nguyên scaffold |
| `specs/001-adopt-spec-kit/` | Đặc tả/kế hoạch/công việc của lần tích hợp này; không phải đặc tả dựng lại toàn bộ phần mềm |
| `scripts/verify_spec_kit.py` | Kiểm tra toàn vẹn và chạy thử helper ngoại tuyến |

Thư viện được tạo bằng Specify CLI trong thư mục tạm rồi ghép các đường dẫn mới vào dự án. Không thêm dependency vào `requirements.txt`, không đổi schema hay dữ liệu PostgreSQL. Native lifecycle events được tắt; không thêm cấu hình auto-approve terminal, gọi agent headless hoặc cài extension bên ngoài trong lần này.

## Cập nhật vào VS Code của bạn

Dừng server bằng Ctrl+C. Mở PowerShell tại thư mục chứa `manage.py`. **Lần đầu nhận Spec Kit, lấy công cụ cập nhật mới trước**, vì công cụ cũ chưa nhận các đường dẫn `.specify`, `.github/skills` và `specs`:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tunato2807-del/ptpmhdtuong/main/scripts/cap_nhat_du_an.py" -OutFile "$env:TEMP\gentleman-update.py"
.\.venv\Scripts\python.exe "$env:TEMP\gentleman-update.py" --project .
.\.venv\Scripts\python.exe scripts\verify_spec_kit.py --smoke
.\.venv\Scripts\python.exe manage.py check
```

Chạy từng lệnh, xử lý nếu một bước lỗi rồi mới tiếp tục. Updater tải nguồn từ một commit cố định, xác minh SHA256 và giữ bản sao lưu ở `.local/cap-nhat-.../sao-luu`; `.env`, `.venv`, database và con trỏ tính năng riêng của máy được giữ lại. Lần sau có thể dùng `scripts\cap_nhat_du_an.py` đã cập nhật. Bản tích hợp này không cần migration, cài thêm thư viện chạy web hoặc tải lại toàn bộ dự án.

Trong VS Code, nhấn Ctrl+Shift+P → **Developer: Reload Window**. Mở Copilot Chat trong thư mục dự án, chọn chế độ Agent và thử gõ `/speckit-`. Việc nhận skill phụ thuộc phiên bản Copilot/VS Code hỗ trợ Agent Skills; nếu chưa thấy, cập nhật tiện ích và kiểm tra đã mở đúng thư mục có `.github/skills/`. Các file đã được cài không thay thế tài khoản/quyền sử dụng AI của bạn.

## Dùng trong Copilot Chat

Các lệnh dưới đây được gõ vào **ô chat**, không phải terminal PowerShell. Phiên bản này dùng dấu gạch ngang, ví dụ `/speckit-specify`; một số bài viết cũ dùng `/speckit.specify` của kiểu tích hợp khác.

Constitution dự án đã được viết sẵn. Khi thêm một thay đổi mới, bắt đầu bằng specify. Ví dụ dưới là yêu cầu tính năng tương lai, **chưa được triển khai**:

```text
/speckit-specify Bổ sung danh sách chờ theo từng chi nhánh khi không có giờ trống. Khách chỉ xem yêu cầu của mình, lễ tân chỉ xử lý chi nhánh được giao. Không tự tạo hoặc hủy lịch của khách.
```

Đọc `spec.md`: phạm vi, ngoại lệ, quyền và tiêu chí nghiệm thu. Nếu còn điểm chưa rõ:

```text
/speckit-clarify
```

Sau đó lập phương án dựa trên hệ thống đang có:

```text
/speckit-plan Dùng Django 5.2, PostgreSQL, HTML/CSS/JavaScript hiện có. Tuân thủ AGENTS.md và constitution. Tái sử dụng services/scheduling và phân quyền hiện có; nêu migration và kiểm thử cần thiết nếu có.
```

Tạo danh sách công việc rồi kiểm tra tính nhất quán trước khi sửa mã:

```text
/speckit-tasks
```

```text
/speckit-analyze
```

Khi phạm vi/kế hoạch đã được xem xét, thực hiện và đánh giá khoảng thiếu:

```text
/speckit-implement
```

```text
/speckit-converge
```

Nếu converge chỉ ra công việc còn thiếu, đọc kết quả và tiếp tục implement/converge cho đúng phạm vi. Có file spec hoặc các ô tasks được đánh dấu không thay thế bằng chứng chạy chương trình và kiểm thử.

Hai lệnh còn lại:

- `/speckit-checklist`: tạo checklist kiểm tra chất lượng yêu cầu.
- `/speckit-constitution`: chỉ dùng khi cần cập nhật nguyên tắc; giữ các quy tắc đã thống nhất trong `AGENTS.md` và các yêu cầu trực tiếp của bạn.

Một lời nhắc thông thường vẫn dùng được, ví dụ: “Đọc specs của tính năng đang chọn, kiểm tra nguyên tắc chi nhánh trong constitution và sửa lỗi tái hiện được”. Không cần gọi toàn bộ quy trình cho một sửa chữ nhỏ.

## Dùng trong Codex

Cùng các bước trên, dùng tiền tố `$` với tên skill trong ô chat, ví dụ:

```text
$speckit-specify Bổ sung danh sách chờ theo chi nhánh, theo yêu cầu và giới hạn nêu trên.
```

Các tên khác là `$speckit-plan`, `$speckit-tasks`, `$speckit-analyze`, `$speckit-implement`, `$speckit-converge`... Client Codex cần hỗ trợ đọc skill dự án tại `.agents/skills/`. Bộ skill hiện có của addyosmani dùng cho các bước kỹ thuật như kiểm tra bảo mật, UI, debugging; Spec Kit tổ chức đặc tả/kế hoạch của thay đổi. Không cần nạp mọi skill cùng lúc.

## Kiểm tra helper trong terminal

Các ví dụ helper upstream dùng `python3`. Trên Windows của bạn, thay phần đó bằng `.\.venv\Scripts\python.exe`; không cần launcher `py`. Linux dùng `.venv/bin/python` tại gốc repository. Bộ helper Python đã chọn không yêu cầu PowerShell 7 hoặc Bash trên Windows.

Chạy thử toàn bộ helper trong thư mục tạm có khoảng trắng và ký tự tiếng Việt:

```powershell
.\.venv\Scripts\python.exe scripts\verify_spec_kit.py --smoke
```

Chọn rõ hồ sơ tích hợp mẫu để xem dữ liệu prerequisite:

```powershell
$env:SPECIFY_FEATURE_DIRECTORY = "specs/001-adopt-spec-kit"
.\.venv\Scripts\python.exe .specify\scripts\python\check_prerequisites.py --json --require-spec --require-tasks --include-tasks
Remove-Item Env:SPECIFY_FEATURE_DIRECTORY
```

`.specify/feature.json` ghi tính năng đang chọn cho checkout này; nó được Git bỏ qua và không nằm trong manifest đồng bộ. Tính năng tiếp theo được tạo thành thư mục mới, ví dụ `specs/002-...`; tên branch Git không bắt buộc trùng tên thư mục. Bộ helper không tự tạo/đổi branch Git trong cấu hình hiện tại.

## Specify CLI: chỉ cài thêm khi cần quản lý/nâng cấp công cụ

Bộ skill/template/helper đã có trong repository và có thể dùng mà không cài CLI vào môi trường chạy Django. Nếu cần lệnh `specify version`, quản lý integration hoặc nâng cấp, có thể tạo môi trường công cụ riêng trên Windows:

```powershell
.\.venv\Scripts\python.exe -m venv .local\spec-kit-cli
.\.local\spec-kit-cli\Scripts\python.exe -m pip install "specify-cli==1.3.0"
.\.local\spec-kit-cli\Scripts\specify.exe version
.\.local\spec-kit-cli\Scripts\specify.exe integration list
```

CLI có các dependency riêng; không đưa chúng vào `requirements.txt` của website. Cài/nâng cấp công cụ cần Internet và Git nếu chọn cài từ nguồn Git; sử dụng AI tùy điều kiện gói công cụ/tài khoản của bạn. Chúng tôi chỉ thử helper và cài scaffold, không gọi mô hình bên ngoài hay kiểm tra thuê bao AI trong đợt tích hợp này.

Không chạy `specify init --here --force` để sửa lỗi website: lệnh đó có thể thay thế tài nguyên Spec Kit đang tùy chỉnh. Khi nâng cấp, tạo scaffold ở thư mục thử trước, so sánh diff và giữ constitution/specs hiện có; cập nhật provenance/hash tương ứng.

## Kiểm tra và giới hạn

- Nguồn ghim: [tag v1.3.0](https://github.com/github/spec-kit/tree/34a0d388eac671d656eb05b125ad3ed6056168ed); [hướng dẫn dự án hiện có](https://github.com/github/spec-kit/blob/34a0d388eac671d656eb05b125ad3ed6056168ed/docs/how-to/existing-projects.md).
- Specify CLI 1.3.0 được cài trong môi trường thử riêng và tạo scaffold Copilot/Codex thành công; các skill/template/helper có hash và giấy phép.
- Kiểm tra ngoại tuyến: 45 tài nguyên scaffold và 18 skill đúng nguồn, cấu hình Python/native events false; helper create/resolve/plan/tasks/prerequisites chạy trong thư mục tạm có khoảng trắng/tiếng Việt.
- 7 kiểm thử updater đạt; Ruff check/format và Django check đạt. Kiểm thử cập nhật thêm ranh giới file công khai Spec Kit và kiểm tra manifest tăng kích thước nhưng vẫn có giới hạn; từ chối credential, adapter package, feature pointer và đường dẫn riêng.
- Các kiểm tra này thực hiện trên Linux/Python 3.12. Không xác nhận thao tác chat đã chạy trong tiện ích VS Code/Windows của bạn, không coi scaffold là chứng nhận bảo mật, không chạy lại toàn bộ nghiệp vụ website khi chỉ thay công cụ/tài liệu.

Trạng thái công việc và bằng chứng cụ thể tại [tasks.md](../specs/001-adopt-spec-kit/tasks.md). File cũ trong `docs/quality/` vẫn lưu kết quả của lượt rà soát trước; không bị ghi đè bằng hồ sơ Spec Kit mới.
