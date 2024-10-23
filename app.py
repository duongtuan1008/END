from flask import Flask, render_template,jsonify, request, redirect, url_for, flash, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
import os
import shutil
from datetime import datetime
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Gán giá trị của UPLOAD_FOLDER vào app.config
PASSWORD_FILE = 'password.txt'
LOG_FILE = 'door_access_log.txt'  # Bạn có thể thay đổi tên file và đường dẫn nếu cần
# Tạo thư mục uploads nếu chưa tồn tại
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)
def get_range(request):
    range_header = request.headers.get('Range', None)
    if range_header:
        range_value = range_header.split('=')[1]
        byte_range = range_value.split('-')
        return int(byte_range[0]), int(byte_range[1]) if byte_range[1] else None
    return None
# Định nghĩa filter datetimeformat
@app.route('/dataset/<path:filename>')
def serve_dataset_file(filename):
    return send_from_directory('dataset', filename)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    return datetime.fromtimestamp(value).strftime(format)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    folder_path = db.Column(db.String(200), nullable=False)

# Hàm đồng bộ người dùng từ thư mục dataset vào cơ sở dữ liệu
def sync_users_from_dataset():
    dataset_dir = os.path.join(os.getcwd(), 'dataset')

    # Duyệt qua tất cả các thư mục con trong dataset
    for user_folder in os.listdir(dataset_dir):
        folder_path = os.path.join(dataset_dir, user_folder)

        if os.path.isdir(folder_path):
            user_in_db = User.query.filter_by(name=user_folder).first()
            if not user_in_db:
                new_user = User(name=user_folder, folder_path=folder_path)
                db.session.add(new_user)
    
    db.session.commit()

# Thêm người dùng mới
@app.route('/add', methods=['POST'])
def add_user():
    if request.method == 'POST':
        name = request.form['username']
        images = request.files.getlist('user-image')

        folder_path = os.path.join('dataset', name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        for image in images:
            image_path = os.path.join(folder_path, image.filename)
            image.save(image_path)

        new_user = User(name=name, folder_path=folder_path)
        db.session.add(new_user)
        db.session.commit()

        flash('Thêm người dùng thành công!', 'success')
        return redirect(url_for('index'))

# Sửa thông tin người dùng
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        new_name = request.form['name']
        new_images = request.files.getlist('new_images')
        replace_images = request.files.getlist('replace_images')

        if not any(image.filename != '' for image in new_images) and not any(image.filename != '' for image in replace_images):
            flash('Vui lòng chọn ảnh để cập nhật.', 'danger')
            return redirect(url_for('edit_user', id=id))

        if any(image.filename != '' for image in new_images) and any(image.filename != '' for image in replace_images):
            flash('Chỉ được thêm ảnh mới hoặc thay thế toàn bộ ảnh, không được thực hiện cả hai cùng lúc.', 'danger')
            return redirect(url_for('edit_user', id=id))

        old_folder_path = user.folder_path
        new_folder_path = os.path.join('dataset', new_name)
        if new_name != user.name:
            os.rename(old_folder_path, new_folder_path)
            user.name = new_name
            user.folder_path = new_folder_path

        if replace_images and any(image.filename != '' for image in replace_images):
            for image_file in os.listdir(new_folder_path):
                image_path = os.path.join(new_folder_path, image_file)
                if os.path.isfile(image_path) and image_file.lower().endswith(('jpg', 'jpeg', 'png')):
                    os.remove(image_path)

            for image in replace_images:
                image_path = os.path.join(new_folder_path, image.filename)
                image.save(image_path)
            flash('Thay thế toàn bộ ảnh thành công!', 'success')

        if new_images and any(image.filename != '' for image in new_images):
            for image in new_images:
                image_path = os.path.join(new_folder_path, image.filename)
                if os.path.exists(image_path):
                    filename, extension = os.path.splitext(image.filename)
                    counter = 1
                    while os.path.exists(image_path):
                        new_filename = f"{filename}_{counter}{extension}"
                        image_path = os.path.join(new_folder_path, new_filename)
                        counter += 1
                image.save(image_path)
            flash('Thêm ảnh mới thành công!', 'success')

        db.session.commit()

        flash('Sửa thông tin người dùng thành công!', 'success')
        return redirect(url_for('edit_user', id=id))

    image_files = os.listdir(user.folder_path)
    image_files = [f for f in image_files if os.path.isfile(os.path.join(user.folder_path, f)) and f.lower().endswith(('jpg', 'jpeg', 'png'))]

    return render_template('edit.html', user=user, image_files=image_files)

# Xóa người dùng
@app.route('/delete/<int:id>')
def delete_user(id):
    user = User.query.get_or_404(id)
    try:
        if os.path.exists(user.folder_path):
            shutil.rmtree(user.folder_path)

        db.session.delete(user)
        db.session.commit()

        flash('Xóa người dùng thành công!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Có lỗi xảy ra: {e}', 'danger')
        return redirect(url_for('index'))

# Quản lý video
# Route để xóa hình ảnh
@app.route('/delete_image/<int:userId>/<imageName>', methods=['POST'])
def delete_image(userId, imageName):
    user = User.query.get_or_404(userId)
    image_path = os.path.join(user.folder_path, imageName)

    if os.path.exists(image_path):
        os.remove(image_path)  # Xóa ảnh
        flash('Ảnh đã được xóa thành công!', 'success')
    else:
        flash('Không tìm thấy ảnh để xóa.', 'danger')

    return redirect(url_for('edit_user', id=userId))

# Lấy danh sách các ảnh từ thư mục upload
def get_images():
    image_files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_files.append({
                'filename': filename,
                'upload_time': datetime.fromtimestamp(os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], filename)))
            })
    # Sắp xếp ảnh theo thời gian tải lên mới nhất trước
    image_files.sort(key=lambda x: x['upload_time'], reverse=True)
    return image_files

# Route hiển thị danh sách ảnh
@app.route('/images')
def images():
    images = get_images()
    return render_template('images.html', images=images)
#-------------------------------------------------------
# Hàm đọc mật khẩu từ file
def read_password():
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, 'r') as file:
            return file.read().strip()
    return None

# Hàm ghi mật khẩu vào file
def write_password(password):
    with open(PASSWORD_FILE, 'w') as file:
        file.write(password)

# Route để nhận mật khẩu từ JavaScript và lưu vào file
@app.route('/update-password', methods=['POST'])
def update_password():
    data = request.get_json()  # Nhận dữ liệu JSON từ yêu cầu
    password = data.get('password')  # Lấy mật khẩu từ dữ liệu JSON

    # Kiểm tra mật khẩu có độ dài là 5 ký tự
    if password and len(password) == 5:
        try:
            write_password(password)  # Ghi mật khẩu vào file
            return jsonify(success=True)  # Trả về JSON báo thành công
        except Exception as e:
            return jsonify(success=False, error=str(e))  # Trả về lỗi nếu có vấn đề
    else:
        return jsonify(success=False, error='Mật khẩu phải có 5 ký tự!')

# Route quản lý mật khẩu hiển thị bằng HTML form
@app.route('/password', methods=['GET', 'POST'])
def manage_password():
    # Đọc mật khẩu hiện tại
    current_password = read_password()

    # Xử lý cập nhật mật khẩu
    if request.method == 'POST':
        new_password = request.form['new_password']
        if new_password and len(new_password) == 5:
            write_password(new_password)
            flash('Mật khẩu đã được cập nhật thành công!', 'success')
            return redirect(url_for('manage_password'))
        else:
            flash('Mật khẩu phải có độ dài là 5 ký tự.', 'danger')

    # Đọc nội dung log từ file
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as file:
            log_lines = file.readlines()
    else:
        log_lines = []

    # Trả về trang pass.html với cả mật khẩu và nội dung log
    return render_template('pass.html', current_password=current_password, log_lines=log_lines)

#-----------------------------------------------------------------
# Hàm ghi log vào file text (mở cửa hoặc đổi mật khẩu)
def log_event_to_text_file(event_description):
    with open(LOG_FILE, "a") as log_file:  # Mở file log ở chế độ append
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Lấy thời gian hiện tại
        log_file.write(f"{log_time} - {event_description}\n")  # Ghi log vào file
# Route để ghi log khi mở cửa bằng mật khẩu
@app.route('/unlock-by-password')
def unlock_by_password():
    log_event_to_text_file("Mở cửa bằng mật khẩu")  # Ghi log sự kiện mở cửa bằng mật khẩu
    return "Đã mở cửa bằng mật khẩu"
# Route để ghi log khi mở cửa bằng khuôn mặt (với ID người dùng)
@app.route('/unlock-by-face/<user_id>')
def unlock_by_face(user_id):
    log_event_to_text_file(f"Mở cửa cho người dùng ID: {user_id}")  # Ghi log sự kiện mở cửa bằng khuôn mặt
    return f"Đã mở cửa cho người dùng có ID: {user_id}"
# Route để hiển thị log từ file text
@app.route('/view-log')
def view_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as file:
            log_lines = file.readlines()  # Đọc tất cả các dòng log từ file
        if not log_lines:
            print("Log file is empty.")
    else:
        log_lines = []
        print("Log file does not exist.")
    
    return render_template('pass.html', log_lines=log_lines)

#-------------------------------------------------------
# Route cho trang chính (index) hiển thị người dùng và ảnh
@app.route('/')
def index():
    users = User.query.all()  # Giả sử có người dùng
    images = get_images()  # Lấy danh sách ảnh
    return render_template('index.html', users=users, images=images)

# Route để phục vụ tệp từ thư mục uploads
@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        sync_users_from_dataset()
    socketio.run(app, debug=True, use_reloader=False)
