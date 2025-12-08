# 📤 Hướng Dẫn Push Code Lên GitHub

## Bước 1: Tạo Repository trên GitHub

1. Đăng nhập vào GitHub: https://github.com
2. Click **"New repository"** (hoặc **"+"** → **"New repository"**)
3. Điền thông tin:
   - **Repository name**: `camAI` (hoặc tên bạn muốn)
   - **Description**: "AI Detection Dashboard với YOLOv5"
   - Chọn **Public** hoặc **Private**
   - **KHÔNG** check "Initialize with README" (vì đã có code rồi)
4. Click **"Create repository"**

## Bước 2: Push Code Lên GitHub

Sau khi tạo repository, GitHub sẽ hiển thị hướng dẫn. Chạy các lệnh sau:

```bash
# Đảm bảo đang ở thư mục camAI
cd C:\Users\admin\Downloads\camAI

# Thêm remote repository (thay YOUR_USERNAME và YOUR_REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Hoặc nếu dùng SSH:
# git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git

# Push code lên GitHub
git branch -M main
git push -u origin main
```

## Bước 3: Xác thực (nếu cần)

- Nếu GitHub yêu cầu authentication:
  - Dùng **Personal Access Token** (không dùng password)
  - Tạo token tại: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Quyền: chọn `repo` (full control)

## Lệnh Nhanh (Copy & Paste)

```bash
# 1. Kiểm tra status
git status

# 2. Add tất cả files (nếu chưa add)
git add .

# 3. Commit
git commit -m "Initial commit: AI Detection Dashboard"

# 4. Thêm remote (THAY YOUR_USERNAME và YOUR_REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 5. Push lên GitHub
git push -u origin main
```

## Lưu Ý

- File `.gitignore` đã được tạo để bỏ qua:
  - Database files (*.db)
  - Captured images
  - Python cache (__pycache__)
  - Model files (*.onnx) - có thể uncomment nếu muốn track
  - Environment files (.env)

- Nếu có file lớn (>100MB), GitHub sẽ từ chối. Cần dùng Git LFS hoặc bỏ qua trong .gitignore

## Troubleshooting

### Lỗi: "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

### Lỗi: "failed to push some refs"
```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### Lỗi: Authentication failed
- Tạo Personal Access Token mới
- Dùng token thay vì password khi push

## Sau Khi Push Thành Công

✅ Code đã được upload lên GitHub
✅ Có thể clone về máy khác: `git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git`
✅ Có thể share link repository cho người khác

