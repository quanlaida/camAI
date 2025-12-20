"""
Script test Telegram Bot
Sử dụng script này để test bot và lấy Chat ID
"""
import requests
import sys

# Bot token từ BotFather
BOT_TOKEN = "8536552488:AAGmQD-vjI9nP3jV4dli1ToNNdKhfcv5rXU"

def get_bot_info():
    """Lấy thông tin bot"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print("✅ Bot thông tin:")
                print(f"   Tên: {bot_info.get('first_name')}")
                print(f"   Username: @{bot_info.get('username')}")
                print(f"   ID: {bot_info.get('id')}")
                return True
            else:
                print(f"❌ Lỗi: {data.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return False

def get_updates():
    """Lấy tin nhắn mới nhất từ bot (để lấy Chat ID)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                updates = data.get('result', [])
                if updates:
                    print("\n✅ Các tin nhắn gần đây:")
                    for update in updates[-5:]:  # Hiển thị 5 tin nhắn gần nhất
                        message = update.get('message', {})
                        chat = message.get('chat', {})
                        chat_id = chat.get('id')
                        first_name = chat.get('first_name', 'Unknown')
                        text = message.get('text', '')
                        print(f"   Chat ID: {chat_id} | Tên: {first_name} | Tin nhắn: {text}")
                    
                    # Lấy Chat ID mới nhất
                    if updates:
                        latest_update = updates[-1]
                        latest_chat = latest_update.get('message', {}).get('chat', {})
                        latest_chat_id = latest_chat.get('id')
                        latest_name = latest_chat.get('first_name', 'Unknown')
                        print(f"\n💡 Chat ID của bạn: {latest_chat_id} ({latest_name})")
                        print(f"   Hãy sử dụng Chat ID này trong web UI!")
                        return latest_chat_id
                else:
                    print("\n⚠️ Chưa có tin nhắn nào. Hãy gửi tin nhắn cho bot @Camera_AI_Canh_Bao_Tu_Dong_BOT trước!")
                    print("   Sau đó chạy lại script này để lấy Chat ID.")
                    return None
            else:
                print(f"❌ Lỗi: {data.get('description', 'Unknown error')}")
                return None
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return None

def send_test_message(chat_id):
    """Gửi tin nhắn test"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    message = "✅ *TEST TELEGRAM BOT*\n\nĐây là tin nhắn test từ hệ thống CamAI. Nếu bạn nhận được tin nhắn này, bot đã hoạt động đúng!"
    
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"\n✅ Đã gửi tin nhắn test đến Chat ID: {chat_id}")
                print("   Vui lòng kiểm tra Telegram của bạn!")
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
    
    # Test bot info
    print("\n1. Kiểm tra bot thông tin...")
    if not get_bot_info():
        print("\n❌ Bot không hoạt động. Vui lòng kiểm tra token!")
        sys.exit(1)
    
    # Get updates để lấy Chat ID
    print("\n2. Lấy Chat ID...")
    chat_id = get_updates()
    
    if chat_id:
        # Test send message
        print(f"\n3. Gửi tin nhắn test đến Chat ID: {chat_id}...")
        send_test_message(chat_id)
        
        print("\n" + "=" * 60)
        print("📝 HƯỚNG DẪN CẤU HÌNH:")
        print("=" * 60)
        print(f"1. Thêm vào file .env hoặc environment variable:")
        print(f"   TELEGRAM_BOT_TOKEN=8536552488:AAGmQD-vjI9nP3jV4dli1ToNNdKhfcv5rXU")
        print(f"\n2. Chat ID của bạn: {chat_id}")
        print(f"   Nhập Chat ID này vào web UI trong phần 'Telegram cảnh báo'")
        print(f"\n3. Restart server để áp dụng cấu hình mới")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("📝 HƯỚNG DẪN:")
        print("=" * 60)
        print("1. Mở Telegram và tìm bot: @Camera_AI_Canh_Bao_Tu_Dong_BOT")
        print("2. Gửi bất kỳ tin nhắn nào cho bot (ví dụ: /start hoặc 'Hello')")
        print("3. Chạy lại script này để lấy Chat ID")
        print("=" * 60)
