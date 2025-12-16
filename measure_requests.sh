#!/bin/bash
# Script đo số request gửi lên server trong 10 giây

DURATION=10
SERVER="boxcamai.cloud"
PORT=443

echo "=========================================="
echo "ĐO SỐ REQUEST GỬI LÊN SERVER"
echo "=========================================="
echo "Server: $SERVER:$PORT"
echo "Thời gian: $DURATION giây"
echo ""

# Kiểm tra quyền sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Cần quyền sudo để chạy tcpdump"
    echo "Chạy: sudo $0"
    exit 1
fi

echo "Đang đo..."
start_time=$(date +%s)

# Đếm packets
packet_count=$(timeout $DURATION tcpdump -i any -n "host $SERVER and port $PORT" 2>/dev/null | wc -l)

end_time=$(date +%s)
actual_duration=$((end_time - start_time))

# Tính FPS (ước tính: mỗi request tạo ~5-10 packets)
# Giả sử mỗi request tạo 7 packets trung bình
estimated_requests=$(echo "scale=2; $packet_count / 7" | bc)
fps=$(echo "scale=2; $estimated_requests / $actual_duration" | bc)

echo ""
echo "=========================================="
echo "KẾT QUẢ"
echo "=========================================="
echo "Thời gian đo: ${actual_duration} giây"
echo "Số packets: $packet_count"
echo "Packets/giây: $(echo "scale=2; $packet_count / $actual_duration" | bc)"
echo ""
echo "Ước tính:"
echo "Số request: ~$estimated_requests"
echo "FPS gửi lên server: ~$fps"
echo ""
echo "Lưu ý:"
echo "- Mỗi request có thể tạo 5-10 packets (TCP handshake, data, ACK, etc)"
echo "- FPS thực tế có thể dao động ±20%"
echo "- Nếu muốn chính xác hơn, dùng lệnh tcpdump với filter POST"
echo "=========================================="
