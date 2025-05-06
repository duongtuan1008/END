import json
import cv2
import os
import serial
import time
import requests
import pickle
from picamera2 import Picamera2
import face_recognition
from pyfingerprint.pyfingerprint import PyFingerprint

# 🟢 Kết nối cảm biến vân tay AS608 qua UART
try:
    sensor = PyFingerprint('/dev/serial0', 57600, 0xFFFFFFFF, 0x00000000)

    if not sensor.verifyPassword():
        raise ValueError("Không thể xác thực cảm biến vân tay!")

except Exception as e:
    print(f"Lỗi cảm biến vân tay: {str(e)}")
    exit(1)

# 🟢 Khởi tạo camera
picam2 = Picamera2()
picam2.start()

# 🟢 Nhập ID người dùng
user_id = input("Nhập ID người dùng: ")

# 🟢 Tạo thư mục nếu chưa có
user_folder = f'dataset/{user_id}'
os.makedirs(user_folder, exist_ok=True)

count = 0
detecting_face = False
image_paths = []

# 📌 Quét và lưu vân tay (có thử lại nếu không khớp)
def enroll_fingerprint(user_id):
    print(f"📌 Đang lưu vân tay cho ID: {user_id}")
    print("👉 Vui lòng đặt ngón tay lên cảm biến...")

    while not sensor.readImage():
        pass
    sensor.convertImage(0x01)

    print("🔄 Nhấc ngón tay ra...")
    while sensor.readImage():
        pass
    print("👉 Đặt lại ngón tay lên cảm biến...")
    while not sensor.readImage():
        pass
    sensor.convertImage(0x02)

    if sensor.compareCharacteristics() == 0:
        print("❌ Vân tay không khớp, thử lại!")
        return enroll_fingerprint(user_id)  # 🔁 Thử lại nếu không khớp

    fingerprint_data = sensor.downloadCharacteristics(0x01)
    file_path = f"{user_folder}/fingerprint_{user_id}.dat"
    with open(file_path, "wb") as f:
        pickle.dump(fingerprint_data, f)

    print(f"✅ Vân tay của ID {user_id} đã được lưu thành công vào {file_path}!")
    return file_path

# 📌 Gọi hàm quét vân tay
fingerprint_path = enroll_fingerprint(user_id)

# 🟢 Nếu lưu vân tay thành công, tiếp tục chụp ảnh khuôn mặt
if fingerprint_path:
    # 👉 Đảm bảo cửa sổ hiển thị đúng kích thước
    cv2.namedWindow('Chụp Ảnh', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Chụp Ảnh', 640, 480)

    while count < 10:
        frame = picam2.capture_array()

        if frame is None or frame.size == 0:
            print("Lỗi: Không thể đọc frame.")
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        if face_locations:
            if not detecting_face:
                print("Khuôn mặt đã được phát hiện, bắt đầu chụp ảnh...")
            detecting_face = True

            img_path = f"{user_folder}/user_{count}.jpg"
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(img_path, gray)

            image_paths.append(img_path)
            print(f"📸 Đã lưu ảnh số {count + 1} cho người dùng {user_id}")
            count += 1
        else:
            if detecting_face:
                print("⛔ Không phát hiện khuôn mặt, dừng chụp ảnh...")
            detecting_face = False

        # 🟢 Vẽ khung quanh khuôn mặt
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        cv2.imshow('Chụp Ảnh', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

    # 🟢 Gửi danh sách ảnh lên server
    url = "http://192.168.137.88/api/upload.php"
    files = {
        'fingerprint': open(fingerprint_path, 'rb')
    }
    data = {
        'username': user_id,
        'image_paths': json.dumps(image_paths)
    }

    response = requests.post(url, files=files, data=data)
    print(response.text)

else:
    print("Lỗi lưu vân tay, không thể tiếp tục.")
