# 🚀 Hướng Dẫn Push Git Nhanh

## 📝 Các Lệnh Cơ Bản

### **1. Kiểm tra trạng thái:**
```bash
git status
```

### **2. Thêm tất cả files:**
```bash
git add .
```

### **3. Commit:**
```bash
git commit -m "Mô tả thay đổi"
```

### **4. Push lên GitHub:**
```bash
git push origin main
```

---

## 🔄 Lần Đầu Push (Nếu chưa có remote)

### **1. Thêm remote repository:**
```bash
git remote add origin https://github.com/USERNAME/REPO_NAME.git
```

### **2. Push lần đầu:**
```bash
git push -u origin main
```

---

## ⚡ Lệnh Nhanh (Copy & Paste)

```bash
# Kiểm tra
git status

# Add tất cả
git add .

# Commit
git commit -m "Update code"

# Push
git push origin main
```

---

## 🔑 Xác Thực GitHub

Nếu hỏi username/password:
- **Username:** Tên GitHub của bạn
- **Password:** Dùng **Personal Access Token** (không phải password thật)
  - Tạo token: GitHub → Settings → Developer settings → Personal access tokens → Generate new token
  - Quyền: chọn `repo`

---

## ❌ Lỗi Thường Gặp

### **"remote origin already exists"**
```bash
git remote remove origin
git remote add origin https://github.com/USERNAME/REPO_NAME.git
```

### **"failed to push"**
```bash
git pull origin main
git push origin main
```

---

**Xong!** ✅

