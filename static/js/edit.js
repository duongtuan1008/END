// Hàm xác nhận xóa ảnh người dùng
function confirmDeleteImage(userId, imageName, index) {
    Swal.fire({
        title: 'Bạn có chắc chắn muốn xóa ảnh này?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Có',
        cancelButtonText: 'Không',
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
    }).then((result) => {
        if (result.isConfirmed) {
            // Sau khi người dùng xác nhận, submit form
            document.getElementById('delete-image-' + index).submit();
        }
    });
}
// Hàm xác nhận xóa ảnh người dùng
function confirmDeleteImage(userId, imageName, index) {
    Swal.fire({
        title: 'Bạn có chắc chắn muốn xóa ảnh này?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Có',
        cancelButtonText: 'Không',
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
    }).then((result) => {
        if (result.isConfirmed) {
            // Sau khi người dùng xác nhận, submit form
            document.getElementById('delete-image-' + index).submit();
        }
    });
}

// Hàm xử lý thông báo xóa thành công
function showDeleteSuccess() {
    Swal.fire({
        title: 'Thành công!',
        text: 'Ảnh đã được xóa!',
        icon: 'success',
        confirmButtonText: 'OK'
    });
}

// Hàm xử lý thông báo xóa thất bại
function showDeleteError(message) {
    Swal.fire({
        title: 'Lỗi!',
        text: message,
        icon: 'error',
        confirmButtonText: 'OK'
    });
}
