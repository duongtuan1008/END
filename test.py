import serial
import time

# Cấu hình UART radar HLK-LD2410
PORT = '/dev/ttyAMA3'  # UART3, dùng GPIO4 (TX) và GPIO5 (RX)
BAUDRATE = 256000

# Gói lệnh để thoát "config mode"
EXIT_CONFIG_COMMAND = bytes.fromhex('F4F502000000FB')

def send_exit_config_command(ser):
    """Gửi lệnh thoát chế độ cấu hình"""
    print("📤 Gửi lệnh thoát 'Config Mode'...")
    ser.write(EXIT_CONFIG_COMMAND)
    time.sleep(0.5)
    resp = ser.read(ser.in_waiting)
    print("📥 Phản hồi khi gửi lệnh:", resp.hex() if resp else "(không có phản hồi)")

def parse_radar_data(data):
    """Phân tích gói dữ liệu từ radar"""
    if len(data) >= 12 and data[0] == 0xF4 and data[1] == 0xF3:
        motion = data[8]
        distance = int.from_bytes(data[9:11], byteorder='little')
        status = "🟢 Có người!" if motion else "⚪ Không phát hiện"
        print(f"{status}  |  📏 Khoảng cách: {distance} cm")
    else:
        print("⚠️ Gói không hợp lệ:", data.hex())

# Mở kết nối serial
try:
    radar = serial.Serial(PORT, baudrate=BAUDRATE, timeout=1)
    print("✅ Đã kết nối radar HLK-LD2410 qua", PORT)

    # Gửi lệnh thoát chế độ cấu hình nếu cần
    send_exit_config_command(radar)

    print("📡 Bắt đầu đọc dữ liệu từ radar...\n")

    while True:
        if radar.in_waiting > 0:
            raw = radar.read(radar.in_waiting)
            print("📥 Dữ liệu nhận:", raw.hex())

            found = False
            for i in range(len(raw) - 11):
                if raw[i] == 0xF4 and raw[i+1] == 0xF3:
                    frame = raw[i:i+12]
                    print("✅ Gói radar hợp lệ:", frame.hex())
                    parse_radar_data(frame)
                    found = True
                    break
            if not found:
                print("❌ Không tìm thấy gói hợp lệ F4F3 trong dữ liệu.")

        else:
            print("⏳ Không có dữ liệu UART, đang chờ...")
        time.sleep(0.3)

except Exception as e:
    print(f"❌ Lỗi: {e}")
finally:
    if 'radar' in locals():
        radar.close()
