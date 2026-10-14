<#
.SYNOPSIS
    Chạy toàn bộ pipeline đồ án Big Data từ dữ liệu thô đến dashboard web, ghi log từng bước.

.DESCRIPTION
    Thứ tự: khởi động cụm, nạp dữ liệu thô lên HDFS, làm sạch cả hai bộ, kiểm tra dữ liệu sạch, benchmark lưu trữ,
    EDA, chia dữ liệu, mô hình cơ sở, ALS, ALS ngầm định, K-means, đổi nhãn cụm Food.com, độ nhạy ViFoodRec,
    thực nghiệm mở rộng quy mô (2 Worker rồi 1 Worker), xuất kết quả, xuất dữ liệu web, kiểm thử web.

    Mỗi bước ghi log nguyên văn vào reports/evidence/logs/<LogPrefix>NN_<tên bước>.log và dừng ngay khi có lỗi.
    Các bước Spark chạy trong container client; các bước xuất web và kiểm thử web chạy trên máy chủ (Python, Node).

.PARAMETER HdfsRoot
    Thư mục gốc trên HDFS (mặc định rỗng: dữ liệu ở /data, /models). Dùng để chạy thử trên bản sao mà không đụng kết quả chính.
.PARAMETER CleanRun
    Chạy trên bản sao: dùng cụm đang chạy của bản chính, tạo container client riêng gắn thư mục này, HdfsRoot mặc định /cleanrun.
.PARAMETER StorageMode
    hdfs (mặc định) hoặc local. Chế độ local chỉ chạy phần ViFoodRec (làm sạch, chia, cơ sở, ALS, K-means) bằng Spark local[*].
.PARAMETER Fast
    Bỏ qua các bước nặng: benchmark lưu trữ, thực nghiệm mở rộng, ALS ngầm định. Bảng ALS ngầm định trên web sẽ không được làm mới.
.PARAMETER WebOnly
    Chỉ xuất dữ liệu web từ app/data, kiểm thử web và (nếu có -ServeWeb) mở web. Không cần Spark.
.EXAMPLE
    .\run_all.ps1                       # chạy tất cả
    .\run_all.ps1 -Fast                 # bỏ các bước nặng
    .\run_all.ps1 -WebOnly -ServeWeb    # chỉ phần web, mở http://localhost:8000/
    .\run_all.ps1 -CleanRun -LogPrefix S6_   # chạy thử trên bản sao (stage S6)
#>

[CmdletBinding()]
param (
    [string]$HdfsRoot = "",
    [switch]$CleanRun,
    [ValidateSet("hdfs", "local")][string]$StorageMode = "hdfs",
    [string]$ClientContainer = "",
    [string]$LogPrefix = "run_",
    [switch]$SkipCluster,
    [switch]$SkipLoad,
    [switch]$SkipSmoke,
    [switch]$SkipStorageBenchmark,
    [switch]$SkipEda,
    [switch]$SkipImprove,
    [switch]$SkipSensitivity,
    [switch]$SkipScalability,
    [switch]$Fast,
    [switch]$SkipWeb,
    [switch]$WebOnly,
    [switch]$ServeWeb,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$root = $PSScriptRoot
Set-Location $root

# Phiên bản image Spark ghim cùng docker-compose.yml (dùng khi tạo container client cho bản chạy thử)
$SparkImage = "quay.io/jupyter/pyspark-notebook:spark-4.2.0"
$Hdfs = "/opt/hadoop/bin/hdfs"
$Py = "/opt/conda/bin/python"

if ($Fast) { $SkipStorageBenchmark = $true; $SkipScalability = $true; $SkipImprove = $true }
if ($CleanRun -and -not $HdfsRoot) { $HdfsRoot = "/cleanrun" }
if ($HdfsRoot -and -not $HdfsRoot.StartsWith("/")) { $HdfsRoot = "/" + $HdfsRoot }
if ($CleanRun) { $SkipCluster = $true }
if (-not $ClientContainer) { if ($CleanRun) { $ClientContainer = "bigdata_spark_cleanrun" } else { $ClientContainer = "bigdata_spark_env" } }
$LocalMode = ($StorageMode -eq "local")

$logDir = Join-Path $root "reports\evidence\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$script:stepNo = 0
$script:summary = New-Object System.Collections.ArrayList
$script:runWatch = [System.Diagnostics.Stopwatch]::StartNew()

function Invoke-Step {
    # Chạy một dòng lệnh, ghi log UTF-8 nguyên văn (gộp stdout và stderr) và dừng khi mã thoát khác 0.
    param([string]$Name, [string]$CommandLine, [switch]$AllowFail)
    $script:stepNo++
    $logName = "{0}{1:D2}_{2}.log" -f $LogPrefix, $script:stepNo, $Name
    $logPath = Join-Path $logDir $logName
    Write-Host ""
    Write-Host ("[{0:D2}] {1}" -f $script:stepNo, $Name) -ForegroundColor Cyan
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $writer = New-Object System.IO.StreamWriter($logPath, $false, (New-Object System.Text.UTF8Encoding($false)))
    $code = 0
    try {
        $writer.WriteLine('$ ' + $CommandLine)
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        cmd /c "$CommandLine 2>&1" | ForEach-Object { $writer.WriteLine($_); Write-Host $_ }
        $code = $LASTEXITCODE
        $ErrorActionPreference = $prev
        $watch.Stop()
        $writer.WriteLine(('# mã thoát {0}, {1:N1} giây' -f $code, $watch.Elapsed.TotalSeconds))
    } finally {
        $writer.Close()
    }
    [void]$script:summary.Add(("{0:D2} | {1} | mã {2} | {3:N1} giây | {4}" -f $script:stepNo, $Name, $code, $watch.Elapsed.TotalSeconds, $logName))
    if ($code -ne 0 -and -not $AllowFail) {
        Write-Summary
        throw "Bước '$Name' lỗi (mã $code). Xem $logPath"
    }
    return $code
}

function Write-Summary {
    $path = Join-Path $logDir ("{0}tong_ket.log" -f $LogPrefix)
    $lines = @("Tổng kết lần chạy run_all.ps1 (tham số: HdfsRoot='$HdfsRoot', StorageMode=$StorageMode, container=$ClientContainer)", "")
    $lines += $script:summary
    $lines += ""
    $lines += ("Tổng thời gian đến thời điểm ghi: {0:N1} phút" -f $script:runWatch.Elapsed.TotalMinutes)
    [System.IO.File]::WriteAllLines($path, $lines, (New-Object System.Text.UTF8Encoding($false)))
}

function Invoke-InClient {
    param([string]$Name, [string]$Script, [string]$ScriptArgs = "")
    $cmd = "docker exec -w /home/jovyan/work -e STORAGE_MODE=$StorageMode -e HDFS_ROOT=$HdfsRoot $ClientContainer $Py $Script $ScriptArgs"
    [void](Invoke-Step -Name $Name -CommandLine $cmd.Trim())
}

function Get-AliveWorkers {
    try {
        $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $json = docker exec spark-master curl -s http://localhost:8080/json/ 2>$null
        $ErrorActionPreference = $prev
        return [int](($json | ConvertFrom-Json).aliveworkers)
    } catch { return -1 }
}

function Wait-Workers {
    param([int]$Expected, [int]$TimeoutSec = 180)
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($watch.Elapsed.TotalSeconds -lt $TimeoutSec) {
        if ((Get-AliveWorkers) -eq $Expected) { Write-Host "   Spark Master báo $Expected Worker còn sống." -ForegroundColor DarkGray; return }
        Start-Sleep -Seconds 3
    }
    throw "Hết $TimeoutSec giây mà Spark Master chưa báo đúng $Expected Worker."
}

function Wait-HdfsReady {
    param([int]$TimeoutSec = 240)
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($watch.Elapsed.TotalSeconds -lt $TimeoutSec) {
        $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $out = docker exec namenode $Hdfs dfsadmin -safemode get 2>$null
        $ErrorActionPreference = $prev
        if ($out -match "OFF") { Write-Host "   HDFS đã thoát safe mode." -ForegroundColor DarkGray; return }
        Start-Sleep -Seconds 3
    }
    throw "Hết $TimeoutSec giây mà HDFS chưa sẵn sàng."
}

function Get-HostPython {
    if (Test-Path ".venv\Scripts\python.exe") { return ".venv\Scripts\python.exe" }
    return "python"
}

function Invoke-WebStages {
    $python = Get-HostPython
    [void](Invoke-Step -Name "xuat_du_lieu_web" -CommandLine "$python src/export_for_web.py")
    if (-not $SkipWeb) {
        [void](Invoke-Step -Name "kiem_thu_giao_dien_web" -CommandLine "node src/verify_web_ui.mjs")
        [void](Invoke-Step -Name "doi_chieu_so_lieu_web" -CommandLine "$python src/verify_web.py")
        [void](Invoke-Step -Name "kiem_thu_kieu_chu_web" -CommandLine "$python src/verify_web_style.py")
    }
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " DO AN BIG DATA: PIPELINE TU DAU DEN DASHBOARD WEB" -ForegroundColor Green
Write-Host ("  HdfsRoot='{0}'  StorageMode={1}  Container={2}  LogPrefix={3}" -f $HdfsRoot, $StorageMode, $ClientContainer, $LogPrefix) -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

if ($WebOnly) {
    Invoke-WebStages
    Write-Summary
} else {
    # 1. Cụm
    if (-not $SkipCluster -and -not $LocalMode) {
        [void](Invoke-Step -Name "khoi_dong_cum" -CommandLine "docker compose up -d")
        Wait-HdfsReady
        Wait-Workers -Expected 2
    }
    if ($CleanRun) {
        # Cụm của bản chính đang chạy; bản sao dùng container client riêng gắn thư mục này để không đụng thư mục chính.
        # Tên máy phải không có dấu gạch dưới: Spark từ chối URL driver dạng spark://...@bigdata_spark_cleanrun:port.
        $net = (docker inspect namenode --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}').Trim()
        $exists = (docker ps -a --filter "name=^$ClientContainer$" --format '{{.Names}}')
        if (-not $exists) {
            $runCmd = "docker run -d --name $ClientContainer --hostname spark-cleanrun --network-alias spark-cleanrun --network $net --user root " +
                "-e SPARK_HOME=/usr/local/spark -e PYTHONPATH=/usr/local/spark/python:/usr/local/spark/python/lib/py4j-0.10.9.9-src.zip " +
                "-e PYSPARK_PYTHON=$Py -e PYSPARK_DRIVER_PYTHON=$Py -e HDFS_NAMENODE_URL=hdfs://namenode:9000 -e SPARK_MASTER_URL=spark://spark-master:7077 " +
                "-v ""${root}:/home/jovyan/work"" -w /home/jovyan/work $SparkImage sleep infinity"
            [void](Invoke-Step -Name "tao_container_client" -CommandLine $runCmd)
        }
        Wait-HdfsReady
        Wait-Workers -Expected 2
    }

    if ($LocalMode) {
        # Chế độ local: dữ liệu ở data/raw trên máy, Spark local[*]; chỉ phần ViFoodRec để chạy trong vài phút.
        Invoke-InClient "local_lam_sach_vietnam" "src/run_pipeline_p3.py" "--only vietnam"
        Invoke-InClient "local_chia_du_lieu_vietnam" "src/split_data.py" "--only vietnam"
        Invoke-InClient "local_co_so_vietnam" "src/baseline.py" "--only vietnam"
        Invoke-InClient "local_als_vietnam" "src/train_als.py" "--only vietnam"
        Invoke-InClient "local_kmeans_vietnam" "src/kmeans_behavior.py" "--only vietnam"
        Write-Summary
        Write-Host "Hoàn tất chế độ local (chỉ ViFoodRec)." -ForegroundColor Green
        return
    }

    # 2. Nạp dữ liệu thô lên HDFS (chỉ đọc từ /data/raw_host trong container namenode, gắn từ data/raw)
    if (-not $SkipLoad) {
        $files = @("food_com/RAW_interactions.csv", "food_com/RAW_recipes.csv", "food_vietnam/foods.csv", "food_vietnam/ratings.csv")
        foreach ($f in $files) {
            $dir = ($f -split "/")[0]
            $leaf = ($f -split "/")[1]
            $target = "$HdfsRoot/data/raw/$f"
            [void](Invoke-Step -Name ("mkdir_" + $leaf.Replace(".csv", "").ToLower()) -CommandLine "docker exec namenode $Hdfs dfs -mkdir -p $HdfsRoot/data/raw/$dir")
            $have = Invoke-Step -Name ("kiem_tra_" + $leaf.Replace(".csv", "").ToLower()) -CommandLine "docker exec namenode $Hdfs dfs -test -e $target" -AllowFail
            if ($have -ne 0) {
                [void](Invoke-Step -Name ("put_" + $leaf.Replace(".csv", "").ToLower()) -CommandLine "docker exec namenode $Hdfs dfs -put /data/raw_host/$f $target")
            }
        }
        [void](Invoke-Step -Name "kiem_tra_du_lieu_tho" -CommandLine "docker exec namenode $Hdfs dfs -ls -R -h $HdfsRoot/data/raw")
    }

    # 3. Kiểm tra cụm bằng một lượt đọc dữ liệu thô và ghi Parquet nhỏ (cần dữ liệu đã nạp)
    if (-not $SkipSmoke) { Invoke-InClient "kiem_tra_cum_smoke_test" "src/smoke_test_cluster.py" }

    # 4. Làm sạch cả hai bộ và kiểm tra
    Invoke-InClient "lam_sach_hai_bo" "src/run_pipeline_p3.py"
    Invoke-InClient "kiem_tra_du_lieu_sach" "src/verify_clean.py"

    # 5. Benchmark lưu trữ và EDA
    if (-not $SkipStorageBenchmark) { Invoke-InClient "benchmark_luu_tru" "src/storage_benchmark.py" }
    if (-not $SkipEda) { Invoke-InClient "eda" "src/eda_analysis.py" }

    # 6. Chia dữ liệu, mô hình cơ sở, ALS, K-means
    Invoke-InClient "chia_du_lieu" "src/split_data.py"
    Invoke-InClient "mo_hinh_co_so" "src/baseline.py"
    Invoke-InClient "als_du_doan_diem" "src/train_als.py"
    if (-not $SkipImprove) { Invoke-InClient "als_ngam_dinh" "src/als_improve.py" }
    Invoke-InClient "kmeans_hanh_vi" "src/kmeans_behavior.py"
    Invoke-InClient "doi_nhan_cum_food_com" "src/relabel_food_com_clusters.py"
    if (-not $SkipSensitivity) { Invoke-InClient "do_nhay_vifoodrec" "src/vifoodrec_sensitivity.py" }

    # 7. Thực nghiệm mở rộng quy mô: 2 Worker rồi dừng worker 2 để đo 1 Worker; luôn bật lại worker 2 khi xong
    if (-not $SkipScalability) {
        Invoke-InClient "mo_rong_2_worker" "src/scalability_experiment.py"
        [void](Invoke-Step -Name "dung_worker_2" -CommandLine "docker stop spark-worker-2")
        try {
            Wait-Workers -Expected 1
            Invoke-InClient "mo_rong_1_worker" "src/scalability_experiment.py"
        } finally {
            [void](Invoke-Step -Name "bat_lai_worker_2" -CommandLine "docker start spark-worker-2" -AllowFail)
            Wait-Workers -Expected 2
        }
    }

    # 8. Xuất kết quả cho dashboard, kiểm tra, trạng thái HDFS
    Invoke-InClient "xuat_mon_tieu_bieu_cum" "src/export_cluster_top_items.py"
    Invoke-InClient "xuat_ket_qua" "src/export_for_app.py"
    Invoke-InClient "kiem_tra_xuat" "src/verify_export.py"
    [void](Invoke-Step -Name "hdfs_fsck" -CommandLine "docker exec namenode $Hdfs fsck $HdfsRoot/data")
    [void](Invoke-Step -Name "hdfs_fsck_models" -CommandLine "docker exec namenode $Hdfs fsck $HdfsRoot/models")

    # 9. Web
    Invoke-WebStages
    Write-Summary
}

Write-Host ""
Write-Host ("Hoàn tất sau {0:N1} phút. Tổng kết ở reports/evidence/logs/{1}tong_ket.log" -f $script:runWatch.Elapsed.TotalMinutes, $LogPrefix) -ForegroundColor Green

if ($ServeWeb) {
    Write-Host ">> Dashboard: http://localhost:$Port (Ctrl+C để dừng). Cũng mở được trực tiếp web/index.html" -ForegroundColor Green
    & (Get-HostPython) -m http.server $Port --directory web
} else {
    Write-Host "Để xem giao diện, mở web/index.html hoặc chạy lại với -WebOnly -ServeWeb." -ForegroundColor Green
}
