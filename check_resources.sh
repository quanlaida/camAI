#!/bin/bash
# Script kiểm tra tài nguyên hệ thống trên Raspberry Pi

echo "=========================================="
echo "THONG SO TAI NGUYEN HE THONG"
echo "=========================================="
echo ""

# CPU Info
echo "--- CPU Information ---"
echo "Model: $(cat /proc/cpuinfo | grep 'Model' | head -1 | cut -d: -f2 | xargs)"
echo "CPU Cores: $(nproc)"
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print "  Idle: " 100-$1 "% | Used: " $1 "%"}'
echo ""

# Memory Info
echo "--- Memory Information ---"
free -h | grep -E "Mem|Swap"
echo ""

# Temperature
echo "--- Temperature ---"
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    temp=$(cat /sys/class/thermal/thermal_zone0/temp)
    temp_c=$((temp/1000))
    echo "CPU Temperature: ${temp_c}°C"
    if [ $temp_c -gt 80 ]; then
        echo "  ⚠️  WARNING: Temperature cao! (>80°C)"
    elif [ $temp_c -gt 70 ]; then
        echo "  ⚠️  CAUTION: Temperature hơi cao (>70°C)"
    else
        echo "  ✅ Temperature bình thường"
    fi
else
    echo "Không thể đọc temperature"
fi
echo ""

# Disk Usage
echo "--- Disk Usage ---"
df -h / | tail -1
echo ""

# GPU Memory (Raspberry Pi)
echo "--- GPU Memory (Raspberry Pi) ---"
if command -v vcgencmd &> /dev/null; then
    echo "GPU Memory Split: $(vcgencmd get_mem gpu | cut -d= -f2)"
    echo "GPU Temperature: $(vcgencmd measure_temp | cut -d= -f2)"
else
    echo "vcgencmd không có sẵn"
fi
echo ""

# Running Processes
echo "--- Top Processes (CPU) ---"
ps aux --sort=-%cpu | head -6
echo ""

# BoxCamAI Service Status
echo "--- BoxCamAI Service Status ---"
if systemctl is-active --quiet boxcamai; then
    echo "Status: ✅ Running"
    echo "PID: $(systemctl show -p MainPID boxcamai | cut -d= -f2)"
    echo "Memory Usage:"
    systemctl status boxcamai | grep -E "Memory|CPU" | head -2
else
    echo "Status: ❌ Not Running"
fi
echo ""

# Network
echo "--- Network ---"
echo "IP Address: $(hostname -I | awk '{print $1}')"
echo ""

echo "=========================================="
echo "KET THUC"
echo "=========================================="
