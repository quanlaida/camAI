#!/bin/bash
# Script monitor performance real-time

echo "Monitoring system resources (Press Ctrl+C to stop)..."
echo ""

while true; do
    clear
    echo "=========================================="
    echo "REAL-TIME MONITORING - $(date '+%H:%M:%S')"
    echo "=========================================="
    echo ""
    
    # CPU
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100-$1}')
    echo "CPU Usage: ${cpu_usage}%"
    
    # Memory
    mem_info=$(free -m | grep Mem)
    mem_total=$(echo $mem_info | awk '{print $2}')
    mem_used=$(echo $mem_info | awk '{print $3}')
    mem_percent=$((mem_used * 100 / mem_total))
    echo "Memory: ${mem_used}MB / ${mem_total}MB (${mem_percent}%)"
    
    # Temperature
    if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        temp=$(cat /sys/class/thermal/thermal_zone0/temp)
        temp_c=$((temp/1000))
        echo "Temperature: ${temp_c}°C"
    fi
    
    # BoxCamAI Process
    if pgrep -f "main.py" > /dev/null; then
        pid=$(pgrep -f "main.py" | head -1)
        cpu_proc=$(ps -p $pid -o %cpu --no-headers | xargs)
        mem_proc=$(ps -p $pid -o %mem --no-headers | xargs)
        echo "BoxCamAI Process:"
        echo "  CPU: ${cpu_proc}%"
        echo "  Memory: ${mem_proc}%"
    else
        echo "BoxCamAI: Not running"
    fi
    
    echo ""
    echo "Press Ctrl+C to stop..."
    sleep 2
done
