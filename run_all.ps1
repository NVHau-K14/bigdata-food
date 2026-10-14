# ==============================================================================
# Pipeline thực thi toàn diện đồ án Big Data: Phân tích hành vi & Gợi ý món ăn
# Không dùng Streamlit - Chuyển sang xuất dữ liệu web và giao diện tĩnh độc lập
# ==============================================================================

[CmdletBinding()]
param (
    [switch]$SkipExport = $false,
    [switch]$ServeWeb = $true,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " [BIG DATA FOOD] PIPELINE THỰC THI & KHỞI CHẠY WEB TĨNH   " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

# 1. Kiểm tra môi trường Python
if (Test-Path ".venv\Scripts\python.exe") {
    $pythonCmd = ".venv\Scripts\python.exe"
    Write-Host "[1/4] Sử dụng Python từ môi trường ảo .venv" -ForegroundColor Cyan
} else {
    $pythonCmd = "python"
    Write-Host "[1/4] Sử dụng Python hệ thống" -ForegroundColor Cyan
}

# 2. Xuất dữ liệu phục vụ Dashboard Web Tĩnh
if (-not $SkipExport) {
    Write-Host "[2/4] Xuất dữ liệu tĩnh từ kết quả pipeline (src/export_for_web.py)..." -ForegroundColor Cyan
    & $pythonCmd src/export_for_web.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Xuất dữ liệu cho web thất bại! Dừng thực thi."
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[2/4] Bỏ qua bước xuất dữ liệu theo tùy chọn -SkipExport" -ForegroundColor Yellow
}

# 3. Kiểm thử: Chrome hoặc Edge headless đọc văn bản hiển thị (verify_web_ui.mjs), rồi đối chiếu số liệu (verify_web.py)
Write-Host "[3/4] Kiểm tra giao diện và đối chiếu số liệu (src/verify_web_ui.mjs, src/verify_web.py)..." -ForegroundColor Cyan
node src/verify_web_ui.mjs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Kiểm tra giao diện thất bại! Dừng thực thi."
    exit $LASTEXITCODE
}
& $pythonCmd src/verify_web.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Kiểm tra đối chiếu số liệu thất bại (có chênh lệch với dữ liệu gốc)! Dừng thực thi."
    exit $LASTEXITCODE
}

# 4. Khởi chạy giao diện tĩnh
if ($ServeWeb) {
    Write-Host "[4/4] Khởi chạy máy chủ cục bộ cho giao diện web..." -ForegroundColor Cyan
    Write-Host ">> Địa chỉ dashboard: http://localhost:$Port" -ForegroundColor Green
    Write-Host ">> Bạn cũng có thể mở trực tiếp không cần server: web/index.html" -ForegroundColor DarkGray
    Write-Host ">> Nhấn Ctrl+C để dừng máy chủ web." -ForegroundColor DarkGray
    & $pythonCmd -m http.server $Port --directory web
} else {
    Write-Host "[4/4] Hoàn tất pipeline. Để xem giao diện, hãy mở tệp web/index.html" -ForegroundColor Green
}
