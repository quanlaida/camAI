# HƯỚNG DẪN CÀI ĐẶT SSH SERVER TRÊN WINDOWS

## CÁCH 1: DÙNG OPENSSH SERVER (CÓ SẴN TRONG WINDOWS 10/11)

### Bước 1: Kiểm tra SSH đã cài chưa

Mở PowerShell với quyền **Administrator**:

```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
```

### Bước 2: Cài đặt OpenSSH Server

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

### Bước 3: Khởi động SSH Service

```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

### Bước 4: Kiểm tra Firewall

```powershell
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

Hoặc kiểm tra xem rule đã có chưa:
```powershell
Get-NetFirewallRule -Name *ssh*
```

### Bước 5: Kiểm tra SSH đang chạy

```powershell
Get-Service sshd
```

Kết quả mong đợi: **Status: Running**

### Bước 6: Test kết nối

Từ máy khác, thử kết nối:
```bash
ssh DungDT@<IP_của_máy>
```

Hoặc từ chính máy đó:
```powershell
ssh localhost
```

---

## CÁCH 2: DÙNG SETTINGS (GIAO DIỆN ĐỒ HỌA)

### Windows 10/11:

1. Mở **Settings** (`Win + I`)
2. Vào **Apps** → **Optional Features**
3. Click **Add a feature**
4. Tìm **"OpenSSH Server"**
5. Click **Install**

### Sau khi cài:

1. Mở **Services** (`services.msc`)
2. Tìm **OpenSSH SSH Server**
3. Right-click → **Start**
4. Right-click → **Properties** → Set **Startup type** = **Automatic**

---

## CẤU HÌNH SSH

### 1. Cấu hình SSH Server

File cấu hình: `C:\ProgramData\ssh\sshd_config`

Mở file với quyền Administrator:
```powershell
notepad C:\ProgramData\ssh\sshd_config
```

**Các cấu hình quan trọng:**
```
Port 22                    # Port SSH (mặc định 22)
PermitRootLogin no        # Không cho phép root login
PasswordAuthentication yes # Cho phép đăng nhập bằng password
PubkeyAuthentication yes  # Cho phép đăng nhập bằng key
```

**Sau khi sửa, restart service:**
```powershell
Restart-Service sshd
```

### 2. Thay đổi Port SSH (Tùy chọn)

Nếu muốn đổi port (ví dụ: 2222):

1. Sửa file `sshd_config`:
   ```
   Port 2222
   ```

2. Cập nhật Firewall:
   ```powershell
   New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 2222
   ```

3. Restart service:
   ```powershell
   Restart-Service sshd
   ```

---

## KIỂM TRA VÀ XỬ LÝ LỖI

### Kiểm tra SSH đang chạy:

```powershell
Get-Service sshd
netstat -an | findstr :22
```

### Xem logs SSH:

```powershell
Get-Content C:\ProgramData\ssh\logs\sshd.log -Tail 50
```

### Restart SSH Service:

```powershell
Restart-Service sshd
```

### Kiểm tra Firewall:

```powershell
Get-NetFirewallRule -Name *ssh*
```

---

## KẾT NỐI TỪ MÁY KHÁC

### Từ Linux/Mac:

```bash
ssh DungDT@<IP_của_máy_Windows>
```

### Từ Windows (PowerShell):

```powershell
ssh DungDT@<IP_của_máy_Windows>
```

### Từ Windows (CMD):

```cmd
ssh DungDT@<IP_của_máy_Windows>
```

### Tìm IP của máy Windows:

```powershell
ipconfig
```

Tìm **IPv4 Address** (ví dụ: `192.168.1.7`)

---

## BẢO MẬT SSH

### 1. Tắt Password Authentication (chỉ dùng Key)

Sửa `sshd_config`:
```
PasswordAuthentication no
PubkeyAuthentication yes
```

### 2. Tạo SSH Key (trên máy client)

**Linux/Mac:**
```bash
ssh-keygen -t rsa -b 4096
ssh-copy-id DungDT@<IP_Windows>
```

**Windows (PowerShell):**
```powershell
ssh-keygen
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh DungDT@<IP_Windows> "mkdir -p .ssh && cat >> .ssh/authorized_keys"
```

### 3. Copy Public Key vào Windows

Trên máy Windows, tạo file:
```
C:\Users\DungDT\.ssh\authorized_keys
```

Paste nội dung public key vào file này.

### 4. Set quyền cho file (quan trọng!)

```powershell
icacls C:\Users\DungDT\.ssh\authorized_keys /inheritance:r
icacls C:\Users\DungDT\.ssh\authorized_keys /grant "DungDT:(R)"
```

---

## TẮT SSH SERVER

Nếu không cần SSH nữa:

```powershell
Stop-Service sshd
Set-Service -Name sshd -StartupType 'Disabled'
```

Hoặc gỡ cài đặt:
```powershell
Remove-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

---

## SỬ DỤNG SSH ĐỂ REMOTE

### 1. Remote Desktop qua SSH Tunnel

```bash
ssh -L 3389:localhost:3389 DungDT@<IP_Windows>
```

Sau đó kết nối RDP đến `localhost:3389`

### 2. Copy file qua SCP

```bash
# Copy từ Windows về máy khác
scp DungDT@<IP_Windows>:C:\path\to\file.txt ./

# Copy từ máy khác lên Windows
scp file.txt DungDT@<IP_Windows>:C:\path\to\
```

### 3. Chạy lệnh từ xa

```bash
ssh DungDT@<IP_Windows> "python server.py"
```

---

## LƯU Ý QUAN TRỌNG

1. **Firewall:** Đảm bảo port 22 (hoặc port bạn dùng) được mở trong Firewall
2. **Password:** Nếu dùng password, đảm bảo password mạnh
3. **Key:** Nên dùng SSH key thay vì password để bảo mật hơn
4. **Port:** Có thể đổi port để tránh bị scan
5. **Logs:** Kiểm tra logs thường xuyên để phát hiện truy cập bất thường

---

## TÓM TẮT CÁC BƯỚC CHÍNH

1. ✅ Cài OpenSSH Server: `Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0`
2. ✅ Start service: `Start-Service sshd`
3. ✅ Set auto-start: `Set-Service -Name sshd -StartupType 'Automatic'`
4. ✅ Mở Firewall: `New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22`
5. ✅ Test: `ssh localhost`

---

## HỖ TRỢ

Nếu gặp lỗi, kiểm tra:
- Service có đang chạy không: `Get-Service sshd`
- Firewall có mở port không: `Get-NetFirewallRule -Name *ssh*`
- Logs có lỗi gì không: `Get-Content C:\ProgramData\ssh\logs\sshd.log -Tail 50`

