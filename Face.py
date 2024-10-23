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
from RPLCD.i2c import CharLCD

# Khởi tạo màn hình LCD
lcd = CharLCD('PCF8574', 0x27)  # Thay '0x27' bằng địa chỉ I2C của LCD (kiểm tra bằng lệnh i2cdetect)


# Cấu hình GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
TILT_PIN =24
RELAY_PIN = 17
PIR_PIN=18
GPIO.setup(PIR_PIN,GPIO.IN)
GPIO.setup(TILT_PIN,GPIO.IN)
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
    #"""Hàm để xóa nội dung trên màn hình LCD"""
    lcd.clear()
    lcd.home()  # Đưa con trỏ về vị trí bắt đầu

# Hàm đọc từng dòng của bàn phím
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
            lcd.write_string("Nhap mat khau:")
            lcd.cursor_pos = (1, 0)  # Di chuyển con trỏ đến dòng thứ hai
            lcd.write_string('*' * len(data_input))  # Hiển thị dấu '*' cho mỗi ký tự được nhập
            
            time.sleep(0.3)  # Tạm dừng để tránh trùng lặp
    GPIO.output(row, GPIO.LOW)  # Tắt hàng hiện tại

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
            lcd.write_string("Nhap mat khau:")
            lcd.cursor_pos = (1, 0)  # Di chuyển con trỏ đến dòng thứ hai
            lcd.write_string('*' * len(data_input))  # Hiển thị dấu '*' cho mỗi ký tự được nhập
            
            time.sleep(0.3)  # Tạm dừng để tránh trùng lặp
    GPIO.output(row, GPIO.LOW)  # Tắt hàng hiện tại

# Hàm kiểm tra mật khẩu
def check_pass():
    global password_input, is_checking_password, Sender_email, pass_sender, Reciever_Email
    clear_lcd()  # Xóa màn hình LCD trước khi hiển thị thông báo
    lcd.write_string('Nhập mật khẩu:')  # Hiển thị thông báo trên LCD
    print(f'Dữ liệu đầu vào: {data_input}')
    
    while True:
        if len(data_input) < 5:  # Giả sử mật khẩu có 5 ký tự
            for row in ROW_PINS:
                read_line(row)  # Gọi hàm để đọc ký tự từ bàn phím ma trận
            time.sleep(0.1)  # Tạm dừng một chút để tránh việc lặp quá nhanh
        else:
            is_checking_password = True  # Đặt cờ là True để cho biết đang kiểm tra mật khẩu
            password_input = ''.join(data_input)

            clear_lcd()  # Xóa màn hình LCD trước khi hiển thị thông báo mới
            if password_input == password:
                lcd.write_string('Mật khẩu đúng!')  # Hiển thị thông báo
                print('Mật khẩu đúng!')
                log_event_to_text_file("Mở cửa bằng mật khẩu")
                GPIO.output(RELAY_PIN, GPIO.HIGH)  # Kích hoạt relay
                time.sleep(5)  # Giữ cửa mở trong 5 giây
                GPIO.output(RELAY_PIN, GPIO.LOW)  # Đóng cửa

            elif password_input == mode_changePass:
                changePass()
            elif password_input == mode_resetPass:
                resetPass()
            else:
                lcd.write_string('Mật khẩu không đúng!')  # Hiển thị thông báo lỗi
                print('Mật khẩu không đúng!')
                GPIO.output(RELAY_PIN, GPIO.LOW)  # Tắt relay
                # Gửi email với ảnh đã chụp
                SendEmail(Sender_email, pass_sender, Reciever_Email) 
                
            is_checking_password = False  # Đặt cờ là False sau khi kiểm tra xong
            clear_data_input()  # Xóa dữ liệu nhập sau khi kiểm tra
            time.sleep(2)  # Đợi 2 giây trước khi xóa màn hình
            clear_lcd()  # Xóa màn hình sau khi kiểm tra

def changePass():
    global password, new_pass1, new_pass2
    clear_lcd()
    lcd.write_string('--- Đổi mật khẩu ---')
    print('--- Đổi mật khẩu ---')
    time.sleep(2)
    
    clear_data_input()

    clear_lcd()
    lcd.write_string("Nhập MK mới:")
    
    while True:
        if len(data_input) < 5:
            for row in ROW_PINS:
                read_line(row)
            time.sleep(0.1)
            clear_lcd()
            lcd.write_string("Nhập MK mới:")
            lcd.cursor_pos = (1, 0)
            lcd.write_string('*' * len(data_input))

        if isBufferdata(data_input):
            insertData(new_pass1, data_input)
            clear_data_input()
            clear_lcd()
            lcd.write_string("--- Nhập lại ---")
            print("--- Nhập lại mật khẩu ---")
            break

    while True:
        if len(data_input) < 5:
            for row in ROW_PINS:
                read_line(row)
            time.sleep(0.1)
            clear_lcd()
            lcd.write_string("Nhập lại MK:")
            lcd.cursor_pos = (1, 0)
            lcd.write_string('*' * len(data_input))

        if isBufferdata(data_input):
            insertData(new_pass2, data_input)
            break

    time.sleep(1)

    if compareData(new_pass1, new_pass2):
        clear_lcd()
        lcd.write_string("--- Mật khẩu khớp ---")
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
        log_event_to_text_file("Đổi mật khẩu thành công")

        clear_lcd()
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
    lcd.write_string("Nhập MK hiện tại:")

    while True:
        if len(data_input) < 5:  # Giả sử mật khẩu có 5 ký tự
            for row in ROW_PINS:
                read_line(row)  # Gọi hàm để đọc ký tự từ bàn phím ma trận
            time.sleep(0.1)  # Tạm dừng một chút để tránh việc lặp quá nhanh

            # Hiển thị tiến trình nhập mật khẩu hiện tại
            clear_lcd()  # Xóa màn hình trước khi cập nhật
            lcd.write_string("Nhập MK hiện tại:")
            lcd.cursor_pos = (1, 0)  # Di chuyển con trỏ đến dòng thứ hai
            lcd.write_string('*' * len(data_input))  # Hiển thị dấu '*' đại diện cho ký tự đã nhập

        if isBufferdata(data_input):  # Kiểm tra xem người dùng đã nhập đủ 5 ký tự
            if compareData(data_input, password):  # So sánh với mật khẩu hiện tại
                clear_data_input()  # Xóa dữ liệu nhập sau khi xác nhận thành công
                clear_lcd()  # Xóa màn hình trước khi thông báo thành công
                lcd.write_string('MK đúng, đang reset...')
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
                        lcd.write_string('Reset MK thành công')
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
                lcd.write_string('MK sai!')
                print('Mật khẩu không đúng!')
                
                # Gửi email cảnh báo
                SendEmail(Sender_email, pass_sender, Reciever_Email)

                clear_data_input()  # Xóa dữ liệu nhập khi sai mật khẩu
                time.sleep(2)  # Hiển thị thông báo trong 2 giây
                clear_lcd()  # Xóa màn hình sau khi thông báo sai mật khẩu
                break  # Kết thúc nếu mật khẩu nhập sai
def changePass():
    global password, new_pass1, new_pass2
    clear_lcd()  # Xóa màn hình LCD trước khi hiển thị nội dung mới
    lcd.write_string('--- Doi mat khau ---')  # Hiển thị thông báo đổi mật khẩu
    print('--- Đổi mật khẩu ---')
    time.sleep(2)
    
    clear_data_input()
    
    # Nhập mật khẩu mới lần 1
    clear_lcd()  # Xóa màn hình LCD trước khi yêu cầu nhập mật khẩu mới
    lcd.write_string("Nhap MK moi:")
    
    while True:
        if len(data_input) < 5:  # Giả sử mật khẩu có 5 ký tự
            for row in ROW_PINS:
                read_line(row)  # Gọi hàm để đọc ký tự từ bàn phím ma trận
            time.sleep(0.1)  # Tạm dừng một chút để tránh việc lặp quá nhanh
            
            # Hiển thị tiến trình nhập mật khẩu trên LCD
            clear_lcd()  # Xóa màn hình trước khi cập nhật
            lcd.write_string("Nhap MK moi:")
            lcd.cursor_pos = (1, 0)  # Di chuyển con trỏ đến dòng thứ hai
            lcd.write_string('*' * len(data_input))  # Hiển thị dấu '*' đại diện cho ký tự đã nhập

        if isBufferdata(data_input):
            insertData(new_pass1, data_input)
            clear_data_input()
            clear_lcd()  # Xóa màn hình LCD trước khi yêu cầu nhập lại
            lcd.write_string("--- Nhap lai ---")
            print("--- Nhập lại mật khẩu ---")
            break

    # Nhập mật khẩu mới lần 2 để xác nhận
    while True:
        if len(data_input) < 5:  # Giả sử mật khẩu có 5 ký tự
            for row in ROW_PINS:
                read_line(row)  # Gọi hàm để đọc ký tự từ bàn phím ma trận
            time.sleep(0.1)  # Tạm dừng một chút để tránh việc lặp quá nhanh
            
            # Hiển thị tiến trình nhập mật khẩu trên LCD
            clear_lcd()  # Xóa màn hình trước khi cập nhật
            lcd.write_string("Nhap lai MK:")
            lcd.cursor_pos = (1, 0)
            lcd.write_string('*' * len(data_input))  # Hiển thị dấu '*' đại diện cho ký tự đã nhập

        if isBufferdata(data_input):
            insertData(new_pass2, data_input)
            break

    time.sleep(1)
    # Kiểm tra xem mật khẩu nhập lại có khớp với mật khẩu ban đầu không
    if compareData(new_pass1, new_pass2):
        clear_lcd()  # Xóa màn hình trước khi thông báo kết quả
        lcd.write_string("--- Mat khau khop ---")
        print("--- Mật khẩu khớp ---")
        time.sleep(1)
        writeEpprom(new_pass2)
        password = ''.join(new_pass2)  # Gán mật khẩu mới

    # Ghi mật khẩu mới vào file password.txt
    try:
        with open('password.txt', 'w') as file:
            file.write(password)
        print("Mật khẩu mới đã được lưu vào file.")
    except IOError:
        print("Không thể ghi mật khẩu vào file.")

    clear_lcd()  # Xóa màn hình trước khi thông báo thành công
    lcd.write_string("Doi MK thanh cong")
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
    lcd.write_string("Nhap MK hien tai:")

    while True:
        if len(data_input) < 5:  # Giả sử mật khẩu có 5 ký tự
            for row in ROW_PINS:
                read_line(row)  # Gọi hàm để đọc ký tự từ bàn phím ma trận
            time.sleep(0.1)  # Tạm dừng một chút để tránh việc lặp quá nhanh

            # Hiển thị tiến trình nhập mật khẩu hiện tại
            clear_lcd()  # Xóa màn hình trước khi cập nhật
            lcd.write_string("Nhap MK hien tai:")
            lcd.cursor_pos = (1, 0)  # Di chuyển con trỏ đến dòng thứ hai
            lcd.write_string('*' * len(data_input))  # Hiển thị dấu '*' đại diện cho ký tự đã nhập

        if isBufferdata(data_input):  # Kiểm tra xem người dùng đã nhập đủ 5 ký tự
            if compareData(data_input, password):  # So sánh với mật khẩu hiện tại
                clear_data_input()  # Xóa dữ liệu nhập sau khi xác nhận thành công
                clear_lcd()  # Xóa màn hình trước khi thông báo thành công
                lcd.write_string('MK dung, dang reset...')
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
                        lcd.write_string('Reset MK thanh cong')
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
                        return  # Thoát hàm reset sau khi hoàn thành
            else:
                # Xử lý khi mật khẩu hiện tại không đúng
                clear_lcd()  # Xóa màn hình trước khi thông báo lỗi
                lcd.write_string('MK sai!')
                print('Mật khẩu không đúng!')
                
                # Gửi email cảnh báo
                SendEmail(Sender_email, pass_sender, Reciever_Email)

                clear_data_input()  # Xóa dữ liệu nhập khi sai mật khẩu
                time.sleep(2)  # Hiển thị thông báo trong 2 giây
                break  # Kết thúc nếu mật khẩu nhập sai


# -------------xử lý dữ liệu từ cảm biến nghiêng --------------
def Tilt_Handle():
    global is_checking_password,Sender_email,Reciever_Email,pass_sender
    tilt_sensor = GPIO.input(TILT_PIN)  # Đọc giá trị từ cảm biến nghiêng
    
    # Kiểm tra nếu không đang kiểm tra mật khẩu và cảm biến ở trạng thái kích hoạt
    if not is_checking_password and tilt_sensor:  
        global i
        i += 1  # Tăng biến đếm ảnh
        
        # Tạo đường dẫn cho ảnh
        image_path = f"/home/Tun/Desktop/FacePass2/image/image_{i}.jpg"
        
        picam2.capture(image_path)  # Chụp ảnh và lưu vào đường dẫn đã tạo
        print('A photo has been taken')  # In thông báo đã chụp ảnh
        
        time.sleep(10)  # Chờ 10 giây trước khi có thể chụp tiếp
        
         

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

#-------------- hàm chính -------------------
print("Cửa khóa")
GPIO.output(RELAY_PIN, GPIO.LOW)

# Khởi tạo camera với Picamera2
picam2 = Picamera2()
picam2.start()  # Bật camera ngay lập tức

# Tải mô hình Haar Cascade để nhận diện khuôn mặt
haarcascade_path = '/home/Tun/Desktop/FacePass2/haarcascade_frontalface_default.xml'
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
    print(f"?nh dã du?c luu: {img_filename}")
    return img_filename  # Tr? v? du?ng d?n ?nh
def delayed_email_if_unknown(sender, pass_sender, receiver):
    time.sleep(10)  # Chờ 10 giây
    print("10 giây đã qua, gửi email với ảnh mới nhất.")
    SendEmail(sender, pass_sender, receiver)

#ghi lại thơi gian mở cửa 
def log_event_to_text_file(event_description):
    log_file_path = 'door_access_log.txt'  # File lưu log
    with open(log_file_path, "a") as log_file:
        log_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"{log_time} - {event_description}\n")

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

# Sử dụng các hàm này trong quá trình nhận diện khuôn mặt
import cv2
import numpy as np
import face_recognition
import threading
import time

def recognize_faces():
    global doorUnlock, is_checking_password, prevTime, se, last_recognized_face, last_recognition_time

    # Biến để lưu khuôn mặt đã nhận diện trước đó và thời gian nhận diện
    last_recognized_face = None
    last_recognition_time = 0  # Lưu thời gian nhận diện trước đó

    while True:
        # Chụp frame từ Picamera2
        frame = picam2.capture_array()

        # Chuyển đổi frame sang định dạng BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Hiển thị khung hình ngay lập tức
        cv2.imshow("Camera - Face Detection and Recognition", frame_bgr)

        # Lấy thời gian hiện tại
        current_time = time.time()

        # Kiểm tra nếu đã qua 10 giây từ lần nhận diện trước
        if current_time - last_recognition_time >= 10:
            # Chuyển frame sang ảnh xám để nhận diện khuôn mặt
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

            # Phát hiện khuôn mặt trong ảnh
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(faces) == 0:
                print("Không có khuôn mặt nào được phát hiện.")
            else:
                print(f"Phát hiện {len(faces)} khuôn mặt.")

                for (x, y, w, h) in faces:
                    # Vẽ hình chữ nhật quanh khuôn mặt
                    cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), (255, 0, 0), 2)

                    # Cắt khuôn mặt từ frame
                    face_image = frame_bgr[y:y + h, x:x + w]
                    face_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)

                    # Trích xuất đặc trưng khuôn mặt
                    face_encoding = face_recognition.face_encodings(face_rgb)

                    if len(face_encoding) == 0:
                        print("Không trích xuất được đặc trưng khuôn mặt.")
                    else:
                        print("Trích xuất đặc trưng khuôn mặt thành công.")
                        
                        # So sánh với các encoding đã lưu
                        distances = face_recognition.face_distance(known_face_encodings, face_encoding[0])
                        best_match_index = np.argmin(distances)  # Lấy chỉ số của khoảng cách nhỏ nhất

                        # Kiểm tra xem khoảng cách có nhỏ hơn ngưỡng không
                        if distances[best_match_index] < face_recognition_threshold:
                            name = known_face_ids[best_match_index]
                            print(f"Mở khóa cửa cho người dùng: {name}")
                            log_event_to_text_file(f"Mở cửa cho người dùng ID: {name}")
                            # Gọi hàm mở khóa cửa
                            mo_khoa_cua()

                            # Kiểm tra nếu người nhận diện trước đó không phải là cùng người
                            if last_recognized_face != name:
                                # Nếu là khuôn mặt mới hoặc không trùng, gửi email và lưu khuôn mặt mới
                                threading.Thread(target=delayed_email_if_unknown, args=(Sender_email, pass_sender, Reciever_Email)).start()
                                last_recognized_face = name  # Cập nhật khuôn mặt nhận diện trước đó
                                print(f"Gửi email cho người dùng: {name}")
                            else:
                                print(f"Khuôn mặt {name} đã nhận diện trước đó, không gửi email lại.")
                        else:
                            # Nếu không nhận diện được thì coi là Unknown
                            name = "Unknown"
                            img_filename = capture_and_save_image(frame_bgr, name)  # Lưu ảnh người không xác định
                            print(f"Người không xác định, gửi email với ảnh: {img_filename}")
                            threading.Thread(target=SendEmail, args=(Sender_email, pass_sender, Reciever_Email)).start()
                            last_recognized_face = None  # Đặt lại vì đây là người lạ

                    # Cập nhật thời gian nhận diện
                    last_recognition_time = current_time

        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


face_thread = threading.Thread(target=recognize_faces)
password_thread = threading.Thread(target=check_pass)

password_thread.start()
face_thread.start()

cv2.imshow("Camera - Face Detection and Recognition", frame_bgr)
cv2.waitKey(1)
picam2.stop()  # Dừng camera
GPIO.output(RELAY_PIN, GPIO.LOW)  # Đảm bảo cửa khóa khi dừng camera
cv2.destroyAllWindows()