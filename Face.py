import cv2
import pickle
from picamera2 import Picamera2
import face_recognition
import numpy as np
import RPi.GPIO as GPIO
import time
import threading
import queue
from email.message import EmailMessage
import mimetypes
import smtplib
import imghdr
import face_recognition
from datetime import datetime
import datetime
import os
import serial
from RPLCD.i2c import CharLCD
import pickle
from pyfingerprint.pyfingerprint import PyFingerprint
import mysql.connector
from flask import Flask, Response,render_template_string

app = Flask(__name__)

shared_frame = None
frame_lock = threading.Lock()

# Khởi tạo màn hình LCD
lcd = CharLCD('PCF8574', 0x27)  # Thay '0x27' bằng địa chỉ I2C của LCD (kiểm tra bằng lệnh i2cdetect)

# Hàm kết nối MySQL
def connect_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",  # Thay bằng user MySQL của bạn
            password="100803",  # Thay bằng mật khẩu MySQL
            database="door_access"
        )
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Lỗi kết nối MySQL: {err}")
        return None

# Cấu hình GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
RELAY_PIN = 17
PIR_PIN=18
LED_PIN =25
BUZZER =23
GPIO.setup(LED_PIN,GPIO.OUT)
GPIO.setup(BUZZER,GPIO.OUT)
GPIO.setup(PIR_PIN,GPIO.IN)
GPIO.setup(RELAY_PIN, GPIO.OUT)
# Định nghĩa chân GPIO cho hàng và cột
ROW_PINS = [6, 13, 19, 26]  # Các chân cho hàng R1, R2, R3, R4
COL_PINS = [12, 16, 20, 21]  # Các chân cho cột C1, C2, C3, C4

# khai bao sender_email Reciever_Email và pass_sender 
Sender_email = "duongtuan10082003@gmail.com"
Reciever_Email ="duongtuan1008@gmail.com"
pass_sender = "vrrw tsqa aljl nbrk"
# Ngưỡng khoảng cách tối đa để coi là trùng khớp
face_recognition_threshold = 0.45  # Bạn có thể điều chỉnh ngưỡng này
# Định nghĩa mật khẩu và biến
pass_def = "12345"
mode_changePass = '*#01#'
mode_resetPass = '*#02#'
password_input = ''
key_queue = queue.Queue()
new_pass1 = [''] * 5
new_pass2 = [''] * 5
data_input = []

# định nghĩa các biến khơi tạo
prevTime = 0  # Biến để theo dõi thời gian trước đó
motion_detected_time = 0
in_num=0
doorUnlock = False  # Trạng thái mở cửa ban đầu là False
is_checking_password = False
# Khai báo từ điển để lưu thời gian nhận diện gần nhất cho mỗi người dùng
last_recognition_time = {}
# Thời gian giãn cách tối thiểu giữa các lần nhận diện (tính bằng giây)
min_recognition_interval = 10  # Ví dụ: 10 giây
# Khai báo thời gian chờ trước khi kết luận "Unknown" (ví dụ 1 giây)
delay_before_unknown = 5  # Ví dụ: 1 giây
# Bảng bàn phím 4x4
KEYPAD = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]


# Thiết lập các chân hàng là output
for row in ROW_PINS:
    GPIO.setup(row, GPIO.OUT)

# Thiết lập các chân cột là input với pull-down resistor
for col in COL_PINS:
    GPIO.setup(col, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


#------------------- xử lý dữ liệu nhập từ matrix phím ---------------------
def get_password():
    try:
        with open('password.txt', 'r') as file:
            password = file.read().strip()  # Đọc và loại bỏ khoảng trắng/thẻ xuống dòng
            return password
    except FileNotFoundError:
        print("File password.txt không tồn tại.")
        return None

# Gọi hàm lấy mật khẩu
password = get_password()

if password:
    # Xử lý mật khẩu (ví dụ: đăng nhập, kết nối API, ...)
    print(f'Mật khẩu là: {password}')
else:
    print("Không thể lấy mật khẩu")
#get dữ liệu từ bàn phím 
# Hàm kiểm tra dữ liệu đầu vào
def isBufferdata(data=[]):
    if len(data) < 5:
        return 0
    for i in range(5):
        if data[i] == '\0':
            return 0
    return 1

# Hàm ghi dữ liệu vào biến new_pass1 và new_pass2
def insertData(data1, data2):
    if len(data1) != len(data2):
        print("Lỗi: Kích thước của data1 và data2 không khớp.")
        return  # Thoát nếu kích thước không khớp
    for i in range(len(data1)):
        data1[i] = data2[i]  # Gán giá trị từ data2 vào data1

# Hàm so sánh hai danh sách dữ liệu
def compareData(data1=[], data2=[]):
    for i in range(5):
        if data1[i] != data2[i]:
            return False
    return True

# Hàm xóa dữ liệu đầu vào
def clear_data_input():
    global data_input
    data_input = []

# Hàm ghi mật khẩu mới vào EEPROM (giả lập)
def writeEpprom(new_pass):
    print(f"Ghi mật khẩu mới vào EEPROM: {new_pass}")
    # Thực hiện ghi vào EEPROM ở đây
def clear_lcd():
    lcd.clear()
    lcd.home()  # Ðua con tro ve vi trí ban d?u
    time.sleep(0.1)  


def reset_lcd_to_default():
    clear_lcd()  # Xóa nội dung trên LCD
    lcd.write_string("---CLOSEDOOR---")  # Hiển thị trạng thái mặc định "Cửa khóa"
# Hàm kiểm tra mật khẩu
def read_line(row):
    GPIO.output(row, GPIO.HIGH)  # Kích hoạt hàng hiện tại
    
    for i, col in enumerate(COL_PINS):
        if GPIO.input(col) == 1:
            key_pressed = KEYPAD[ROW_PINS.index(row)][i]  # Lấy ký tự tương ứng
            print(f"Key pressed: {key_pressed}")
            data_input.append(key_pressed)  # Thêm ký tự vào data_input
            
            # Xóa màn hình LCD trước khi cập nhật nội dung mới
            clear_lcd()
            
            # Hiển thị tiến trình nhập mật khẩu trên màn hình LCD
            lcd.write_string("Checking pass:")
            lcd.cursor_pos = (1, 0)  # Di chuyển con trỏ đến dòng thứ hai
            lcd.write_string('*' * len(data_input))  # Hiển thị dấu '*' cho mỗi ký tự được nhập
            
            time.sleep(0.3)  # Tạm dừng để tránh trùng lặp
    GPIO.output(row, GPIO.LOW)  # Tắt hàng hiện tại

# Hàm kiểm tra mật khẩu
def check_pass():
    global password_input, is_checking_password, Sender_email, pass_sender, Reciever_Email
    clear_lcd()  # Xóa màn hình LCD trước khi hiển thị thông báo
    lcd.write_string('Checking pass:')  # Hiển thị thông báo đang kiểm tra trên LCD

    while True:
        if len(data_input) < 5:  # Giả sử mật khẩu có 5 ký tự
            for row in ROW_PINS:
                read_line(row)  # Gọi hàm để đọc ký tự từ bàn phím ma trận
            time.sleep(0.1)  # Tạm dừng một chút để tránh việc lặp quá nhanh
        else:
            is_checking_password = True  # Đặt cờ là True để cho biết đang kiểm tra mật khẩu
            password_input = ''.join(data_input)

            if password_input == password:
                lcd.clear()
                lcd.write_string('---OPENDOOR---')
                time.sleep(1)  # Đợi 1 giây để hiển thị thông báo "Mật khẩu đúng!"
                print('Mật khẩu đúng!')
                log_access("User", "Password", "Mở cửa bằng mật khẩu")


                # Mở relay để mở cửa
                GPIO.output(RELAY_PIN, GPIO.HIGH)  # Kích hoạt relay (mở cửa)
                time.sleep(5)  # Giữ cửa mở trong 5 giây
                GPIO.output(RELAY_PIN, GPIO.LOW)  # Đóng cửa

                # Sau khi đóng cửa, đặt lại LCD về trạng thái mặc định
                reset_lcd_to_default()  # Gọi hàm đưa LCD về trạng thái mặc định
            elif password_input == mode_changePass:
                changePass()
            elif password_input == mode_resetPass:
                resetPass()
            else:
                lcd.clear()
                lcd.write_string('WRONG PASSWORD')  # Hiển thị thông báo lỗi
                open_buzzer(1)  # Buzzer bật 1 giây khi nhập sai mật khẩu
                print('Mật khẩu không đúng!')
                GPIO.output(RELAY_PIN, GPIO.LOW)  # Đảm bảo cửa vẫn đóng
                # Gửi email với ảnh đã chụp
                SendEmail(Sender_email, pass_sender, Reciever_Email)

            is_checking_password = False  # Đặt cờ là False sau khi kiểm tra xong
            clear_data_input()  # Xóa dữ liệu nhập sau khi kiểm tra
            time.sleep(2)  # Đợi 2 giây trước khi xóa màn hình
            reset_lcd_to_default()  # Đặt lại trạng thái màn hình về mặc định
  # Xóa màn hình sau khi hoàn thành kiểm tra

def changePass():
    global password, new_pass1, new_pass2
    clear_lcd()  # Xóa màn hình ngay khi bắt đầu
    lcd.write_string('-- Change Pass --')
    print('--- Đổi mật khẩu ---')
    time.sleep(2)
    
    clear_data_input()

    clear_lcd()  # Chỉ xóa màn hình trước khi hiển thị nội dung mới
    lcd.write_string("--- New Pass ---")

    # Nhập mật khẩu mới lần 1
    while True:
        if len(data_input) < 5:
            for row in ROW_PINS:
                read_line(row)
            time.sleep(0.1)

            # Chỉ cập nhật dấu '*' khi có sự thay đổi trong data_input
            lcd.cursor_pos = (1, 0)
            lcd.write_string('*' * len(data_input))

        if isBufferdata(data_input):  # Khi đã nhập đủ dữ liệu
            insertData(new_pass1, data_input)
            clear_data_input()  # Xóa dữ liệu nhập lần 1
            lcd.clear()  # Xóa màn hình khi hoàn thành việc nhập
            lcd.write_string("--- PASSWORD ---")
            print("---- AGAIN ----")
            break

    # Nhập lại mật khẩu lần 2
    while True:
        if len(data_input) < 5:
            for row in ROW_PINS:
                read_line(row)
            time.sleep(0.1)

            # Hiển thị tiến trình nhập lại mật khẩu lần 2
            lcd.cursor_pos = (1, 0)
            lcd.write_string('*' * len(data_input))

        if isBufferdata(data_input):  # Khi đã nhập đủ lần 2
            insertData(new_pass2, data_input)
            break

    time.sleep(1)

    # So sánh hai lần nhập mật khẩu
    if compareData(new_pass1, new_pass2):
        lcd.clear()  # Chỉ xóa khi thực sự cần hiển thị nội dung khác
        lcd.write_string("--- Success ---")
        print("--- Mật khẩu khớp ---")
        time.sleep(1)
        writeEpprom(new_pass2)
        password = ''.join(new_pass2)

        # Ghi mật khẩu mới vào file password.txt
        try:
            with open('password.txt', 'w') as file:
                file.write(password)
            print("Mật khẩu mới đã được lưu vào file.")
        except IOError:
            print("Không thể ghi mật khẩu vào file.")

        # Ghi log khi thay đổi mật khẩu
        log_access("Admin", "Change Password", "Đổi mật khẩu thành công")

        lcd.clear()  # Xóa màn hình trước khi thông báo thành công
        lcd.write_string("Đổi MK thành công")
        time.sleep(2)
def resetPass():
    global password
    clear_lcd()  # Xóa LCD trước khi hiển thị nội dung mới
    lcd.write_string('--- Reset Pass ---')  # Hiển thị "Reset Pass" trên LCD
    print('--- Reset Pass ---')
    time.sleep(2)  # Cho phép người dùng nhìn thấy thông báo trên LCD

    clear_data_input()
    
    # Bắt đầu quá trình nhập mật khẩu hiện tại để xác nhận
    clear_lcd()  # Xóa LCD trước khi hiển thị nội dung mới
    lcd.write_string("--- PassWord ---")

    while True:
        if len(data_input) < 5:  # Giả sử mật khẩu có 5 ký tự
            for row in ROW_PINS:
                read_line(row)  # Gọi hàm để đọc ký tự từ bàn phím ma trận
            time.sleep(0.1)  # Tạm dừng một chút để tránh việc lặp quá nhanh

            # Hiển thị tiến trình nhập mật khẩu hiện tại
            clear_lcd()  # Xóa màn hình trước khi cập nhật
            lcd.write_string("R1enter password")
            lcd.cursor_pos = (1, 0)  # Di chuyển con trỏ đến dòng thứ hai
            lcd.write_string('*' * len(data_input))  # Hiển thị dấu '*' đại diện cho ký tự đã nhập

        if isBufferdata(data_input):  # Kiểm tra xem người dùng đã nhập đủ 5 ký tự
            if compareData(data_input, password):  # So sánh với mật khẩu hiện tại
                clear_data_input()  # Xóa dữ liệu nhập sau khi xác nhận thành công
                clear_lcd()  # Xóa màn hình trước khi thông báo thành công
                lcd.write_string('---resetting...---')
                print('Mật khẩu đúng, sẵn sàng reset!')
                
                # Đợi 2 giây để thông báo thành công trước khi tiếp tục
                time.sleep(2)

                while True:
                    key = None  # Đặt mặc định key là None để kiểm tra
                    for row in ROW_PINS:
                        GPIO.output(row, GPIO.HIGH)
                        for i, col in enumerate(COL_PINS):
                            if GPIO.input(col) == 1:
                                key = KEYPAD[ROW_PINS.index(row)][i]
                                time.sleep(0.3)  # Tránh trùng lặp khi nhấn
                        GPIO.output(row, GPIO.LOW)

                    if key == '#':  # Khi người dùng nhấn phím '#'
                        new_default_pass = list(pass_def)  # Mật khẩu mặc định thành danh sách
                        new_password = list(password)  # Chuyển đổi mật khẩu hiện tại thành danh sách
                        insertData(new_password, new_default_pass)  # Đặt lại mật khẩu mặc định
                        clear_lcd()  # Xóa LCD trước khi hiển thị thông báo mới
                        lcd.write_string('---reset successful---')
                        print('--- Reset mật khẩu thành công ---')
                        writeEpprom(pass_def)  # Giả lập ghi vào EEPROM
                        password = ''.join(new_password)  # Chuyển đổi danh sách trở lại chuỗi

                        # Ghi mật khẩu mới vào file password.txt
                        try:
                            with open('password.txt', 'w') as file:
                                file.write(password)
                            print("Mật khẩu mới đã được lưu vào file.")
                        except IOError:
                            print("Không thể ghi mật khẩu vào file.")

                        clear_data_input()  # Xóa dữ liệu nhập
                        time.sleep(2)  # Hiển thị thông báo thành công trong 2 giây
                        clear_lcd()  # Xóa màn hình sau khi thông báo thành công
                        return  # Thoát hàm reset sau khi hoàn thành
            else:
                # Xử lý khi mật khẩu hiện tại không đúng
                clear_lcd()  # Xóa màn hình trước khi thông báo lỗi
                lcd.write_string('---ERROR---')
                print('Mật khẩu không đúng!')
                
                # Gửi email cảnh báo
                SendEmail(Sender_email, pass_sender, Reciever_Email)

                clear_data_input()  # Xóa dữ liệu nhập khi sai mật khẩu
                time.sleep(2)  # Hiển thị thông báo trong 2 giây
                clear_lcd()  # Xóa màn hình sau khi thông báo sai mật khẩu
                break  # Kết thúc nếu mật khẩu nhập sai
#--------------------------------------------------------------
try:
    radar = serial.Serial('/dev/ttyAMA3', baudrate=256000, timeout=1)  # UART Radar HLK-LD2410B
    print("✅ Kết nối cảm biến Radar HLK-LD2410B thành công!")
except Exception as e:
    print(f"❌ Lỗi kết nối cảm biến Radar: {e}")
    exit(1)
def log_motion_detected():
    conn = connect_db()
    if conn is None:
        print("⚠ Không thể kết nối MySQL, bỏ qua ghi nhật ký chuyển động.")
        return
    
    try:
        cursor = conn.cursor()
        detect_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = "INSERT INTO motion_log (detect_time, description) VALUES (%s, %s)"
        values = (detect_time, "Phát hiện chuyển động!")
        cursor.execute(sql, values)
        conn.commit()
        print(f"✅ Ghi nhật ký vào `motion_log`: {detect_time}")
    except mysql.connector.Error as err:
        print(f"❌ Lỗi MySQL khi ghi nhật ký vào `motion_log`: {err}")
    finally:
        cursor.close()
        conn.close()

def detect_motion():
    try:
        while True:
            if radar.in_waiting > 10:  # Ð?m b?o có d? d? li?u
                data = radar.read(radar.in_waiting)  # Ð?c d? li?u
                if len(data) < 10:
                    continue  # Bo qua neu du lieu quá ngan

                if data[0] == 0xF4 and data[1] == 0xF3:  # Header hop ly
                    # ?? **TH? CÁC V? TRÍ KHÁC NHAU**
                    possible_distances = [
                        int.from_bytes(data[9:11], byteorder="little"),  # V? trí 1
                        int.from_bytes(data[10:12], byteorder="little"), # V? trí 2
                        int.from_bytes(data[11:13], byteorder="little")  # V? trí 3
                    ]

                    for distance in possible_distances:
                        if 0 < distance <= 50:  
                            print(f"Phát hiện có người trong pham vi {distance} cm!")
                            GPIO.output(LED_PIN, GPIO.HIGH)  # Bat LED caanh báo
                            log_motion_detected()
                            time.sleep(2)
                            break
                        else:
                            GPIO.output(LED_PIN, GPIO.LOW)  # Tat LED n?u không có ngu?i g?n

            time.sleep(0.1)  # Chi 100ms truoc khi kiem tra tiep
    except Exception as e:
        print(f"Loi radar: {e}")

# ------------- send email khi phát hiện xâm nhập -------------
def get_latest_image_path(upload_folder):
    # Lấy danh sách các tệp trong thư mục
    image_files = [f for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))]
    
    if not image_files:
        print("Không tìm thấy ảnh nào trong thư mục uploads.")
        return None
    
    # Lấy tệp mới nhất dựa trên thời gian sửa đổi (modification time)
    latest_image = max(image_files, key=lambda x: os.path.getmtime(os.path.join(upload_folder, x)))
    
    # Trả về đường dẫn đầy đủ tới ảnh mới nhất
    return os.path.join(upload_folder, latest_image)
def SendEmail(sender, pass_sender, receiver):
    # Đường dẫn tới thư mục uploads
    upload_folder = 'uploads'

    # Lấy đường dẫn tới ảnh mới nhất
    latest_image_path = get_latest_image_path(upload_folder)

    if latest_image_path is None:
        print("Không có ảnh để gửi.")
        return

    print(f"Đang gửi email với ảnh từ: {latest_image_path}")  # Thông báo ảnh được sử dụng
    newMessage = EmailMessage()
    newMessage['Subject'] = "CANH BAO !!!"
    newMessage['From'] = sender
    newMessage['To'] = receiver
    newMessage.set_content('CANH BAO AN NINH')

    # Mở và đọc dữ liệu ảnh
    with open(latest_image_path, 'rb') as f:
        image_data = f.read()
        image_type = imghdr.what(f)
        if image_type is None:
            image_type = 'jpeg'
        image_name = os.path.basename(latest_image_path)
        newMessage.add_attachment(image_data, maintype='image', subtype=image_type, filename=image_name)

    # Gửi email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender, pass_sender)
            smtp.send_message(newMessage)
        print("Email đã được gửi với ảnh đính kèm.")
    except Exception as e:
        print(f"Không thể gửi email: {e}")
#------Kết nối cảm biến vân tay (UART: /dev/ttyS0)-------
try:
    finger = PyFingerprint('/dev/ttyS0', 57600, 0xFFFFFFFF, 0x00000000)
    if not finger.verifyPassword():
        raise ValueError("Không thể xác minh mật khẩu cảm biến vân tay!")
    print("✅ Cảm biến vân tay kết nối thành công!")
except Exception as e:
    print(f"❌ Lỗi cảm biến vân tay: {e}")
    exit(1)


def load_fingerprint_data(user_name):
    """Tải dữ liệu vân tay từ file"""
    file_path = f"dataset/{user_name}/fingerprint_{user_name}.dat"
    
    try:
        with open(file_path, "rb") as f:
            fingerprint_data = pickle.load(f)
        return fingerprint_data
    except (FileNotFoundError, pickle.UnpicklingError):
        print(f"❌ Không tìm thấy hoặc lỗi dữ liệu vân tay cho {user_name}")
        return None

def authenticate_fingerprint(user_name):
    """Quét vân tay và xác thực"""
    print("📌 Vui lòng đặt vân tay...")
    clear_data_input()
    lcd.write_string("Place Finger")

    start_time = time.time()
    while time.time() - start_time < 55:  # Chỉ cho phép quét trong 10 giây
        if finger.readImage():
            finger.convertImage(0x01)
            scanned_data = finger.downloadCharacteristics()
            stored_data = load_fingerprint_data(user_name)

            if stored_data:
                finger.convertImage(0x02)  # Chuy?n m?u vân tay quét vào b? nh? 0x02
                match_score = finger.compareCharacteristics()
                
                if match_score >= 50:  # Ngu?ng so sánh (50-100 là t?t)
                    print(f" Xác thưc vân tay thành công! Mơ cửa cho {user_name}")
                    clear_data_input()
                    lcd.write_string("Fingerprint OK!")
                    log_access(user_name, "Face", f"{user_name} đã mở cửa bằng nhận diện khuôn mặt")
                    return True
                else:
                    print(" Vân tay không hop lệ!")
                    clear_data_input()
                    lcd.write_string("Fingerprint Fail")
                    open_buzzer(2)
                    return False


    print("⏳ Hết thời gian quét vân tay!")
    clear_data_input()
    lcd.write_string("Time out!")
    return False  # Nếu quá 10s mà chưa quét, trả về False

#-------------- hàm chính -------------------
print("Cửa khóa")
GPIO.output(RELAY_PIN, GPIO.LOW)

# Khởi tạo camera với Picamera2
# Camera cho nhận diện khuôn mặt
picam2 = Picamera2()
face_config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(face_config)
picam2.start()

# Tải mô hình Haar Cascade để nhận diện khuôn mặt
haarcascade_path = '/home/Tun/Desktop/END/haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(haarcascade_path)

if face_cascade.empty():
    print("Không thể tải mô hình Haar Cascade.")
    exit()

# Đọc mô hình đã huấn luyện từ tệp
try:
    with open('face_recognition_model.pkl', 'rb') as model_file:
        clf = pickle.load(model_file)
except FileNotFoundError:
    print("Tệp mô hình nhận diện khuôn mặt không tồn tại.")
    exit()

# Đọc dữ liệu khuôn mặt đã lưu
try:
    with open('dataset_faces.dat', 'rb') as file:
        all_face_encodings = pickle.load(file)
except FileNotFoundError:
    print("Tệp dữ liệu khuôn mặt không tồn tại.")
    exit()

# Chuyển đổi từ điển thành danh sách các encoding và ID
known_face_encodings = list(all_face_encodings.values())
known_face_ids = list(all_face_encodings.keys())
# Hàm kiểm tra chuyển động
# Định nghĩa bộ mã hóa video và kích thước khung hình
fourcc = cv2.VideoWriter_fourcc(*'mp4v')

# Tạo thư mục 'uploads' nếu chưa tồn tại
upload_folder = 'uploads'
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)
# Hàm d? ch?p và luu ?nh trong lu?ng riêng
def capture_and_save_image(frame, name):
    output_dir = 'uploads'  # Bạn có thể dùng biến 'upload_folder' nếu đã định nghĩa trước đó
    # T?o tên t?p v?i d?nh d?ng "Name_YYYY-MM-DD_HH-MM-SS.jpg"
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    img_filename = f"{output_dir}/{name}_{timestamp}.jpg"
    cv2.imwrite(img_filename, frame)
    print(f"anh dã duoc luu: {img_filename}")
    return img_filename  # Tr? v? du?ng d?n ?nh
def delayed_email_if_unknown(sender, pass_sender, receiver):
    time.sleep(10)  # Chờ 10 giây
    print("10 giây đã qua, gửi email với ảnh mới nhất.")
    SendEmail(sender, pass_sender, receiver)

#ghi lại thơi gian mở cửa 
def log_access(user_name, access_method, event_description):
    conn = connect_db()
    if conn is None:
        print("⚠ Không thể kết nối MySQL, bỏ qua ghi nhật ký truy cập.")
        return
    
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO access_log (user_name, access_method, event_description, timestamp) VALUES (%s, %s, %s, NOW())"
        values = (user_name, access_method, event_description)
        cursor.execute(sql, values)
        conn.commit()
        print(f"✅ Ghi nhật ký vào `access_log`: {user_name} - {access_method}")
    except mysql.connector.Error as err:
        print(f"❌ Lỗi MySQL khi ghi nhật ký vào `access_log`: {err}")
    finally:
        cursor.close()
        conn.close()

# Hàm mở khóa cửa
def mo_khoa_cua():
    print("Mở khóa cửa...")
    GPIO.output(RELAY_PIN, GPIO.HIGH)  # Kích hoạt rơ-le
    time.sleep(5)  # Mở trong 5 giây (có thể tùy chỉnh)
    khoa_cua()  # Sau đó khóa cửa lại

# Hàm khóa cửa
def khoa_cua():
    print("Khóa cửa lại.")
    GPIO.output(RELAY_PIN, GPIO.LOW)  # Đưa rơ-le về trạng thái không kích hoạt

# Hàm sử dụng để kiểm tra cửa đã mở bao lâu và cần khóa lại
def delay_khoa_cua(delay_time):
    print(f"Đợi {delay_time} giây trước khi khóa cửa...")
    time.sleep(delay_time)
    khoa_cua()
def check_face_recognition(face_encoding):
    distances = face_recognition.face_distance(known_face_encodings, face_encoding)
    best_match_index = np.argmin(distances)
    
    if distances[best_match_index] < face_recognition_threshold:
        return known_face_ids[best_match_index]  # Trả về ID nếu khớp
    else:
        return None  # Trả về None nếu không khớp
# Sửa đổi vòng lặp nhận diện khuôn mặt
def open_buzzer(thời_gian=1):
    GPIO.output(BUZZER, GPIO.HIGH)  # Bật buzzer
    time.sleep(thời_gian)           # Giữ buzzer trong khoảng thời gian nhất định
    GPIO.output(BUZZER, GPIO.LOW)    # Tắt buzzer
def recognize_faces():
    global doorUnlock, is_checking_password, prevTime, last_recognized_face, last_recognition_time
    global shared_frame

    # Khởi tạo cờ unknown_timeout_flag
    unknown_timeout_flag = False
    
    # Sửa đổi vòng lặp nhận diện khuôn mặt
    while True:
        # Chụp frame từ Picamera2
        frame = picam2.capture_array()
           # 🔒 Ghi frame để Flask stream
        with frame_lock:
            shared_frame = frame.copy()
        # Chuyển đổi frame sang định dạng BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Chuyển frame sang ảnh xám để nhận diện khuôn mặt
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # Phát hiện khuôn mặt trong ảnh
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) > 0:
            for (x, y, w, h) in faces:
                cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), (255, 0, 0), 2)
                
                # Cắt khuôn mặt từ frame
                face_image = frame[y:y + h, x:x + w]
                face_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                
                # Trích xuất đặc trưng khuôn mặt
                face_encoding = face_recognition.face_encodings(face_rgb)
                
                if len(face_encoding) > 0:
                    name = check_face_recognition(face_encoding[0])
                    
                    if name:
                        # Nếu nhận diện được người dùng
                        unknown_timeout_flag = False  # Đặt lại cờ nếu nhận diện đúng người dùng
                        current_time = time.time()
                        if name not in last_recognition_time or (current_time - last_recognition_time[name]) > min_recognition_interval:
                            print(f"✅ Nhận diện khuôn mặt thành công: {name}")
                            last_recognition_time[name] = current_time
                            
                            # Chụp và lưu ảnh
                            img_filename = capture_and_save_image(frame_bgr, name)

                            # 👉 Hiển thị trên LCD yêu cầu quét vân tay
                            clear_data_input()
                            lcd.write_string(f"Hello {name}!")
                            lcd.cursor_pos = (1, 0)
                            lcd.write_string("Scan Finger...")

                            # Cho phép quét vân tay trong vòng 10s
                            start_time = time.time()
                            while time.time() - start_time < 10:
                                if authenticate_fingerprint(name):  # Nếu vân tay đúng thì mở cửa
                                    print(f"🔓 Mở khóa cửa cho {name}")
                                    clear_data_input()
                                    lcd.write_string("Door Opened!")
                                    threading.Thread(target=mo_khoa_cua).start()
                                    time.sleep(2)
                                    clear_data_input()
                                    lcd.write_string("Scan Face")
                                    break
                            else:
                                # Nếu quá 10s mà không quét vân tay, yêu cầu quét lại từ đầu
                                print("⏳ Quá thời gian quét vân tay, quét lại khuôn mặt!")
                                clear_data_input()
                                lcd.write_string("Time out!")
                                time.sleep(2)
                                clear_data_input()
                                lcd.write_string("Scan Face")

                    else:
                        # Đợi trước khi kết luận là "Unknown"
                        if not unknown_timeout_flag:
                            start_unknown_time = time.time()
                            unknown_timeout_flag = True  # Đặt cờ để bắt đầu đợi
                        
                        elapsed_time = time.time() - start_unknown_time
                        
                        # Đợi đến khi thời gian đã trôi qua để xác định là "Unknown"
                        if elapsed_time >= delay_before_unknown:
                            name = check_face_recognition(face_encoding[0])
                            if not name:
                                name = "Unknown"
                                current_time = time.time()
                                if "Unknown" not in last_recognition_time or (current_time - last_recognition_time["Unknown"]) > min_recognition_interval:
                                    last_recognition_time["Unknown"] = current_time
                                    threading.Thread(target=khoa_cua).start()
                                    open_buzzer(1)
                                    # Chụp và lưu ảnh cho người không xác định
                                    img_filename = capture_and_save_image(frame_bgr, name)
                                    threading.Thread(target=SendEmail, args=(Sender_email, pass_sender, Reciever_Email)).start()
                    
                    # Hiển thị ID trên khung hình
                    cv2.putText(frame_bgr, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        cv2.imshow("Camera - Face Detection and Recognition", frame_bgr)
        cv2.waitKey(1)

        
        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
def gen_frames():
    global shared_frame
    while True:
        with frame_lock:
            if shared_frame is None:
                continue
            frame = shared_frame.copy()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template_string("""
    <!doctype html>
    <html>
        <head>
            <title>Live Stream</title>
        </head>
        <body>
            <h1>Xem camera trực tiếp</h1>
            <img src="/video" width="800" height="600">
        </body>
    </html>
    """)

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    print("✅ Flask server đang chạy trên http://<IP của bạn>:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()
face_thread = threading.Thread(target=recognize_faces)
password_thread = threading.Thread(target=check_pass)
motion_thread = threading.Thread(target=detect_motion)

# Khởi động luồng xử lý cảm biến nghiêng

# Đảm bảo các luồng khác vẫn hoạt động song song
face_thread.start()
password_thread.start()
motion_thread.start()
cv2.imshow("Camera - Face Detection and Recognition", frame_bgr)
cv2.waitKey(1)
picam2.stop()

  # Dừng camera
GPIO.output(RELAY_PIN, GPIO.LOW)  # Đảm bảo cửa khóa khi dừng camera
cv2.destroyAllWindows()