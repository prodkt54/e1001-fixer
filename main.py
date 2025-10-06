import subprocess
import sys
import re
import os
import brotli


rom_directory = "rom.zip"


def decompress_dat_br(input_file, dat_file):
    print(f"🔹 Giải nén {input_file} → {dat_file} ...")
    with open(input_file, "rb") as f:
        compressed = f.read()
    decompressed = brotli.decompress(compressed)
    with open(dat_file, "wb") as f:
        f.write(decompressed)
    print(f"✅ Hoàn tất: {dat_file} ({len(decompressed)//1024/1024:.2f} MB)")

# ----------------------------
# Hàm convert .dat → .img
# ----------------------------
def convert_dat_to_img(sdat2img_path, transfer_list, dat_file, img_file):
    print(f"🔹 Convert {dat_file} → {img_file} bằng sdat2img.py")
    cmd = ["python", sdat2img_path, transfer_list, dat_file, img_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line.strip())
    process.wait()
    if process.returncode == 0:
        print(f"✅ Convert thành công: {img_file}")
    else:
        print("❌ Lỗi convert:")
        print(process.stdout.read())
        print(process.stderr.read())
def resize_img_wsl(img_file = r"output\system.img"):
    if not os.path.exists(img_file):
        print(f"❌ File không tồn tại: {img_file}")
        return
    # Kích thước gốc
    size_bytes = os.path.getsize(img_file)
    size_mb = size_bytes / 1024 / 1024
    print(f"🔹 Kích thước gốc của {img_file}: {size_mb:.2f} MB")
    # Nhập kích thước mới từ bàn phím
    while True:
        try:
            new_size_mb = float(input("Nhập kích thước mới mong muốn (MB): "))
            if new_size_mb <= 0:
                print("⚠️ Kích thước phải > 0")
                continue
            break
        except ValueError:
            print("⚠️ Vui lòng nhập số hợp lệ")
    #new_size_bytes = int(new_size_mb * 1024 * 1024)
    # Convert Windows path → WSL 
    path_wsl = img_file.replace(':','').replace('\\','/')
    print(f"🔹 Mở rộng file container lên {new_size_mb:.2f} MB...")
    #subprocess.run(f"wsl truncate -s {new_size_bytes} {path_wsl}", shell=True)
    new_size_mb = int(new_size_mb)
    print("🔹 Resize filesystem ext4...")
    subprocess.run(f"wsl resize2fs {path_wsl} {new_size_mb}M", shell=True)
    print(f"✅ Hoàn tất resize {img_file} lên {new_size_mb:.2f} MB")

    # =============================
    # Main
    # =============================
    #img_file = input("Nhập đường dẫn file .img: ").strip()


# ----------------------------
# Main
# ----------------------------
def convert_and_resize():
    os.makedirs("output", exist_ok=True)
    sdat2img_path = r"sdat2img.py"  # đường dẫn tới sdat2img.py

    # Danh sách các phân vùng cần convert
    partitions = [
        {"name": "system", "dat_br": r"temp\system.new.dat.br", "transfer_list": r"temp\system.transfer.list", "img": r"output\system.img"},
        {"name": "vendor", "dat_br": r"temp\vendor.new.dat.br", "transfer_list": r"temp\vendor.transfer.list", "img": r"output\vendor.img"},
    ]

    for part in partitions:
        decompress_dat_br(part["dat_br"], part["dat_br"].replace(".new.dat.br", ".new.dat"))
        dat_file = part["dat_br"].replace(".new.dat.br", ".new.dat")
        convert_dat_to_img(sdat2img_path, part["transfer_list"], dat_file, part["img"])
    resize_img_wsl()

def get_connected_devices():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()[1:]  # bỏ dòng header

    device_names = []
    statuses = []

    for line in lines:
        if line.strip():  # bỏ dòng trống
            parts = line.split("\t")
            if len(parts) == 2:
                device_names.append(parts[0])
                statuses.append(parts[1])

    return device_names, statuses

# Lấy 2 mảng
def check_device_status():
    devices, status = get_connected_devices()

    devices_count = len(devices)

    if devices:
        print(f"✅ Thiết bị được kết nối: {devices_count}")
        for d, s in zip(devices, status):
            print(f"{d} -> {s}")
            if(s == 'unauthorized'):
                print("↑ Cho phép thiết bị này trước khi tiếp tục!")
                sys.exit()
    else:
        print("❌ Không có thiết bị nào được kết nối.")
def check_system_partition_size():
    try:
        # Chạy lệnh df /system
        result = subprocess.run(
            ["adb", "shell", "df", "/system"],
            capture_output=True,
            text=True
        )
        output = result.stdout.strip()

        # Lọc bỏ dòng warning (bỏ các dòng chứa "linker" hoặc "Warning")
        lines = [line for line in output.splitlines() if "linker" not in line and "Warning" not in line]

        if len(lines) < 2:
            return None  # không parse được

        # Lấy dòng thứ 2 (dữ liệu phân vùng)
        parts = lines[1].split()
        if len(parts) < 4:
            return None

        # Chuyển sang MB
        total = int(parts[1]) / 1024
        used  = int(parts[2]) / 1024
        free  = int(parts[3]) / 1024

        return {"Tổng dung lượng MB": total, "Đã sử dụng MB": used, "Còn trống_MB": free}

    except Exception as e:
        print("Lỗi khi lấy thông tin phân vùng:", e)
        return None

def extract_7z(seven_zip_path = "7z.exe", archive_path = rom_directory, output_path = "temp"):
    """
    Giải nén archive bằng 7z.exe và in progress
    :param seven_zip_path: đường dẫn tới 7z.exe
    :param archive_path: file nén (.zip, .7z, ...)
    :param output_path: thư mục giải nén
    """
    # Lệnh 7z
    cmd = [seven_zip_path, "x", archive_path, f"-o{output_path}", "-y", "-bsp1"]

    # -bsp1 để in progress ra stdout
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    progress_pattern = re.compile(r'(\d+)%')  # regex tìm phần trăm

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.strip()
            # In raw line
            print(line)
            # Nếu có phần trăm
            match = progress_pattern.search(line)
            if match:
                percent = match.group(1)
                print(f"Progress: {percent}%")

    process.wait()
    if process.returncode == 0:
        print("✅ Extract hoàn tất")
    else:
        print(f"❌ Extract lỗi, code: {process.returncode}")


def main():
    running = True
    
    while(running):
        os.system("cls")
        print("1. Check thiết bị ADB")
        print("2. Check dung lượng phân vùng system")
        print("3. Tạo system.img, vendor.img mới từ .zip")
        print("4. Thông tin ứng dụng")
        print("5. Thoát")
        print("Nhập lựa chọn của bạn: ")
        choose = input()
        if(choose == "1"):
            os.system("cls")
            check_device_status()
            input()
        if(choose == "2"):
            os.system("cls")
            print(check_system_partition_size())
            input()
        if(choose == "3"):
            os.system("cls")
            extract_7z()
            convert_and_resize()
            os.system("wsl cp temp/boot.img output")
            print("Bạn có muốn xoá các file tàn dư (temp) không?\nY: Có. xoá cho đỡ tốn ổ\nN: Không, cứ để vậy")
            arg = input()
            if(arg == "Y" or arg == "y"):
                os.system("wsl rm -rf temp")
            print("Ok đã hoàn thành việc build file system, vendor mới (output/system.img, vendor.img)")
            print("Bạn có thể flash file boot.img, system.img, vendor.img để bắt đầu sử dụng")
            print("Nhấn nút bất kì để tiếp tục")
            input()
        if(choose == "4"):
            print("About:\n Viết bởi:\n  Trần Quốc Khánh (prodkt54)\n Dependencies: brotli\n Cảm ơn:\n  xpirt (sda2img.py)")
            input()
        if(choose == "5"):
            sys.exit()
main()