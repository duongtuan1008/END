// document.addEventListener('DOMContentLoaded', function () {
//     // Hiển thị các thông báo từ Flask (Flash messages)
//     {% with messages = get_flashed_messages(with_categories=true) %}
//     {% if messages %}
//         {% for category, message in messages %}
//             Swal.fire({
//                 icon: '{{ category }}',  // Có thể là 'success', 'error', 'warning', 'info'
//                 title: '{{ message }}',
//                 showConfirmButton: true,
//                 timer: 5000 // Thông báo tự động đóng sau 5 giây
//             });
//         {% endfor %}
//     {% endif %}
//     {% endwith %}
// });

// Hàm xác nhận xóa người dùng với SweetAlert2
function confirmDelete(userId) {
    Swal.fire({
        title: 'Bạn có chắc chắn muốn xóa người dùng này?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Có',
        cancelButtonText: 'Không'
    }).then((result) => {
        if (result.isConfirmed) {
            // Nếu người dùng nhấn "Có", chuyển hướng tới URL để xóa người dùng
            window.location.href = '/delete/' + userId;
        }
    });
}

// Hàm xác nhận thêm người dùng với SweetAlert2
function confirmAddUser() {
    Swal.fire({
        title: 'Bạn có chắc chắn muốn thêm người dùng này?',
        icon: 'info',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Có',
        cancelButtonText: 'Không'
    }).then((result) => {
        if (result.isConfirmed) {
            // Nếu người dùng xác nhận, gửi form để thêm người dùng
            document.getElementById('addUserForm').submit();
        }
    });
}
function togglePlayPause(videoId) {
    var videoElement = document.getElementById(videoId);
    if (videoElement.paused) {
        videoElement.play();
    } else {
        videoElement.pause();
    }
}
document.getElementById("submit-on").addEventListener("click", function() {
    fetch('/open_door', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Cửa đã được mở!");
        } else {
            alert("Có lỗi xảy ra khi mở cửa.");
        }
    })
    .catch(error => {
        console.error("Error:", error);
    });
});
document.getElementById("submit-off").addEventListener("click", function() {
    fetch('/closeclose_door', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Cửa đã đóngđóng!");
        } else {
            alert("Có lỗi xảy ra khi đóngđóng cửa.");
        }
    })
    .catch(error => {
        console.error("Error:", error);
    });
});


