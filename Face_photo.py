import cv2
import os
from picamera2 import Picamera2
import face_recognition

# Khởi tạo camera với Picamera2
picam2 = Picamera2()
picam2.start()

# Đặt ID cho người dùng
user_id = input("Nhập ID cho người dùng: ")

# Tạo thư mục cho người dùng
os.makedirs(f'dataset/{user_id}', exist_ok=True)

count = 0
detecting_face = False  # Biến để theo dõi trạng thái nhận diện khuôn mặt

while count < 100:  # Chụp 100 ảnh
    # Capture the frame from the Picamera2
    frame = picam2.capture_array()

    # Kiểm tra xem đã đọc được frame không
    if frame is None or frame.size == 0:
        print("Error: Could not read frame.")
        break

    # Chuyển đổi khung hình thành RGB (face_recognition yêu cầu)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Phát hiện khuôn mặt trong khung hình
    face_locations = face_recognition.face_locations(rgb_frame)

    # Nếu có khuôn mặt được phát hiện
    if face_locations:
        if not detecting_face:  # Nếu trước đó không nhận diện khuôn mặt
            print("Khuôn mặt đã được phát hiện, bắt đầu chụp ảnh...")
        detecting_face = True  # Đánh dấu rằng đã bắt đầu nhận diện khuôn mặt

        # Lưu ảnh vào thư mục
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(f'dataset/{user_id}/user.{count}.jpg', gray)
        print(f"Đã lưu ảnh số {count + 1} cho người dùng {user_id}")
        count += 1

    else:
        if detecting_face:  # Nếu không còn khuôn mặt
            print("Không phát hiện khuôn mặt, dừng chụp ảnh...")
        detecting_face = False  # Đánh dấu rằng không còn nhận diện khuôn mặt

    # Hiển thị khung hình
    cv2.imshow('Chụp Ảnh', frame)

    # Dừng lại nếu nhấn 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng camera và đóng cửa sổ hiển thị
cv2.destroyAllWindows()
