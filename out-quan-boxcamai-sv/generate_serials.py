"""
Script để generate danh sách Serial codes
Format: YYYY + mã nhị phân (binary)
Ví dụ: 20250000, 20250001, 20250010, 20250011, 20251001, ...
"""
import json

def generate_serials_binary(year=2025, bits=4, start=0, count=None):
    """
    Generate danh sách Serial codes với mã nhị phân
    
    Args:
        year: Năm (mặc định 2025)
        bits: Số bit nhị phân (mặc định 4)
        start: Số bắt đầu (mặc định 0)
        count: Số lượng Serial cần tạo (None = tất cả có thể với số bit đó)
    
    Returns:
        List of Serial codes
    """
    if count is None:
        # Tự động tính số lượng tối đa với số bit
        count = 2 ** bits  # 4 bit = 16 mã, 5 bit = 32 mã
    
    serials = []
    max_value = 2 ** bits - 1  # 4 bit: 0-15, 5 bit: 0-31
    
    for i in range(start, min(start + count, max_value + 1)):
        # Convert to binary với số bit tương ứng
        binary_str = format(i, f'0{bits}b')  # Format as 4-bit binary: 0000, 0001, ...
        serial = f"{year}{binary_str}"  # Format: 20250000, 20250001, ...
        serials.append(serial)
    return serials

if __name__ == "__main__":
    # Generate 30 Serial codes với mã nhị phân 5 bit (0-29, tức là 00000-11101)
    serials = generate_serials_binary(2025, bits=5, start=0, count=30)
    
    print("=" * 50)
    print("Danh sách 30 mã Serial (mã nhị phân 5 bit):")
    print("=" * 50)
    for idx, serial in enumerate(serials, 1):
        # Extract binary part for display
        binary_part = serial[4:]  # Get part after year
        decimal_value = int(binary_part, 2)  # Convert binary to decimal
        print(f"{idx:2d}. {serial} (binary: {binary_part} = {decimal_value} decimal)")
    
    print("\n" + "=" * 50)
    print("Format JSON (để import vào database):")
    print("=" * 50)
    print(json.dumps(serials, indent=2))
    
    # Save to file
    with open('SERIAL_CODES.txt', 'w', encoding='utf-8') as f:
        f.write("Danh sách 30 mã Serial cho thiết bị:\n")
        f.write("Format: 2025 + mã nhị phân 5 bit (00000-11101)\n\n")
        for serial in serials:
            f.write(f"{serial}\n")
        f.write("\nGiải thích:\n")
        f.write("- Format: 2025 + [mã nhị phân 4 bit]\n")
        for idx, serial in enumerate(serials):
            binary_part = serial[4:]
            decimal_value = int(binary_part, 2)
            f.write(f"- {binary_part} = {decimal_value} (decimal)\n")
        f.write(f"- Tổng cộng: {len(serials)} mã (từ 0 đến {len(serials)-1})\n")
    
    print("\n✅ Đã lưu vào file SERIAL_CODES.txt")

