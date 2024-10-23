// Lấy danh sách tất cả các ô nhập mật khẩu
const inputs = Array.from(document.querySelectorAll('.password-box input'));

// Hàm tự động chuyển qua ô nhập tiếp theo khi người dùng nhập ký tự
inputs.forEach((input, index) => {
    input.addEventListener('input', function() {
        const nextInput = inputs[index + 1];

        // Khi người dùng nhập, nếu có ô tiếp theo thì focus vào ô tiếp theo
        if (input.value && nextInput) {
            nextInput.focus();
        }

        // Kiểm tra nếu đã đầy đủ ô thì không cho nhập thêm
        const allFilled = inputs.every(input => input.value.length === 1);
        if (allFilled) {
            inputs.forEach(input => input.setAttribute('disabled', true)); // Khóa các ô lại
        }
    });

    // Khi nhấn phím Backspace trong ô hiện tại, tự động quay lại ô trước đó
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' && input.value === '' && index > 0) {
            inputs[index - 1].focus();
            inputs[index - 1].value = ''; // Xóa giá trị ở ô trước khi quay lại
        }

        // Bỏ khóa ô khi nhấn backspace
        if (e.key === 'Backspace') {
            inputs.forEach(input => input.removeAttribute('disabled')); // Mở khóa các ô khi xoá
        }
    });
});

// Hàm gửi mật khẩu về backend để cập nhật file pass.txt
function updatePassword() {
    // Lấy giá trị từ các ô nhập mật khẩu
    const password = inputs.map(input => input.value).join('');  // Nối các ký tự lại thành chuỗi

    // Kiểm tra nếu mật khẩu đủ 5 ký tự
    if (password.length === 5) {
        // Gửi yêu cầu POST để lưu mật khẩu
        fetch('/update-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ password: password }),  // Gửi dữ liệu mật khẩu dưới dạng JSON
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Mật khẩu đã được cập nhật thành công!');
            } else {
                alert('Có lỗi xảy ra khi cập nhật mật khẩu: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Lỗi:', error);
            alert('Có lỗi xảy ra khi gửi yêu cầu!');
        });
    } else {
        alert('Mật khẩu phải có 5 ký tự!');
    }
}

// Hàm reset mật khẩu (xóa tất cả và mở khóa các ô)
function resetPassword() {
    inputs.forEach(input => {
        input.value = ''; // Xoá tất cả các ô
        input.removeAttribute('disabled'); // Mở khóa các ô
    });
    inputs[0].focus(); // Focus vào ô đầu tiên sau khi reset
}

// Focus vào ô đầu tiên khi trang được tải
window.onload = function() {
    inputs[0].focus();
};
