## Ghi chú cho AI / dev khi dùng Cursor

- **Phạm vi chỉnh sửa ưu tiên**:
  - Chỉ chỉnh sửa **server** (Flask, DB, API, web).
  - Và **client Orange Pi** (`out-quan-boxcamai-client-orangepi/`).
  - Tránh sửa client Raspberry hoặc phần khác, trừ khi có yêu cầu rõ ràng.

- **Nơi mô tả kiến trúc**:
  - Xem `docs/ARCHITECTURE.md` để hiểu kiến trúc tổng thể, luồng dữ liệu và vai trò từng module.

- **Theo dõi thay đổi / ý tưởng**:
  - Ghi lại mọi thay đổi kiến trúc, API, hoặc hành vi quan trọng trong `docs/CHANGELOG.md`.
  - Khi thêm tính năng mới, mô tả ngắn:
    - Lý do thêm.
    - Cách hoạt động tổng quát.
    - File chính liên quan (server / Orange Pi client).

- **Phong cách comment**:
  - Comment chỉ giải thích **ý tưởng / lý do thiết kế**, không lặp lại nội dung code.
  - Những chỗ “đặc biệt” như IoU cooldown, priority classes, auto-restart nên có 1–2 dòng giải thích.

- **Khi mở repo bằng Cursor account khác**:
  - Đọc lần lượt:
    1. `README.md` (nếu có).
    2. `docs/ARCHITECTURE.md`.
    3. `docs/CHANGELOG.md`.
    4. File này `docs/CURSOR_NOTES.md` để biết phạm vi được phép chỉnh sửa.
