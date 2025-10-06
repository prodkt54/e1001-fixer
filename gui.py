import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import os
import sys
import re
import brotli

# -------------------------
# GUI Logger
# -------------------------
class GuiLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, msg):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

    def flush(self):
        pass  # file-like object requirement

# -------------------------
# Language dictionary
# -------------------------
LANG = "EN"  # default

def tr(en, vn):
    return vn if LANG == "VN" else en

# -------------------------
# Global variables
# -------------------------
rom_directory = "rom.zip"  # default ROM path

def load_rom_file():
    global rom_directory
    file_path = filedialog.askopenfilename(
        title=tr("Select ROM file", "Chọn file ROM"),
        filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
    )
    if file_path:
        rom_directory = file_path
        logger.write(f"🔹 {tr('ROM loaded', 'ROM đã được chọn')}: {rom_directory}")

# -------------------------
# CLI Utility functions
# -------------------------
def get_connected_devices():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()[1:]
    device_names, statuses = [], []
    for line in lines:
        if line.strip():
            parts = line.split("\t")
            if len(parts) == 2:
                device_names.append(parts[0])
                statuses.append(parts[1])
    return device_names, statuses

def check_system_partition_size():
    try:
        result = subprocess.run(["adb", "shell", "df", "/system"], capture_output=True, text=True)
        lines = [line for line in result.stdout.strip().splitlines() if "linker" not in line and "Warning" not in line]
        if len(lines) < 2:
            return None
        parts = lines[1].split()
        if len(parts) < 4:
            return None
        total = int(parts[1]) / 1024
        used  = int(parts[2]) / 1024
        free  = int(parts[3]) / 1024
        return {"Total (MB)": total, "Used (MB)": used, "Free (MB)": free}
    except Exception as e:
        logger.write(f"{tr('Error getting partition info', 'Lỗi khi lấy thông tin phân vùng')}: {e}")
        return None

def extract_7z(seven_zip_path, archive_path, output_path):
    cmd = [seven_zip_path, "x", archive_path, f"-o{output_path}", "-y", "-bsp1"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    progress_pattern = re.compile(r'(\d+)%')
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.strip()
            logger.write(line)
            match = progress_pattern.search(line)
            if match:
                percent = int(match.group(1))
                progress_var.set(percent)
    process.wait()
    progress_var.set(0)
    if process.returncode == 0:
        messagebox.showinfo(tr("Extract", "Giải nén"), tr("✅ Extract completed!", "✅ Giải nén hoàn tất!"))
    else:
        messagebox.showerror(tr("Extract Error", "Lỗi giải nén"), f"{tr('Error code', 'Mã lỗi')}: {process.returncode}")

def decompress_dat_br(input_file, dat_file):
    logger.write(f"🔹 {tr('Decompressing', 'Giải nén')} {input_file} → {dat_file} ...")
    with open(input_file, "rb") as f:
        compressed = f.read()
    decompressed = brotli.decompress(compressed)
    with open(dat_file, "wb") as f:
        f.write(decompressed)
    logger.write(f"✅ {tr('Done', 'Hoàn tất')}: {dat_file} ({len(decompressed)//1024/1024:.2f} MB)")

def convert_dat_to_img(sdat2img_path, transfer_list, dat_file, img_file):
    logger.write(f"🔹 {tr('Converting', 'Chuyển đổi')} {dat_file} → {img_file}")
    cmd = ["python", sdat2img_path, transfer_list, dat_file, img_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        logger.write(line.strip())
    process.wait()
    if process.returncode == 0:
        logger.write(f"✅ {tr('Converted', 'Đã chuyển đổi')}: {img_file}")
    else:
        logger.write("❌ " + tr("Convert error", "Lỗi chuyển đổi"))

def resize_img_wsl(img_file=r"output\\system.img"):
    if not os.path.exists(img_file):
        logger.write(f"❌ {tr('File not found', 'File không tồn tại')}: {img_file}")
        return
    size_bytes = os.path.getsize(img_file)
    size_mb = size_bytes / 1024 / 1024
    logger.write(f"🔹 {tr('Original size', 'Kích thước gốc')} {img_file}: {size_mb:.2f} MB")

    partition_info = check_system_partition_size()
    free_space = partition_info.get("Free (MB)", 0) if partition_info else None

    def resize_action():
        try:
            new_size = float(entry_resize.get())
            if free_space and new_size > free_space:
                msg = tr(
                    f"Entered size exceeds free system space ({free_space:.2f} MB).",
                    f"Dung lượng nhập vượt quá dung lượng trống của system ({free_space:.2f} MB)."
                )
                messagebox.showwarning(tr("Warning", "Cảnh báo"), msg)
                return
            path_wsl = img_file.replace(':','').replace('\\','/')
            logger.write(f"🔹 {tr('Expanding container to', 'Mở rộng container lên')} {new_size:.2f} MB...")
            subprocess.run(f"wsl resize2fs {path_wsl} {int(new_size)}M", shell=True)
            logger.write(f"✅ {tr('Resize done', 'Hoàn tất resize')}: {img_file} → {new_size:.2f} MB")
            popup.destroy()
        except Exception as e:
            logger.write(f"❌ {tr('Resize error', 'Lỗi resize')}: {e}")

    popup = tk.Toplevel(root)
    popup.title(tr("Resize system.img", "Thay đổi dung lượng system.img"))
    tk.Label(popup, text=f"{tr('Original size', 'Kích thước gốc')}: {size_mb:.2f} MB").pack(padx=10, pady=5)
    if free_space:
        tk.Label(popup, text=f"{tr('Free system space', 'Dung lượng trống system')}: {free_space:.2f} MB").pack(padx=10, pady=5)
    tk.Label(popup, text=tr("Enter new size (MB):", "Nhập dung lượng mới (MB):")).pack(padx=10, pady=5)
    entry_resize = tk.Entry(popup)
    if free_space:
        entry_resize.insert(0, f"{free_space:.2f}")  # Recommend default value
    entry_resize.pack(padx=10, pady=5)
    tk.Button(popup, text=tr("Resize / Apply", "Thay đổi"), command=resize_action,
              bg="#4CAF50", fg="white", relief="raised", bd=3, width=15).pack(pady=10)

def convert_and_resize():
    os.makedirs("output", exist_ok=True)
    sdat2img_path = r"sdat2img.py"
    partitions = [
        {"name": "system", "dat_br": r"temp\system.new.dat.br", "transfer_list": r"temp\system.transfer.list", "img": r"output\system.img"},
        {"name": "vendor", "dat_br": r"temp\vendor.new.dat.br", "transfer_list": r"temp\vendor.transfer.list", "img": r"output\vendor.img"},
    ]
    for part in partitions:
        decompress_dat_br(part["dat_br"], part["dat_br"].replace(".new.dat.br", ".new.dat"))
        dat_file = part["dat_br"].replace(".new.dat.br", ".new.dat")
        convert_dat_to_img(sdat2img_path, part["transfer_list"], dat_file, part["img"])
    resize_img_wsl()

# -------------------------
# GUI Actions
# -------------------------
def run_check_devices(): run_in_thread(gui_check_devices)
def run_check_partition(): run_in_thread(gui_check_partition)
def run_build_images(): run_in_thread(gui_build_images)

def gui_check_devices():
    devices, statuses = get_connected_devices()
    if devices:
        for d, s in zip(devices, statuses):
            logger.write(f"{d} -> {s}")
            if s == 'unauthorized':
                logger.write(tr("Allow device first", "Cho phép thiết bị trước"))
    else:
        logger.write(tr("No devices connected", "Không có thiết bị kết nối"))

def gui_check_partition():
    info = check_system_partition_size()
    if info:
        for k, v in info.items():
            logger.write(f"{k}: {v:.2f} MB")
    else:
        logger.write(tr("Cannot get partition info", "Không lấy được thông tin phân vùng"))

def gui_build_images():
    extract_7z("7z.exe", rom_directory, "temp/")
    convert_and_resize()
    os.system("wsl cp temp/boot.img output")
    messagebox.showinfo(tr("Build", "Xây dựng"), tr("✅ Build system.img & vendor.img done", "Hoàn tất build system.img & vendor.img"))

def gui_about():
    msg = (
        "E1001 Fix Tool\n"
        "Author / Tác giả: Trần Quốc Khánh (prodkt54)\n"
        "Dependencies / Thư viện: brotli, adb, 7z.exe, sdat2img.py\n"
        "Thanks / Cảm ơn: xpirt (sdat2img.py)\n"
        "Version: 1.0"
    )
    messagebox.showinfo(tr("About", "Giới thiệu"), msg)

def switch_language():
    global LANG
    LANG = "VN" if LANG == "EN" else "EN"
    btn_check_device.config(text=tr("Check ADB Devices", "Kiểm tra ADB"))
    btn_check_partition.config(text=tr("Check system partition", "Kiểm tra phân vùng"))
    btn_build_img.config(text=tr("Build system/vendor.img", "Build system/vendor.img"))
    btn_about.config(text=tr("About", "Giới thiệu"))
    btn_exit.config(text=tr("Exit", "Thoát"))
    btn_lang.config(text=tr("Switch to Vietnamese", "Chuyển sang English"))
    btn_load_rom.config(text=tr("Load ROM", "Chọn ROM"))



# -------------------------
# Thread helper
# -------------------------
def run_in_thread(func):
    threading.Thread(target=func, daemon=True).start()

# -------------------------
# GUI Main
# -------------------------
root = tk.Tk()
root.title("E1001 Fix Tool")
root.geometry("850x650")
root.resizable(False, False)

# Progress Bar
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(root, maximum=100, variable=progress_var)
progress_bar.pack(fill="x", padx=10, pady=5)

# Output log (font debug to hơn)
txt_output = scrolledtext.ScrolledText(root, state='disabled', width=100, height=25, font=("Consolas", 12))
txt_output.pack(padx=10, pady=5)
logger = GuiLogger(txt_output)
sys.stdout = logger

# -------------------------
# Buttons frame
# -------------------------
frame_btns = tk.Frame(root)
frame_btns.pack(pady=10)

btn_style = {"bg": "#4CAF50", "fg": "white", "relief": "raised", "bd": 3, "width": 18, "height": 1, "font": ("Arial", 10)}

btn_check_device = tk.Button(frame_btns, text=tr("Check ADB Devices", "Kiểm tra ADB"), command=run_check_devices, **btn_style)
btn_check_partition = tk.Button(frame_btns, text=tr("Check system partition", "Kiểm tra phân vùng"), command=run_check_partition, **btn_style)
btn_build_img = tk.Button(frame_btns, text=tr("Build system/vendor.img", "Build system/vendor.img"), command=run_build_images, **btn_style)
btn_about = tk.Button(frame_btns, text=tr("About", "Giới thiệu"), command=gui_about, **btn_style)
btn_exit = tk.Button(frame_btns, text=tr("Exit", "Thoát"), command=root.quit, **btn_style)
btn_lang = tk.Button(frame_btns, text=tr("Switch to Vietnamese", "Chuyển sang English"), command=switch_language, **btn_style)
btn_load_rom = tk.Button(frame_btns, text=tr("Load ROM", "Chọn ROM"), command=load_rom_file, **btn_style)

# Arrange buttons in grid
btn_check_device.grid(row=0, column=0, padx=5, pady=5)
btn_check_partition.grid(row=0, column=1, padx=5, pady=5)
btn_build_img.grid(row=0, column=2, padx=5, pady=5)
btn_about.grid(row=0, column=3, padx=5, pady=5)
btn_exit.grid(row=0, column=4, padx=5, pady=5)
btn_lang.grid(row=1, column=0, columnspan=2, pady=5)
btn_load_rom.grid(row=1, column=2, columnspan=3, pady=5)

# -------------------------
# Run GUI
# -------------------------
root.mainloop()
