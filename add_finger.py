import os
import serial
import time
import pickle
import requests
from pyfingerprint.pyfingerprint import PyFingerprint

# 🟢 Kết nối cảm biến vân tay AS608
try:
    sensor = PyFingerprint('/dev/serial0', 57600, 0xFFFFFFFF, 0x00000000)

    if not sensor.verifyPassword():
        raise ValueError("Không thể xác thực cảm biến vân tay!")

except Exception as e:
    print(f"❌ Lỗi cảm biến vân tay: {str(e)}")
    exit(1)

# 🟢 Nhập ID người dùng
user_id = input("🔹 Nhập ID người dùng để cập nhật vân tay: ").strip()

# 🟢 Kiểm tra thư mục chứa ảnh người dùng
user_folder = f'dataset/{user_id}'
if not os.path.exists(user_folder):
    print(f"❌ Không tìm thấy thư mục {user_folder}. Hãy kiểm tra lại.")
    exit(1)

# 🟢 Kiểm tra danh sách ảnh
image_paths = [f for f in os.listdir(user_folder) if f.endswith(".jpg")]
if not image_paths:
    print("⚠ Không tìm thấy ảnh nào trong thư mục!")
else:
    print(f"📤 Số ảnh tìm thấy: {len(image_paths)}")

# 📌 Quét vân tay và lưu file
def enroll_fingerprint(user_id):
    print(f"📌 Đang lưu vân tay cho ID: {user_id}")
    
    # 🟢 Bước 1: Đặt ngón tay lên cảm biến
    print("👉 Vui lòng đặt ngón tay lên cảm biến...")
    while not sensor.readImage():
        pass

    sensor.convertImage(0x01)

    # 🟢 Bước 2: Nhấc ngón tay ra và đặt lại
    print("🔄 Nhấc ngón tay ra...")
    while sensor.readImage():
        pass  # Đợi cho đến khi nhấc ngón tay ra

    print("👉 Đặt lại ngón tay lên cảm biến...")
    while not sensor.readImage():
        pass

    sensor.convertImage(0x02)

    # 🟢 Kiểm tra vân tay có khớp không
    if sensor.compareCharacteristics() == 0:
        print("❌ Vân tay không khớp, thử lại!")
        return False

    # 🟢 Lưu vân tay vào file
    fingerprint_data = sensor.downloadCharacteristics(0x01)

    file_path = f"{user_folder}/fingerprint_{user_id}.dat"
    with open(file_path, "wb") as f:
        pickle.dump(fingerprint_data, f)

    print(f"✅ Vân tay của ID {user_id} đã được lưu thành công vào {file_path}!")

    return file_path

# 📌 Gọi hàm quét vân tay
fingerprint_path = enroll_fingerprint(user_id)

# 🟢 Nếu quét vân tay thành công, gửi lên MySQL
if fingerprint_path:
    url = "http://192.168.137.88/api/update_fingerprint.php"

    files = {'fingerprint': open(fingerprint_path, 'rb')}
    
    # 🟢 Gửi tất cả ảnh đúng cách
    for i, img in enumerate(image_paths):
        files[f'images[{i}]'] = open(f"{user_folder}/{img}", 'rb')

    data = {'username': user_id}

    response = requests.post(url, files=files, data=data)
    print(f"📤 Server response: {response.text}")  # In phản hồi từ server
else:
    print("❌ Không thể cập nhật vân tay.")