"""
Script migrate database để thêm cột telegram_chat_id và telegram_enabled vào bảng alert_settings
Chạy script này một lần để cập nhật database schema
"""
import sqlite3
import os
from pathlib import Path

# Đường dẫn database
db_path = os.path.join(os.path.dirname(__file__), 'detections.db')

def migrate_database():
    """Thêm cột telegram vào bảng alert_settings nếu chưa có"""
    if not os.path.exists(db_path):
        print(f"⚠️  Database không tồn tại tại: {db_path}")
        print("   Database sẽ được tạo tự động khi server khởi động.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Kiểm tra xem cột đã tồn tại chưa
        cursor.execute("PRAGMA table_info(alert_settings)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'telegram_chat_id' not in columns:
            print("📝 Thêm cột telegram_chat_id vào bảng alert_settings...")
            cursor.execute("ALTER TABLE alert_settings ADD COLUMN telegram_chat_id VARCHAR(50)")
            print("✅ Đã thêm cột telegram_chat_id")
        else:
            print("✅ Cột telegram_chat_id đã tồn tại")
        
        if 'telegram_enabled' not in columns:
            print("📝 Thêm cột telegram_enabled vào bảng alert_settings...")
            cursor.execute("ALTER TABLE alert_settings ADD COLUMN telegram_enabled BOOLEAN DEFAULT 0")
            print("✅ Đã thêm cột telegram_enabled")
        else:
            print("✅ Cột telegram_enabled đã tồn tại")
        
        conn.commit()
        print("\n✅ Migration hoàn tất!")
        
    except Exception as e:
        print(f"❌ Lỗi khi migrate: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 MIGRATE DATABASE - Thêm cột Telegram")
    print("=" * 60)
    migrate_database()
