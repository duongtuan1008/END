import serial
from pyfingerprint.pyfingerprint import PyFingerprint

# Kết nối với cảm biến vân tay AS608
try:
    sensor = PyFingerprint('/dev/serial0', 57600, 0xFFFFFFFF, 0x00000000)

    if not sensor.verifyPassword():
        raise ValueError("Không thể xác thực cảm biến vân tay!")

except Exception as e:
    print(f"Lỗi cảm biến vân tay: {str(e)}")
    exit(1)

# Xác nhận trước khi xóa
confirm = input("Bạn có chắc chắn muốn XÓA TẤT CẢ vân tay? (yes/no): ")
if confirm.lower() == "yes":
    try:
        sensor.clearDatabase()
        print("🟢 Đã xóa toàn bộ dữ liệu vân tay thành công!")
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {str(e)}")
else:
    print("⚠ Hủy thao tác xóa vân tay.")
