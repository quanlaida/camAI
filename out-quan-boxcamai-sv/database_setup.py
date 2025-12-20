from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL, SERVER_IMAGES_DIR
import os

Base = declarative_base()

class Client(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # Tên hiển thị (có thể đổi)
    serial_number = Column(String(100), nullable=False, unique=True)  # Serial number (không đổi, unique)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_detect_enabled = Column(Boolean, default=True, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    show_roi_overlay = Column(Boolean, default=True, nullable=False)  # Hiển thị ROI trên stream
    rtsp_subtype = Column(Integer, default=1, nullable=False)  # RTSP subtype: 0=chất lượng cao, 1=chất lượng thấp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   # ✅ vùng nhận diện (Region of Interest)
    # Giữ tương thích ngược: vẫn giữ 1 ROI cũ (roi_x1, y1, x2, y2)
    roi_x1 = Column(Float, nullable=True)
    roi_y1 = Column(Float, nullable=True)
    roi_x2 = Column(Float, nullable=True)
    roi_y2 = Column(Float, nullable=True)
    # Nhiều ROI hợp nhất - lưu mảng ROI dạng JSON: [{"x1": float, "y1": float, "x2": float, "y2": float}, ...]
    # Logic: Chỉ detect khi object trong TẤT CẢ các ROI
    roi_regions = Column(Text, nullable=True)  # JSON string: [{"x1": float, "y1": float, "x2": float, "y2": float}, ...]
    # Relationship to detections
    detections = relationship("Detection", back_populates="client")

class Detection(Base):
    __tablename__ = 'detections'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    class_name = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    image_path = Column(String(255), nullable=False)
    bbox_x = Column(Integer, nullable=False)
    bbox_y = Column(Integer, nullable=False)
    bbox_width = Column(Integer, nullable=False)
    bbox_height = Column(Integer, nullable=False)
    metadata_json = Column(Text)  # JSON string for additional data
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=True)

    # Relationship to client
    client = relationship("Client", back_populates="detections")

class AlertSettings(Base):
    __tablename__ = 'alert_settings'

    id = Column(Integer, primary_key=True)
    alert_email = Column(String(255), nullable=True)  # Email để nhận cảnh báo
    email_enabled = Column(Boolean, default=False, nullable=False)
    telegram_chat_id = Column(String(50), nullable=True)  # Telegram Chat ID để nhận cảnh báo
    telegram_enabled = Column(Boolean, default=False, nullable=False)  # Bật/tắt cảnh báo Telegram
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_database():
    """Initialize the database and create tables"""
    # Tăng pool size để tránh connection timeout khi có nhiều requests đồng thời
    engine = create_engine(
        DATABASE_URL, 
        echo=False,
        pool_size=10,  # Tăng từ mặc định 5 lên 10
        max_overflow=20,  # Tăng từ mặc định 10 lên 20
        pool_pre_ping=True,  # Kiểm tra connection trước khi dùng
        pool_recycle=3600  # Recycle connections sau 1 giờ
    )

    # Create tables
    Base.metadata.create_all(engine)
    
    # Auto-migration: Add serial_number column if not exists
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    # Check if column exists by getting all columns and checking names
    columns = [col['name'] for col in inspector.get_columns('clients')]
    if 'serial_number' not in columns:
        with engine.connect() as connection:
            connection.execute(text("ALTER TABLE clients ADD COLUMN serial_number VARCHAR(100)"))
            connection.commit()
            print("✅ Added 'serial_number' column to 'clients' table.")
            # Set default serial_number for existing clients (based on name)
            try:
                connection.execute(text("UPDATE clients SET serial_number = name WHERE serial_number IS NULL"))
                connection.commit()
                print("✅ Set default serial_number for existing clients.")
            except Exception as e:
                print(f"⚠️  Warning: Could not set default serial_number: {e}")
    if 'show_roi_overlay' not in columns:
        with engine.connect() as connection:
            connection.execute(text("ALTER TABLE clients ADD COLUMN show_roi_overlay BOOLEAN DEFAULT 1"))
            connection.commit()
            print("✅ Added 'show_roi_overlay' column to 'clients' table (default TRUE).")
    if 'rtsp_subtype' not in columns:
        with engine.connect() as connection:
            connection.execute(text("ALTER TABLE clients ADD COLUMN rtsp_subtype INTEGER DEFAULT 1"))
            connection.commit()
            print("✅ Added 'rtsp_subtype' column to 'clients' table (default 1 = chất lượng thấp).")

    # Create images directory
    os.makedirs(SERVER_IMAGES_DIR, exist_ok=True)

    return engine

def get_session(engine):
    """Get a database session"""
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    print("Initializing database...")
    engine = init_database()
    print("Database initialized successfully!")
