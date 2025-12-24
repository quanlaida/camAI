"""
Script test Telegram Bot với Group Chat ID
"""
import requests
import sys
import io

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Bot token và Chat ID của nhóm
BOT_TOKEN = "8536552488:AAGmQD-vjI9nP3jV4dli1ToNNdKhfcv5rXU"
CHAT_ID = "-5009640116"  # Chat ID của nhóm "Cảnh báo tự động"

def send_test_message():
    """Gửi tin nhắn test đến nhóm"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    message = "✅ *TEST TELEGRAM BOT*\n\nĐây là tin nhắn test từ hệ thống CamAI.\n\n🚨 Bot sẽ tự động gửi cảnh báo khi phát hiện đối tượng trong khu vực ROI."
    
    data = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        print(f"📤 Đang gửi tin nhắn test đến nhóm (Chat ID: {CHAT_ID})...")
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Đã gửi tin nhắn test thành công!")
                print("   Vui lòng kiểm tra nhóm Telegram 'Cảnh báo tự động'")
                return True
            else:
                print(f"❌ Lỗi: {result.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi gửi tin nhắn: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 TEST TELEGRAM BOT - CamAI Alert System")
    print("=" * 60)
    send_test_message()
    print("=" * 60)

