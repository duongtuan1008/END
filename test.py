from pyfingerprint.pyfingerprint import PyFingerprint

try:
    finger = PyFingerprint('/dev/ttyAMA3', 57600, 0xFFFFFFFF, 0x00000000)

    if not finger.verifyPassword():
        raise ValueError("Lỗi: Không thể xác minh mật khẩu cảm biến vân tay!")

    print("✅ Kết nối cảm biến vân tay thành công!")

    print("Đặt ngón tay lên cảm biến...")
    
    if finger.readImage():
        print("✅ Đọc vân tay thành công!")
    else:
        print("❌ Không thể đọc vân tay.")

except Exception as e:
    print(f"❌ Lỗi cảm biến vân tay: {e}")
