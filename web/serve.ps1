# Script khởi chạy máy chủ web cục bộ phục vụ Dashboard tĩnh
# Cổng mặc định: 8000
$port = 8000
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Khởi động máy chủ Dashboard Web tĩnh tại cổng $port..." -ForegroundColor Green
Write-Host " Truy cập tại trình duyệt: http://localhost:$port" -ForegroundColor Cyan
Write-Host " Hoặc nhấp đúp trực tiếp tệp index.html để chạy offline" -ForegroundColor Yellow
Write-Host " Nhấn Ctrl+C để dừng máy chủ" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Green

python -m http.server $port --directory $PSScriptRoot
